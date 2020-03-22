import os

from flask import Flask, render_template, request, jsonify, g
from flask_socketio import SocketIO, emit, join_room, leave_room
# import json
import sqlite3
from collections import defaultdict

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
socketio = SocketIO(app)

# Channel Data Global Variables
channel_list = {"general": []}
present_channel = {"initial": "general"}
# submitted_words[channel][user]:
submitted_words = defaultdict(lambda: defaultdict(str))
# TODO: team name instead of red/blue
team_points = defaultdict(int)
team_points["red"] = 0
team_points["blue"] = 0
# team_points = {"red": 0, "blue": 0}

DATABASE = 'database.db'


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
        return render_template("index.html", channel_list=channel_list)

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
    channel = message_data["current_channel"]
    channel_message_count = len(channel_list[channel])
    del message_data["current_channel"]
    channel_list[channel].append(message_data)
    message_data["deleted_message"] = False
    if (channel_message_count >= 100):
        del channel_list[channel][0]
        message_data["deleted_message"] = True
    emit("recieve message", message_data, broadcast=True, room=channel)


@socketio.on("send word")
def send_word(message_data):
    print(message_data)
    channel = message_data["current_channel"]
    user = message_data["user"]

    # TODO: check here for bad word

    if submitted_words[channel][user]:
        print("already submitted, changing")
    submitted_words[channel][user] = message_data["submitted_word"]
    # emit("recieve word", message_data, broadcast=True, room=channel)
    print("submitted words:")
    print(submitted_words)


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
