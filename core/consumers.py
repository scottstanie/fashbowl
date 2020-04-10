# fashbowl/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from pprint import pprint
from . import utils


class ChatConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Obtains the 'room_name' parameter from the URL route in chat/routing.py
        that opened the WebSocket connection to the consumer. Every consumer has
        a scope that contains information about its connection, including in
        particular any positional or keyword arguments from the URL route and
        the currently authenticated user if any.
        """
        # pprint("INIT:")
        # pprint(self.scope)
        # url_route come sfrom the .js socket opening (see routing for param)
        self.room_name = self.scope['url_route']['kwargs']['room']
        # Constructs a Channels group name directly from the user-specified room name
        # will fail on room names that have letters, digits, hyphens, and periods
        self.room_group_name = 'room_group_%s' % self.room_name

    async def connect(self):
        # pprint("connect: ChatConsumer")
        # print("self.scope")
        # pprint(self.scope['user'])

        # user_id = self.scope["session"]["_auth_user_id"]
        # self.group_name = "{}".format(user_id)
        # Join room group
        # print("self.room_group_name:", self.room_group_name)
        # print("self.channel_name:", self.channel_name)

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        msg = "{} has entered the room.".format(self.scope["user"].username)
        event = utils.make_message_event(self.room_name, msg, private=False, type_="game_update")
        await self.channel_layer.group_send(self.room_group_name, event)
        await self.accept()

    async def disconnect(self, close_code):
        # print("disconnect")
        # Leave room group
        msg = "{} has left the room.".format(self.scope["user"].username)
        event = utils.make_message_event(self.room_name, msg, private=False, type_="game_update")
        await self.channel_layer.group_send(self.room_group_name, event)
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    # Receive message from WebSocket
    async def receive(self, text_data=None, bytes_data=None):
        # print("chatconsumer receive:")
        # print("self.scope")
        pprint(self.scope)

        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        # Send message to room group
        # print('room group name', self.room_group_name)
        await self.channel_layer.group_send(self.room_group_name, {
            'type': 'receive_group_message',
            'message': message
        })

    async def receive_group_message(self, event):
        message_id = event['message_id']
        # print("chatconsumer receive_group_message")
        # print("event:", event)

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message_id': message_id,
        }))

    async def receive_private_message(self, event):
        # print("chatconsumer receive_private_message:")
        # print("event:", event)
        # Send message to WebSocket
        await self.send(text_data=json.dumps(event))

    async def game_update(self, event):
        # print("chatconsumer game_update:")
        event["game_update"] = True
        await self.send(text_data=json.dumps(event))
