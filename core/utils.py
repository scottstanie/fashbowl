import datetime
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
# from rest_framework.renderers import JSONRenderer


def game_to_dict(game):
    from .serializers import GameSerializer
    gs = GameSerializer(game)
    return gs.data
    # return JSONRenderer().render(gs.data)


def make_message_event(
    room,
    message_text,
    user="Admin",
    admin=True,
    type_="receive_private_message",
    submitter=None,
    private=True,
    game=None,
):
    """Direct message (no db saved Message object)
    Can be public or private
    message_text of None leads to just a game update
    """
    message = {
        "body": message_text,
        "user": "Admin",
        "timestamp": datetime.datetime.now().timestamp(),
        "room": room,
    }

    event = {
        "type": type_,
        "message": message,
        "submitter": submitter,
        "private": private,
        "admin": admin,
    }
    if game is not None:
        event["game_state"] = game_to_dict(game)
    return event


def get_group(room):
    room_group_name = "room_group_{}".format(room)
    return room_group_name


def notify_ws_game_update(room, message_text, user, game=None):
    """ Inform clients there is a game state update (with possible message)
     used by commands """
    event = make_message_event(room,
                               message_text,
                               private=False,
                               submitter=user,
                               type_="game_update",
                               game=game)
    print("in notify_ws_game_update, event:", event)
    channel_layer = get_channel_layer()
    room_group_name = get_group(room)
    async_to_sync(channel_layer.group_send)(room_group_name, event)
    return True