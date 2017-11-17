import pika
import sys

from event_queue.models import EventQueueModel


class LongPoll(object):
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

    def __init__(self, host='localhost', port=5672, username='guest', password='guest', vhost='/', queue_name=None,
                 exchange='', exchange_type=None):
        self.__exchange = exchange
        self.__exchange_type = exchange_type
        self.__host = host
        self.__port = port
        self.__username = username
        self.__password = password
        self.__vhost = vhost
        self.__queue_name = queue_name

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
        self.__connection = pika.BlockingConnection(parameters=params)
        self.__channel = self.__connection.channel()
        self.__channel.queue_declare(queue=self.__queue_name, durable=True, exclusive=False, auto_delete=False)
        self.__channel.basic_qos()

    def listening(self):
        """
        Begin consuming

        """
        if self.__connection is None:
            self.connect()
        self.__channel.basic_consume(consumer_callback=self.callback, queue=self.__queue_name)
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
            exchange=method.exchange,
            exchange_type=self.__exchange_type,
            correlation_id=props.correlation_id,
            payload=body,
            queue=method.routing_key,
        )
        print(body)

    def close(self):
        """
        Close connection
        :return:
        """
        if self.__connection is not None:
            self.__connection.close()
        self.__connection = None

    def insert_event(self, exchange=None, exchange_type=None, correlation_id=None, payload=None, queue=None,
                     event_type=EventQueueModel.TYPE__RECEIVE):
        try:
            event = EventQueueModel(
                exchange=exchange,
                exchange_type=exchange_type,
                queue=queue,
                correlation_id=correlation_id,
                payload=payload,
                event_type=event_type,
                attempt=0,
                status=EventQueueModel.STATUS__OPENED,
            )
            event.save()
            return event.id > 0
        except:
            return False

    def __call__(self, *args, **kwargs):
        try:
            self.connect()
            self.listening()
        except:
            exc_info = sys.exc_info()
            self.close()
