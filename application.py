import os
import itertools
from threading import Lock
import copy
from flask import Flask, render_template, request, jsonify, g
from flask_socketio import SocketIO, emit, join_room, leave_room
# import json
import sqlite3
from collections import defaultdict
import random

thread = None
thread_lock = Lock()
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
socketio = SocketIO(app)

# Channel Data Global Variables
channel_list = {"general": []}
present_channel = {"initial": "general"}

# SUBMITTED_WORDS[channel][user]:
# SUBMITTED_WORDS = defaultdict(lambda: defaultdict(str))
SUBMITTED_WORDS = defaultdict(str)

# TODO: add scoreboard, add CLEAR ALL button

BLUE_TEAM = "blue"
RED_TEAM = "red"
IS_ROUND_DONE = False
# Team data: points and team members
# # TEAM_MEMBERS[channel]["red"] = {"user 1", ...}
# TEAM_MEMBERS = defaultdict(lambda: defaultdict(set))
# # TEAM_POINTS[channel]["blue"] = 1
# TEAM_POINTS = defaultdict(lambda: defaultdict(int))

# TEAM_MEMBERS["red"] = {"user 1", ...}
TEAM_MEMBERS = defaultdict(set)
# TEAM_POINTS["blue"] = 1
TEAM_POINTS = defaultdict(int)
RED_TEAM_CYCLE = None
BLUE_TEAM_CYCLE = None

# # CURRENT_ROUND[channel] = 1  OR 2, or 3
# CURRENT_ROUND = defaultdict(int)
IS_LIVE_ROUND = False
CURRENT_ROUND = 0
CLUE_GIVER = ""
ALL_WORDS = []
CURRENT_WORD = ""
GUESSED_WORDS = set()
GUESSING_TEAM = RED_TEAM

DATABASE = 'database.db'

# GAME STEPS:
# - everyone joins a room and submits their word. those who haven't
#   submitted a word are just spectators
# - divide the people in the chat room into two teams, red and blue
# - pick order of clue givers for each team
# - start round 1: timer goes off for 60 seconds, start random.choice on words
#       - here's where button shows up and they can skip


@app.route("/", methods=["POST", "GET"])
def index():
    if request.method == "GET":
        # Pass channel list to, and use jinja to display already created channels
        return render_template(
            "index.html",
            channel_list=channel_list,
        )

    elif request.method == "POST":
        channel = request.form.get("channel_name")
        user = request.form.get("username")

        # Adding a new channel
        if channel and (channel not in channel_list):
            channel_list[channel] = []
            return jsonify({"success": True})
        # Switching to a different channel
        elif channel in channel_list:
            # send channel specific data to client i.e. messages, who sent them/when
            # send via JSON response and then render with JS
            print(f"Switch to {channel}")
            present_channel[user] = channel
            channel_data = channel_list[present_channel[user]]
            return jsonify(channel_data)
        else:
            return jsonify({"success": False})


@socketio.on("create channel")
def create_channel(new_channel):
    emit("new channel", new_channel, broadcast=True)


@socketio.on("send message")
def send_message(message_data):
    global GUESSING_TEAM
    # print(channel_list)
    channel = message_data["current_channel"]
    channel_message_count = len(channel_list[channel])
    del message_data["current_channel"]
    channel_list[channel].append(message_data)
    message_data["deleted_message"] = False
    if (channel_message_count >= 100):
        del channel_list[channel][0]
        message_data["deleted_message"] = True

    emit("recieve message", message_data, broadcast=True, room=channel)
    # We're only checking for matching/scoring while the round is live
    if IS_LIVE_ROUND:
        message_content = message_data["message_content"]
        guess_result = check_guess(message_content)
        if guess_result is True:
            message_data["message_content"] = "Point for Team %s!!" % GUESSING_TEAM
            message_data["message_color"] = GUESSING_TEAM
            emit("recieve message", message_data, broadcast=True, room=channel)
            update_scoreboard()
            # m = "Score: Team Red: %s, Team blue: %s" % (TEAM_POINTS[RED_TEAM], TEAM_POINTS[BLUE_TEAM])
            # message_data["message_content"] = m
            # emit("recieve message", message_data, broadcast=True, room=channel)


@socketio.on("skip")
def skip_word():
    global CURRENT_WORD
    remaining_words = _get_remaining_words(exclude=CURRENT_WORD)
    print("Skipping word %s" % CURRENT_WORD)
    print("Choosing from ", remaining_words)
    CURRENT_WORD = random.choice(list(remaining_words))
    print("New word: %s" % CURRENT_WORD)


