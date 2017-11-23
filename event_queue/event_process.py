import logging
import sys
from django.core.cache import caches
from django.utils import timezone

from event_queue import utils
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
    TIMEOUT = 1

    def __init__(self, task_name=None):
        self.set_task_name(task_name)

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
            timeout = self.TIMEOUT
        # No running task
        begin_timestamp = task_cache.get(key)
        if begin_timestamp is None:
            return False

        # Timed out task
        current_timestamp = timezone.now().timestamp()
        if current_timestamp - begin_timestamp > timeout:
            return False
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
            timeout = self.TIMEOUT
        task_cache.set(key, timezone.now().timestamp(), timeout)

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
                 status=EventQueueModel.STATUS__OPENED):
        """
        Get list of opened events

        :return: model list
        """

        query_params = {}
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
        logger.info('get_list | task: {} | query_params: {}'.format(task_name, query_params))
        opened_list = EventQueueModel.objects.filter(**query_params)
        return opened_list

    def closed_event(self, event):
        """
        Close an event
        :param event: event need closing

        """
        logger.info('closed_event | task: {} | event_id: {}'.format(event.task_name, event.id))
        event.status = EventQueueModel.STATUS__CLOSED
        event.updated_at = timezone.now()
        event.save()

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

    def __call__(self, **kwargs):
        try:
            task_name = self.get_task_name()
            if self.is_running_task(key=task_name):
                logger.info('Running | task: {}'.format(task_name))
                return False
            self.lock_task(key=task_name)
            logger.info('Locked | task: {}'.format(task_name))
            args = self.get_args(**kwargs)
            logger.info('get_args | task: {} | args: {}'.format(task_name, args))
            event_list = self.get_list(
                task_name=args['task_name'],
                exchange=args['exchange'],
                exchange_type=args['exchange_type'],
                queue=args['queue'],
                routing_key=args['routing_key'],
                event_type=args['event_type']
            )
            for event in event_list:
                logger.info('get_list | task: {} | event_id: {}'.format(task_name, event.id))
                if self.process(event):
                    self.closed_event(event)
            self.release_lock(task_name)
            return True
        except:
            exc_info = utils.format_exc_info(sys.exc_info())
            logger.info('exception: {}'.format(exc_info))
        return False
