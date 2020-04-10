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

CMD_HELP = 'help'
CMD_JOIN = 'join'
CMD_SUBMIT_WORD = 'submit'
CMD_START_TURN = 'start'
CMD_LIST_WORDS = 'mywords'
CMD_CLEAR_WORDS = 'clearwords'
CMD_SKIP_WORD = 'skip'
CMD_LEAVE_TEAM = 'leave'
CMD_CURRENT_GIVER = 'upnow'
CMD_NEXT_GIVER = 'upnext'
CMD_REMOVE_PLAYER = 'remove'
CMD_SET_CONFIG = 'set'
CMD_GET_CONFIG = 'settings'

ERR_TOO_LONG = "too long"


def get_help():
    out = """Commands: <br />
/join [red or blue] <br />
/submit [word, goes into fishbowl!]<br />
/mywords    <--- see what you submitted <br />
/clearwords <--- erases your words <br />
/skip       <--- if you are clue giving, skip to next word <br />
/upnext     <--- see the current clue givers <br />
/upnext     <--- see the next clue givers <br />
/leave      <--- leave the game (removes you from either team) <br />
/remove     <--- removes yourself from either team <br /> 
/remove [name] <--- removes [name] from either team <br /> 
/set [option] [value]  <- set the max_word_length, turn_length or red_giver/blue_giver  <br />
/settings   <- see current game settings
    """
    return out


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
    if command == CMD_HELP:
        msg = get_help()
        notify_ws_clients_private(room, msg, request.user.username)
    elif command == CMD_JOIN:
        name, team = add_player_to_team(room, game, request.user, cmd_args)
        msg = "added {} to {}".format(name, team)
        utils.notify_ws_game_update(room, msg, request.user.username, game=game)
    elif command == CMD_LIST_WORDS:
        word_list = get_player_words(room, game, request.user)
        msg = "Your words: {}".format(", ".join(word_list))
        notify_ws_clients_private(room, msg, request.user.username)
    elif command == CMD_CLEAR_WORDS:
        num_deleted = clear_player_words(room, game, request.user)
        msg = "Erased all {} of your words.".format(num_deleted)
        notify_ws_clients_private(room, msg, request.user.username)
        utils.notify_ws_game_update(room, None, None)
    elif command == CMD_SUBMIT_WORD:
        text, created = submit_player_word(room, game, request.user, cmd_args)
        if not text:
            return JsonResponse({"success": False})
        if created == ERR_TOO_LONG:
            msg = "Too long! max length: {}".format(game.max_word_length)
        elif created is True:
            msg = "Added word: \"{}\"".format(text)
        else:
            msg = "You've already submitted \"{}\"".format(text)
        notify_ws_clients_private(room, msg, request.user.username)
        utils.notify_ws_game_update(room, None, request.user.username, game=game)
    elif command == CMD_START_TURN:
        if not game.is_live_turn:
            utils.notify_ws_game_update(room, "Starting Round...", None)
            # loop = asyncio.get_event_loop()
            # loop.create_task(turn_countdown(room))
            asyncio.run(turn_countdown(room))
    elif command == CMD_SKIP_WORD:
        if request.user == game.clue_giver().user and game.is_live_turn:
            game.next_word()
            msg = "Skipping... new word."
            utils.notify_ws_game_update(room, msg, request.user.username)
        else:
            msg = "Only the giver can /skip during a live turn!"
            notify_ws_clients_private(room, msg, request.user.username)
    elif command == CMD_CURRENT_GIVER:
        msg = "Current Red: {}, Current Blue: {}".format(game.red_giver, game.blue_giver)
        notify_ws_clients_private(room, msg, request.user.username)
    elif command == CMD_NEXT_GIVER:
        msg = "Next Red: {}, next Blue: {}".format(*game.next_clue_givers())
        notify_ws_clients_private(room, msg, request.user.username)
    elif command == CMD_LEAVE_TEAM:
        msg, success = remove_player(room, game, request.user, cmd_args)
        utils.notify_ws_game_update(room, msg, None, game=game)
    elif command == CMD_REMOVE_PLAYER:
        msg, success = remove_player(room, game, request.user, cmd_args)
        if success:
            utils.notify_ws_game_update(room, msg, None, game=game)
        else:
            notify_ws_clients_private(room, msg, request.user.username)
    elif command == CMD_SET_CONFIG:
        msg = set_game_config(room, game, request.user, cmd_args)
        notify_ws_clients_private(room, msg, request.user.username)
        utils.notify_ws_game_update(room, None, None)
    elif command == CMD_GET_CONFIG:
        msg = get_game_config(room, game, request.user)
        notify_ws_clients_private(room, msg, request.user.username)
    else:
        notify_ws_clients_private(room, "Unknown command: '/{}'".format(command),
                                  request.user.username)

    # TODO: make this a more useful json response
    return JsonResponse({"success": True})