def update_scoreboard():
    global TEAM_POINTS
    print("Updating scoreboard:")
    print(TEAM_POINTS)
    emit(
        "score update",
        {
            "red": TEAM_POINTS[RED_TEAM],
            "blue": TEAM_POINTS[BLUE_TEAM]
        },
        broadcast=True,
    )


def _get_remaining_words(exclude=None):
    global ALL_WORDS, GUESSED_WORDS
    remaining_words = set.difference(set(ALL_WORDS), set(GUESSED_WORDS))
    if exclude is not None and set([exclude]) != remaining_words:  # ignore if 1 remains
        print("EXCLUDING", exclude, "from", remaining_words)
        remaining_words = set.difference(remaining_words, set([exclude]))
    return remaining_words


def check_guess(message_content):
    global ALL_WORDS, CURRENT_WORD, GUESSING_TEAM, GUESSED_WORDS, TEAM_POINTS, IS_ROUND_DONE
    print("GUESED!", message_content, CURRENT_WORD)
    if message_content.lower() == CURRENT_WORD.lower():
        print("RIGHT")
        TEAM_POINTS[GUESSING_TEAM] += 1
        GUESSED_WORDS.add(CURRENT_WORD)

        remaining_words = _get_remaining_words()
        print("all, guessed, remaining")
        print(ALL_WORDS, GUESSED_WORDS, remaining_words)
        if not remaining_words:
            CURRENT_WORD = "ALL DONE: ROUND OVER"
            IS_ROUND_DONE = True
        else:
            CURRENT_WORD = random.choice(list(remaining_words))
            IS_ROUND_DONE = False
        return True
    return False


# For writing down word at beginning and sticking in the fishbowl
@socketio.on("send word")
def send_word(message_data):
    global SUBMITTED_WORDS
    print(message_data)
    # channel = message_data["current_channel"]
    user = message_data["user"]

    # TODO: check here for bad word

    # if SUBMITTED_WORDS[channel][user]:
    SUBMITTED_WORDS[user] = message_data["submitted_word"]
    # emit("recieve word", message_data, broadcast=True, room=channel)
    print("submitted words:")
    print(SUBMITTED_WORDS)


@socketio.on("select team")
def select_team(message_data):
    print(message_data)
    # channel = message_data["current_channel"]
    user = message_data["user"]
    team = message_data["team"]

    # TEAM_MEMBERS[channel][team].add(user)
    TEAM_MEMBERS[team].add(user)
    other_team = RED_TEAM if team == BLUE_TEAM else BLUE_TEAM
    TEAM_MEMBERS[other_team].discard(user)
    # emit("recieve word", message_data, broadcast=True, room=channel)
    update_playerlist()


def update_playerlist():
    global TEAM_MEMBERS
    print("updating player list. teams:")
    print(TEAM_MEMBERS)
    emit(
        "player update",
        {
            "red": ",".join(TEAM_MEMBERS[RED_TEAM]),
            "blue": ",".join(TEAM_MEMBERS[BLUE_TEAM]),
        },
        broadcast=True,
    )


@socketio.on("start game")
def start_game():
    global ALL_WORDS, CLUE_GIVER, CURRENT_ROUND
    global CURRENT_WORD, GUESSED_WORDS, RED_TEAM_CYCLE, BLUE_TEAM_CYCLE
    print("start game")

    CURRENT_ROUND = 1
    RED_TEAM_CYCLE = itertools.cycle(
        random.sample(list(TEAM_MEMBERS["red"]), len(TEAM_MEMBERS["red"])))
    BLUE_TEAM_CYCLE = itertools.cycle(
        random.sample(list(TEAM_MEMBERS["blue"]), len(TEAM_MEMBERS["blue"])))
    if GUESSING_TEAM == RED_TEAM:
        CLUE_GIVER = next(RED_TEAM_CYCLE)
    else:
        CLUE_GIVER = next(BLUE_TEAM_CYCLE)

    red_words = set([w for name, w in SUBMITTED_WORDS.items() if name in TEAM_MEMBERS["red"]])
    blue_words = set([w for name, w in SUBMITTED_WORDS.items() if name in TEAM_MEMBERS["blue"]])
    ALL_WORDS = list(set.union(red_words, blue_words))
    CURRENT_WORD = random.choice(ALL_WORDS)

    # TODO: add socketio handler for teams, and display
    print("Start game:", CLUE_GIVER, CURRENT_ROUND, CURRENT_WORD, ALL_WORDS)
    start_round()


