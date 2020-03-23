import os

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

# submitted_words[channel][user]:
# submitted_words = defaultdict(lambda: defaultdict(str))
submitted_words = defaultdict(str)

BLUE_TEAM = "blue"
RED_TEAM = "red"
# Team data: points and team members
# TODO: team name instead of red/blue
# # team_members[channel]["red"] = {"user 1", ...}
# team_members = defaultdict(lambda: defaultdict(set))
# # team_points[channel]["blue"] = 1
# team_points = defaultdict(lambda: defaultdict(int))

# team_members["red"] = {"user 1", ...}
team_members = defaultdict(set)
# team_points["blue"] = 1
team_points = defaultdict(int)
red_team_order = None
blue_team_order = None

# # current_round[channel] = 1  OR 2, or 3
# current_round = defaultdict(int)
is_live_round = False
current_round = 0
clue_giver = ""
all_words = []
current_word = ""
guessed_words = set()
guessing_team = RED_TEAM

DATABASE = 'database.db'

# GAME STEPS:
# - everyone joins a room and submits their word. those who haven't
#   submitted a word are just spectators
# - divide the people in the chat room into two teams, red and blue
# - pick order of clue givers for each team
# - start round 1: timer goes off for 60 seconds, start random.choice on words
#       - here's where button shows up and they can skip


def connect_db():
    return sqlite3.connect(DATABASE)


@app.before_request
def before_request():
    g.db = connect_db()


@app.teardown_request
def teardown_request(exception):
    if hasattr(g, 'db'):
        g.db.close()


def query_db(query, args=(), one=False):
    cur = g.db.execute(query, args)
    rv = [
        dict((cur.description[idx][0], value) for idx, value in enumerate(row))
        for row in cur.fetchall()
    ]
    return (rv[0] if rv else None) if one else rv


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
    # print(channel_list)
    channel = message_data["current_channel"]
    channel_message_count = len(channel_list[channel])
    del message_data["current_channel"]
    channel_list[channel].append(message_data)
    message_data["deleted_message"] = False
    if (channel_message_count >= 100):
        del channel_list[channel][0]
        message_data["deleted_message"] = True

    if is_live_round:
        message_content = message_data["message_content"]
        check_guess(message_content)

    emit("recieve message", message_data, broadcast=True, room=channel)


def check_guess(message_content):
    global all_words, current_word, guessing_team, guessed_words
    print("GUESED!", message_content, current_word)
    if message_content.lower() == current_word.lower():
        print("RIGHT")
        team_points[guessing_team] += 1
        guessed_words.add(current_word)
        remaining_words = set.difference(set(all_words), set(guessed_words))
        print("all, remaining")
        print(all_words, remaining_words)
        if not remaining_words:
            current_word = "ALL DONE"
        else:
            current_word = random.choice(list(remaining_words))


@socketio.on("send word")
def send_word(message_data):
    print(message_data)
    # channel = message_data["current_channel"]
    user = message_data["user"]

    # TODO: check here for bad word

    # if submitted_words[channel][user]:
    submitted_words[user] = message_data["submitted_word"]
    # emit("recieve word", message_data, broadcast=True, room=channel)
    print("submitted words:")
    print(submitted_words)


@socketio.on("select team")
def select_team(message_data):
    print(message_data)
    # channel = message_data["current_channel"]
    user = message_data["user"]
    team = message_data["team"]

    # team_members[channel][team].add(user)
    team_members[team].add(user)
    other_team = RED_TEAM if team == BLUE_TEAM else BLUE_TEAM
    team_members[other_team].discard(user)
    # emit("recieve word", message_data, broadcast=True, room=channel)
    print("teams:")
    print(team_members)
    # TODO: add socketio handler for teams, and display
    # emit("recieve team", message_data, broadcast=True, room=channel)


@socketio.on("start game")
def start_game():
    global all_words, clue_giver, current_round, current_word, guessed_words
    print("start game")

    current_round = 1

    red_team_order = copy.deepcopy(list(team_members["red"]))
    blue_team_order = copy.deepcopy(list(team_members["blue"]))
    random.shuffle(red_team_order)
    random.shuffle(blue_team_order)
    if guessing_team == RED_TEAM:
        clue_giver = red_team_order[0]
    else:
        clue_giver = blue_team_order[0]

    red_words = set([w for name, w in submitted_words.items() if name in team_members["red"]])
    blue_words = set([w for name, w in submitted_words.items() if name in team_members["blue"]])
    all_words = list(set.union(red_words, blue_words))
    current_word = all_words[0]

    # TODO: add socketio handler for teams, and display
    print("Start game:", clue_giver, current_round, current_word, all_words)
    start_round()


@socketio.on('start')
def start_round():
    global is_live_round
    global thread
    print("START")
    is_live_round = True
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(count_minute_background)


def count_minute_background():
    """Example of how to send server generated events to clients."""
    global is_live_round
    count = 60
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
                'current_round': current_round,
                'current_word': current_word,
                'clue_giver': clue_giver,
            },
            namespace='',
        )
    print("round is NOT live")
    is_live_round = False


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
