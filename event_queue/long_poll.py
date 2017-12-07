import logging

import pika
import sys

from event_queue import utils
from event_queue.models import EventQueueModel

logger = logging.getLogger('main')


class LongPoll(object):
    __task_name = None
    __connection = None
    __channel = None
    __exchange = None
    __exchange_type = None

    __username = None
    __password = None
    __host = None
    __port = 5672
    __vhost = '/'
    __queue_name = ''
    __routing_key = None

    def __init__(self, task_name=None, host='localhost', port=5672, username='guest', password='guest', vhost='/',
                 routing_key=None, queue_name=None, exchange='', exchange_type=None):
        self.__task_name = task_name

        self.__host = host
        self.__port = port
        self.__username = username
        self.__password = password
        self.__vhost = vhost

        self.__exchange = exchange
        self.__exchange_type = exchange_type
        self.__queue_name = queue_name
        self.__routing_key = routing_key

    def connect(self):
        """
        Connect to Queue
        :return:
        """
        params = pika.ConnectionParameters(
            host=self.__host,
            port=self.__port,
            virtual_host=self.__vhost,
            credentials=pika.credentials.PlainCredentials(
                username=self.__username,
                password=self.__password
            )
        )
        logger.info('[Connecting] {}:{}/{}'.format(self.__host, self.__port, self.__vhost))
        self.__connection = pika.BlockingConnection(parameters=params)
        logger.info(
            '[Declare] exchange: {} | exchange_type: {} | queue_name: {} | routing_key: {}'.format(self.__exchange,
                                                                                                   self.__exchange_type,
                                                                                                   self.__queue_name,
                                                                                                   self.__routing_key))

        self.__channel = self.__connection.channel()
        self.__channel.queue_declare(queue=self.__queue_name, durable=True, exclusive=False, auto_delete=False)
        if self.__routing_key is not None:
            self.__channel.queue_bind(queue=self.__queue_name, routing_key=self.__routing_key,
                                      exchange=self.__exchange_type)
        self.__channel.basic_qos()

    def listening(self):
        """
        Begin consuming

        """
        if self.__connection is None:
            self.connect()
        self.__channel.basic_consume(consumer_callback=self.callback, queue=self.__queue_name)
        logger.info('[Consuming] queue_name'.format(self.__queue_name))
        self.__channel.start_consuming()

    def callback(self, ch, method, props, body):
        """
        Callback function, can be overrode
        :param ch:
        :param method:
        :param props:
        :param body:
        :return:
        """
        inserted = self.insert_event(
            task_name=self.__task_name,
            exchange=method.exchange,
            exchange_type=self.__exchange_type,
            correlation_id=props.correlation_id,
            payload=body,
            queue=self.__queue_name,
            routing_key=method.routing_key,
        )
        ch.basic_ack(delivery_tag=method.delivery_tag)
        return inserted

    def close(self):
        """
        Close connection
        :return:
        """
        logger.info('[Closing]')
        if self.__connection is not None:
            self.__connection.close()
        self.__connection = None
        logger.info('[Closed]')

    def insert_event(self, task_name=None, exchange=None, exchange_type=None, correlation_id=None, payload=None,
                     queue=None,
                     routing_key=None, event_type=EventQueueModel.TYPE__RECEIVE):
        event = EventQueueModel(
            task_name=task_name,
            exchange=exchange,
            exchange_type=exchange_type,
            queue=queue,
            routing_key=routing_key,
            correlation_id=correlation_id,
            payload=payload,
            event_type=event_type,
            attempt=0,
            status=EventQueueModel.STATUS__OPENED,
        )
        event.save()
        return event

    def __call__(self, *args, **kwargs):
        try:
            self.connect()
            self.listening()
        except:
            self.close()
            raise sys.exc_info()
