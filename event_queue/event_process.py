import os
import importlib
import logging

import pika
from django.core.cache import caches
from django.db.models import Q
from django.utils import timezone

from event_queue.models import EventQueueModel

task_cache = caches['default']
logger = logging.getLogger('main')


class QueueProcessFacade(object):
    """
    Class processes event in queue

    """

    TASK_NAME = None
    EXCHANGE = None
    EXCHANGE_TYPE = None
    QUEUE = None
    ROUTING_KEY = None
    EVENT_TYPE = None
    MAX_ATTEMPT = 3

    __default_connection_config = {
        'host': 'localhost',
        'port': 5672,
        'vhost': '/',
        'username': 'guest',
        'password': 'guest',
    }

    __connection = None
    __channel = None
    __timeout = None
    __limit = None

    def __init__(self, task_name=None, timeout=600, limit=100):
        self.set_task_name(task_name)
        self.__timeout = timeout
        self.__limit = limit

    def set_connection(self, connection=None):
        if connection is not None:
            self.__connection = connection

    def get_connection(self):
        return self.__connection

    def set_task_name(self, name):
        """
        Set task name

        :param name:
        :return:
        """
        if name is None:
            name = self.__class__.__name__
        self.TASK_NAME = name

    def get_task_name(self):
        """
        Get task name and use as key to lock or release task
        :return:
        """
        if self.TASK_NAME is None:
            self.TASK_NAME = self.__class__.__name__
        return self.TASK_NAME

    def get_args(self, **kwargs):
        """
        Get argruments for cronjob, this should be overrode in subclass
        :param kwargs:
        :return:
        """
        return {
            'task_name': self.TASK_NAME,
            'exchange': None,
            'exchange_type': None,
            'queue': None,
            'routing_key': None,
            'event_type': None,
        }

    def is_running_task(self, key=None, timeout=None):
        """
        Check if the task is running or not

        :param key: should be task name
        :param timeout:
        :return:
        """
        if key is None:
            key = self.get_task_name()
        if timeout is None:
            timeout = self.__timeout
        # No running task
        begin_timestamp = task_cache.get(key)
        if begin_timestamp is None:
            return False

        # Timed out task
        current_timestamp = timezone.now().timestamp()
        if current_timestamp - begin_timestamp > timeout:
            return False
        logger.info('Running | task: {}'.format(key))
        return True

    def lock_task(self, key=TASK_NAME, timeout=None):
        """
        Lock a task as running

        :param key:
        :param timeout:
        :return:
        """
        if key is None:
            key = self.get_task_name()
        if timeout is None:
            timeout = self.__timeout
        task_cache.set(key, timezone.now().timestamp(), timeout)
        if task_cache.get(key, None) is None:
            logger.error('Cache service is not available')
            raise RuntimeError
        logger.info('Locked | task: {}'.format(key))

    def release_lock(self, key=TASK_NAME):
        """
        Release locked task
        :param key:
        :return:
        """
        if key is None:
            key = self.get_task_name()
        task_cache.delete(key)
        logger.info('release_lock | task: {}'.format(key))

    def get_list(self, task_name=None, exchange=None, exchange_type=None, queue=None, routing_key=None, event_type=None,
                 status=EventQueueModel.STATUS__OPENED, max_attempt=3, limit=None):
        """
        Get list of opened events

        :return: model list
        """

        query_params = {
            'attempt__lt': max_attempt,
        }
        if task_name is not None:
            query_params['task_name'] = task_name
        if exchange is not None:
            query_params['exchange'] = exchange
        if exchange_type is not None:
            query_params['exchange_type'] = exchange_type
        if queue is not None:
            query_params['queue'] = queue
        if routing_key is not None:
            query_params['routing_key'] = routing_key
        if event_type is not None:
            query_params['event_type'] = event_type
        if status is not None:
            query_params['status'] = status
        opened_list = EventQueueModel.objects.filter(**query_params)
        if limit is None:
            limit = self.__limit
        if limit is not None:
            opened_list = opened_list[:limit]
        logger.info('get_list | query_params: {} | number of records: {}'.format(query_params, len(opened_list)))
        return opened_list

    def close_event(self, event):
        """
        Close an event
        :param event: event need closing

        """
        affected_row = EventQueueModel.objects.filter(
            Q(pk=event.id) & ~Q(status=EventQueueModel.STATUS__CLOSED)
        ).update(status=EventQueueModel.STATUS__CLOSED, updated_at=timezone.now())
        logger.info(
            'close_event | task: {} | event_id: {} | affected_row: {}'.format(event.task_name, event.id, affected_row))
        return affected_row

    def is_closed(self, event):
        """
        Check if an event is closed or not
        :param event: event need checking
        :return: boolean
        """
        return event.status == EventQueueModel.STATUS__CLOSED

    def process(self, event):
        """
        Main process for event should be overrode in subclass
        :param event:
        :return:
        """
        if self.is_closed(event):
            return False
        return True

    def make_connection(self, connection_config=None):
        """
        Connect to a host
        :param connection_config:
        :type connection_config: dict
        :return:
        """
        if connection_config is None:
            connection_config = self.__default_connection_config
        self.__default_connection_config.update(connection_config)
        self.__connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=self.__default_connection_config['host'],
                virtual_host=self.__default_connection_config['vhost'],
                port=self.__default_connection_config['port'],
                credentials=pika.credentials.PlainCredentials(
                    username=self.__default_connection_config['username'],
                    password=self.__default_connection_config['password'],
                )
            )
        )
        return self.__connection

    def create_channel(self):
        if self.__channel is not None:
            self.__channel.close()
        self.__channel = self.__connection.channel()

    def get_channel(self):
        if self.__channel is None:
            self.__channel = self.__connection.channel()
        return self.__channel

    def close_channel(self):
        try:
            self.__channel.close()
        except:
            pass
        finally:
            self.__channel = None

    def close_connection(self):
        """
        Close AMQP connection
        :return:
        """
        try:
            self.__connection.close()
        except:
            pass
        finally:
            self.__connection = None

    def __call__(self, **kwargs):
        self.handle(**kwargs)

    def handle(self, **kwargs):
        task_name = self.get_task_name()
        if self.is_running_task(key=task_name):
            return False
        try:
            self.lock_task(key=task_name)
            args = self.get_args(**kwargs)
            logger.info('get_args | task: {} | args: {}'.format(task_name, args))
            event_list = self.get_list(
                task_name=args.get('task_name', None),
                exchange=args.get('exchange', None),
                exchange_type=args.get('exchange_type', None),
                queue=args.get('queue', None),
                routing_key=args.get('routing_key', None),
                event_type=args.get('event_type', None),
                max_attempt=args.get('max_attempt', self.MAX_ATTEMPT),
                limit=args.get('limit', None)
            )
            if len(event_list) > 0:
                if kwargs.get('make_amqp_connection', True):
                    self.make_connection(kwargs.get('amqp_config', None))
                    self.create_channel()
                for event in event_list:
                    logger.info('get_list | task: {} | event_id: {}'.format(task_name, event.id))
                    if self.process(event):
                        self.close_event(event)
                    elif event.status == EventQueueModel.STATUS__OPENED:
                        # Fix compare int with CombinedExpression
                        event.refresh_from_db()
                        if event.attempt >= self.MAX_ATTEMPT:
                            event.status = EventQueueModel.STATUS__MAX_ATTEMPT
                            event.save()
                self.close_channel()
                self.close_connection()
        except:
            self.release_lock(task_name)
            raise
        self.release_lock(task_name)
        return True

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.__channel is not None:
            self.close_channel()
        if self.__connection is not None:
            self.close_connection()
