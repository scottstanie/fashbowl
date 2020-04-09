import time
import asyncio
from django.views.generic import TemplateView
from django.db.models import Count
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from channels.layers import get_channel_layer
from channels.db import database_sync_to_async
from asgiref.sync import async_to_sync

from . import models
from . import utils
# from pprint import pprint
CMD_JOIN = 'join'
CMD_SUBMIT_WORD = 'submit'
CMD_START_TURN = 'start'
CMD_LIST_WORDS = 'mywords'
CMD_CLEAR_WORDS = 'clearwords'


@require_http_methods(["GET"])
def game_users(request, room):
    # room = request.GET.get('room')
    game, created_game = models.Game.objects.get_or_create(room=room)
    pqueryset = models.Player.objects.filter(game=game).annotate(word_count=Count('word'))
    # player_names = [p.user.username for p in pqueryset]
    # print("in ", room, "player list:", pqueryset)

    red_team = [(p.user.username, p.word_count) for p in pqueryset
                if p.team == models.RED_TEAM_NAME]
    blue_team = [(p.user.username, p.word_count) for p in pqueryset
                 if p.team == models.BLUE_TEAM_NAME]

    # Get number of words submitted per user
    return JsonResponse(dict(
        success=True,
        red_team=red_team,
        blue_team=blue_team,
    ))


@require_http_methods(["POST"])
def command(request):
    print("COMMAND view:")
    room = request.POST.get('room')
    game, created_game = models.Game.objects.get_or_create(room=room)
    message = request.POST.get('body')
    command, *cmd_args = message.split(' ')
    # TODO: maybe other cleaning of comands
    command = command.replace("'", "").replace('"', '').strip('/')
    print('room, game, command, cmd_args, request.user')
    print(room, game, command, cmd_args, request.user)
    if command == CMD_JOIN:
        name, team = add_player_to_team(room, game, request.user, cmd_args)
        msg = "added {} to {}".format(name, team)
        success = utils.notify_ws_game_update(room, msg, request.user.username)
    elif command == CMD_LIST_WORDS:
        word_list = get_player_words(room, game, request.user)
        msg = "Your words: {}".format(", ".join(word_list))
        success = notify_ws_clients_private(room, msg, request.user.username)
    elif command == CMD_CLEAR_WORDS:
        num_deleted = clear_player_words(room, game, request.user)
        msg = "Erased all {} of your words.".format(num_deleted)
        notify_ws_clients_private(room, msg, request.user.username)
        success = utils.notify_ws_game_update(room, None, None)
    elif command == CMD_SUBMIT_WORD:
        text, created = submit_player_word(room, game, request.user, cmd_args)
        if not text:
            return JsonResponse({"success": False})
        if created is True:
            msg = "Added word: \"{}\"".format(text)
        else:
            msg = "You've already submitted \"{}\"".format(text)
        success = notify_ws_clients_private(room, msg, request.user.username)
        success = utils.notify_ws_game_update(room, None, request.user.username)
    elif command == CMD_START_TURN:
        utils.notify_ws_game_update(room, "Starting Round...", None)
        # loop = asyncio.get_event_loop()
        # loop.create_task(turn_countdown(room))
        asyncio.run(turn_countdown(room))
        success = True
    else:
        notify_ws_clients_private(room, "Unknown command: '/{}'".format(command),
                                  request.user.username)
        success = False

    # TODO: make this a more useful json response
    return JsonResponse({"success": success})


def notify_ws_clients_private(room, message_text, user):
    """ Inform one client there is a new message (for commands) """
    print("in notify_ws_clients_private")
    event = utils.make_message_event(room, message_text, private=True, submitter=user)
    channel_layer = get_channel_layer()
    room_group_name = utils.get_group(room)
    print("sending", event, "to ", room_group_name)
    async_to_sync(channel_layer.group_send)(room_group_name, event)
    return True


def notify_ws_start_turn(room):
    print("in notify_ws_start_turn")
    channel_layer = get_channel_layer()
    room_group_name = utils.get_group(room)
    message = {"starting": True}
    event = {
        # 'type': 'receive_game_update',
        'type': 'start_turn',
        'message': message,
    }
    async_to_sync(channel_layer.group_send)(room_group_name, event)


def add_player_to_team(room, game, user, cmd_args):
    team = cmd_args[0]
    team_names = [t[1] for t in models.TEAM_CHOICES]
    if team not in team_names:
        print(team, "not in choices:", team_names)
        return False
    player, created_player = models.Player.objects.get_or_create(game=game, user=user)
    player.team = team
    player.save()
    return player.user.username, team


def get_player_words(room, game, user):
    try:
        player, created_player = models.Player.objects.get_or_create(game=game, user=user)
        word_list = models.Word.objects.filter(player=player)
        return [w.text for w in word_list]
    except Exception as e:
        print(e)
        return False


def clear_player_words(room, game, user):
    try:
        player, created_player = models.Player.objects.get_or_create(game=game, user=user)
        del_count, del_dict = models.Word.objects.filter(player=player).delete()
        return del_count
    except Exception as e:
        print(e)
        return False


def submit_player_word(room, game, user, cmd_args):
    try:
        text = ' '.join(cmd_args)
        if not text:
            return text, False

        player, created_game = models.Player.objects.get_or_create(game=game, user=user)

        word, created_word = models.Word.objects.get_or_create(player=player, text=text)
        return text, created_word
    except Exception as e:
        print(e)
        return text, False


async def turn_countdown(room):
    print("start turn_countdown")
    channel_layer = get_channel_layer()
    room_group_name = "room_group_{}".format(room)

    game, _ = await get_room_async(room)
    if game.is_live_turn:
        print("ALREADY LIVE!")
        return
    await database_sync_to_async(game.start_turn)()
    game_state = utils.game_to_dict(game)
    turn_length = game.turn_length if game.remaining_seconds <= 0 else game.remaining_seconds
    start_time = game.turn_start_timeint
    # turn_length = 10
    # start_time = time.time() - 1
    turn_time_elapsed = time.time() - start_time
    time_left = int(round(turn_length))

    msg_text = None
    event = utils.make_message_event(room,
                                     msg_text,
                                     private=False,
                                     submitter=None,
                                     type_="game_update")

    not_finished = True
    while turn_time_elapsed < turn_length and not_finished:
        game, is_round_done = await get_room_async(room)
        game_state = utils.game_to_dict(game)
        not_finished = game.is_live_turn and len(game.remaining_words()) > 0
        turn_time_elapsed = time.time() - start_time

        # Send more readable time_left to users
        time_left = int(round(turn_length - turn_time_elapsed))
        game_state['time_left'] = time_left
        event['game_state'] = game_state
        print("time left", time_left)

        await channel_layer.group_send(
            room_group_name,
            event,
        )
        await asyncio.sleep(.4)

    print("Broke out of countdown loop")
    await check_final_state(room, time_left)


@database_sync_to_async
def get_room_async(room):
    g = models.Game.objects.get(room=room)
    return g, g.is_round_done()


@database_sync_to_async
def check_final_state(room, time_left):
    print("check_final_state")
    game = models.Game.objects.get(room=room)
    if game.is_round_done():
        print("round done")
        msg = "Thats the end of round {}!!".format(game.current_round)
        success = utils.notify_ws_game_update(room, msg, None)
        game.end_round(time_left)
    else:
        msg = "Time's up for Team {}!!".format(game.current_guessing_team)
        success = utils.notify_ws_game_update(room, msg, None)
        game.end_turn()


class ChatView(TemplateView):
    template_name = 'core/chat.html'

    @property
    def room(self):
        return self.kwargs['room']
