from django.contrib import admin

# Register your models here.
from event_queue.models import EventQueueModel


class EventQueueModelAdmin(admin.ModelAdmin):
    actions = None
    empty_value_display = '-empty-'
    list_display = (
        'id',
        'exchange',
        'exchange_type',
        'queue',
        'correlation_id',
        'payload',
        'event_type',
        'attempt',
        'status',
        'created_at',
        'updated_at',
    )
    readonly_fields = list_display
    fieldsets = [
        (None, {'fields': list_display}),
    ]
    list_display_links = None

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(EventQueueModel, EventQueueModelAdmin)
