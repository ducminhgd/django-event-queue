from django.db import models


class EventQueueModel(models.Model):
    TYPE__UNKNOWN = 0
    TYPE__RECEIVE = 1
    TYPE__SEND = 2

    TYPE_CHOICES = (
        (TYPE__UNKNOWN, 'Unknown'),
        (TYPE__RECEIVE, 'Receive'),
        (TYPE__SEND, 'Send'),
    )

    STATUS__OPENED = 0
    STATUS__CLOSED = 1
    STATUS__CANCELLED = 2

    STATUS_CHOICES = (
        (STATUS__OPENED, 'Opened'),
        (STATUS__CLOSED, 'Closed'),
    )

    id = models.BigAutoField(primary_key=True)
    task_name = models.CharField(max_length=50, null=True)
    exchange = models.CharField(max_length=50, null=True)
    exchange_type = models.CharField(max_length=50, null=True)
    queue = models.CharField(max_length=50, null=True)
    routing_key = models.CharField(max_length=50, null=True)
    correlation_id = models.CharField(max_length=36, null=True)
    payload = models.TextField(null=True)
    event_type = models.PositiveSmallIntegerField(default=TYPE__UNKNOWN, choices=TYPE_CHOICES)
    attempt = models.PositiveIntegerField(default=0, auto_created=True, null=False)
    status = models.PositiveSmallIntegerField(default=STATUS__OPENED, null=False, choices=STATUS_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        db_table = 'event_queue'
