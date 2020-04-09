from core import consumers
# from django.conf.urls import url
from django.urls import re_path

websocket_urlpatterns = [
    re_path(r'ws/room/(?P<room>\w+)/$', consumers.ChatConsumer)
    # url(r'^ws$', consumers.ChatConsumer),
]