def notify_ws_clients_private(room, message_text, user):
    """ Inform one client there is a new message (for commands) """
    print("in notify_ws_clients_private")
    event = utils.make_message_event(room, message_text, private=True, submitter=user)
    channel_layer = get_channel_layer()
    room_group_name = utils.get_group(room)
    print("sending", event, "to ", room_group_name)
    async_to_sync(channel_layer.group_send)(room_group_name, event)
    return True


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
        if len(text) > game.max_word_length:
            print("TOO LONG")
            return text, ERR_TOO_LONG

        player, created_game = models.Player.objects.get_or_create(game=game, user=user)

        word, created_word = models.Word.objects.get_or_create(player=player, text=text)
        return text, created_word
    except Exception as e:
        print(e)
        return text, False


def remove_player(room, game, request_user, cmd_args):
    if len(cmd_args) < 1 or not cmd_args[0]:
        user_to_remove = request_user
        player = models.Player.objects.get(game=game, user=user_to_remove)
    else:
        try:
            player = models.Player.objects.get(game=game, user__username=cmd_args[0])
            user_to_remove = player.user
        except Exception:
            return ("Failed to remove {}".format(cmd_args[0]), False)

    # track how many words
    num_words = models.Word.objects.filter(player=player).count()
    player.team = None
    player.save(update_fields=["team"])

    to_remove_str = user_to_remove.username if user_to_remove != request_user else "themself"
    msg = "{} removed {} from the game ".format(request_user.username, to_remove_str)
    if num_words > 0:
        msg += " (but left {} words in the bowl)".format(num_words)
    return msg, True


def set_game_config(room, game, user, cmd_args):
    try:
        if cmd_args[0].lower() == "turn_length":
            game.turn_length = int(cmd_args[1])
            game.save()
        elif cmd_args[0].lower() == "max_word_length":
            game.max_word_length = int(cmd_args[1])
            game.save()
        elif cmd_args[0].lower() == "red_giver":
            try:
                player = models.Player.objects.get(game=game, user__username=cmd_args[1])
                if player.team != models.RED_TEAM_NAME:
                    return "Can't set a blue player to red_giver !"
                game.red_giver = player
                game.save()
            except Exception as e:
                print(e)
                return "Errored: {}".format(e)
        elif cmd_args[0].lower() == "blue_giver":
            try:
                player = models.Player.objects.get(game=game, user__username=cmd_args[1])
                if player.team != models.BLUE_TEAM_NAME:
                    return "Can't set a red player to blue_giver !"
                game.blue_giver = player
                game.save()
            except Exception as e:
                print(e)
                return "Errored: {}".format(e)
        else:
            return "Unknown argument"
    except Exception as e:
        print(e)
        return "Errored: {}".format(e)
    return "Success: set {} to {}".format(cmd_args[1], cmd_args[0])


def get_game_config(room, game, user):
    return "Turn length: {}, Max word length: {}".format(game.turn_length, game.max_word_length)


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
        game.end_round(time_left)
        success = utils.notify_ws_game_update(room, msg, None, game=game)
    else:
        msg = "Time's up for Team {}!!".format(game.current_guessing_team)
        game.end_turn()
        success = utils.notify_ws_game_update(room, msg, None, game=game)


class ChatView(TemplateView):
    template_name = 'core/chat.html'

    @property
    def room(self):
        return self.kwargs['room']
