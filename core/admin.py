from django.contrib.admin import ModelAdmin, site
from core.models import Message, Game


class MessageAdmin(ModelAdmin):
    readonly_fields = ('timestamp', )
    search_fields = ('id', 'body', 'room', 'user__username')
    list_display = ('id', 'user', 'room', 'timestamp', 'characters')
    list_display_links = ('id', )
    list_filter = ('user', 'room')
    date_hierarchy = 'timestamp'


site.register(Message, MessageAdmin)
site.register(Game)