@socketio.on('start round')
def start_round():
    global thread, CURRENT_WORD
    print("START ROUND")
    CURRENT_WORD = random.choice(list(_get_remaining_words()))
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(round_countdown)
    thread = None


def round_countdown():
    """Example of how to send server generated events to clients."""
    global IS_LIVE_ROUND, GUESSING_TEAM, CLUE_GIVER
    IS_LIVE_ROUND = True
    count = 10
    while count > 0:
        socketio.sleep(1)
        print(count)
        count -= 1
        # if count % 10 != 0 and count < 50:
        # continue

        socketio.emit(
            'countdown',
            {
                'data': 'Countdown for round',
                'count': count,
                'current_round': CURRENT_ROUND,
                'current_word': CURRENT_WORD,
                'clue_giver': CLUE_GIVER,
            },
            namespace='',
        )
    print("round is NOT live")
    IS_LIVE_ROUND = False
    switch_guess_team()
    pass_clue_giver()

    if IS_ROUND_DONE:
        reset_round()


def switch_guess_team():
    global GUESSING_TEAM
    GUESSING_TEAM = RED_TEAM if GUESSING_TEAM == BLUE_TEAM else BLUE_TEAM


def pass_clue_giver():
    global CLUE_GIVER, GUESSING_TEAM
    if GUESSING_TEAM == RED_TEAM:
        CLUE_GIVER = next(RED_TEAM_CYCLE)
    else:
        CLUE_GIVER = next(BLUE_TEAM_CYCLE)


def reset_round():
    global CURRENT_ROUND, GUESSED_WORDS, CURRENT_WORD
    print("RESET ROUND")
    CURRENT_ROUND += 1
    CURRENT_WORD = ""
    GUESSED_WORDS = set()
    IS_ROUND_DONE = False


@socketio.on('reset')
def reset_all_game():
    # TODO: so studpid, just use a database dummy
    global IS_ROUND_DONE, IS_LIVE_ROUND, TEAM_MEMBERS, TEAM_POINTS, RED_TEAM_CYCLE
    global BLUE_TEAM_CYCLE, CURRENT_ROUND, CLUE_GIVER, ALL_WORDS, CURRENT_WORD
    global GUESSED_WORDS, GUESSING_TEAM
    print("Reseting all game data")

    IS_ROUND_DONE = False
    IS_LIVE_ROUND = False
    TEAM_MEMBERS = defaultdict(set)
    TEAM_POINTS = defaultdict(int)
    RED_TEAM_CYCLE = None
    BLUE_TEAM_CYCLE = None
    CURRENT_ROUND = 0
    CLUE_GIVER = ""
    ALL_WORDS = []
    CURRENT_WORD = ""
    GUESSED_WORDS = set()
    GUESSING_TEAM = RED_TEAM
    update_playerlist()
    update_scoreboard()


@socketio.on("delete channel")
def delete_channel(message_data):
    channel = message_data["current_channel"]
    user = message_data["user"]
    present_channel[user] = "general"
    del message_data["current_channel"]
    del channel_list[channel]
    channel_list["general"].append(message_data)
    message_data = {"data": channel_list["general"], "deleted_channel": channel}
    emit("announce channel deletion", message_data, broadcast=True)


@socketio.on("leave")
def on_leave(room_to_leave):
    print("leaving room")
    leave_room(room_to_leave)
    emit("leave channel ack", room=room_to_leave)


@socketio.on("join")
def on_join(room_to_join):
    print("joining room")
    join_room(room_to_join)
    emit("join channel ack", room=room_to_join)


# def connect_db():
#     return sqlite3.connect(DATABASE)
#
#
# @app.before_request
# def before_request():
#     g.db = connect_db()
#
#
# @app.teardown_request
# def teardown_request(exception):
#     if hasattr(g, 'db'):
#         g.db.close()
#
#
# def query_db(query, args=(), one=False):
#     cur = g.db.execute(query, args)
#     rv = [
#         dict((cur.description[idx][0], value) for idx, value in enumerate(row))
#         for row in cur.fetchall()
#     ]
#     return (rv[0] if rv else None) if one else rv
