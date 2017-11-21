# Event Queue

*Current version:* 0.1.0 (dev)

## Requirements

1. Using cache (memcache, redis,... )
2. Python 3

## Installation

Run `pip install django-event-queue`

### Add settings

```python
# settings.py

INSTALLED_APPS = [
    ...,
    'event_queue',
]

# example cache settings
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
        'TIMEOUT': 300,
    }
}

```

### Run migrate data

`python manage.py migrate`

## Example

### Long Polling

Exmaple of a custom command.

```python
# management/commands/long_poll.py
from django.core.management import BaseCommand

from event_queue.long_poll import LongPoll


class Command(BaseCommand):
    help = 'Event Queue Long Polling'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        long_poll = LongPoll(exchange=None, username='rabbitmq', password='rabbitmq', vhost='localhost',
                             queue_name='long_poll')
        long_poll()

```

### Event processing

```python
class PrintBody(QueueProcessFacade):
    TASK_NAME = 'PrintBody'

    def process(self, event):
        """
        Main process for event should be overrode in subclass
        :param event:
        :return:
        """
        if self.is_closed(event):
            return False
        print(event.payload)
        return True
```