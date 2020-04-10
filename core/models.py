import re
import random
import time
from django.contrib.auth.models import User
from django.db import models
from django.db.models import (
    Model,
    TextField,
    CharField,
    DateTimeField,
    ForeignKey,
    CASCADE,
    Q,
)
# from django.contrib.postgres.fields import ArrayField
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.validators import MinValueValidator
from . import utils

# choice structure: [(actual, human readable),...]
TEAM_CHOICES = [("red", "red"), ("blue", "blue")]
RED_TEAM, BLUE_TEAM = TEAM_CHOICES
RED_TEAM_NAME, BLUE_TEAM_NAME = RED_TEAM[1], BLUE_TEAM[1]
TEAM_NAMES = [RED_TEAM_NAME, BLUE_TEAM_NAME]
ROUND_CHOICES = [(1, "round one"), (2, "round two"), (3, "round three"), (4, "postgame")]


class Game(Model):
    created_timestamp = DateTimeField('created_timestamp',
                                      auto_now_add=True,
                                      editable=False,
                                      db_index=True)
    room = CharField('room', max_length=500, unique=True, db_index=True)

    # Populated with time.time()
    turn_start_timeint = models.IntegerField(blank=True, null=True)
    current_round = models.IntegerField(default=ROUND_CHOICES[0][0], choices=ROUND_CHOICES)

    # Setable attributes:
    turn_length = models.IntegerField(default=30, validators=[MinValueValidator(0)])
    max_word_length = models.IntegerField(default=100, validators=[MinValueValidator(0)])

    is_live_turn = models.BooleanField(default=False)
    # If we finish the round with time left, keep track
    remaining_seconds = models.IntegerField(default=0, validators=[MinValueValidator(0)])

    red_giver = ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=CASCADE,
        related_name='red_giver',
    )
    blue_giver = ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=CASCADE,
        related_name='blue_giver',
    )

    current_guessing_team = CharField(max_length=50, null=True, blank=True, choices=TEAM_CHOICES)

    current_word = ForeignKey("Word", null=True, blank=True, on_delete=CASCADE)

    def clue_giver(self):
        return self.red_giver if self.current_guessing_team == RED_TEAM_NAME else self.blue_giver

    def red_points(self):
        return len(Point.objects.filter(player__game__id=self.id, player__team='red'))

    def blue_points(self):
        return len(Point.objects.filter(player__game__id=self.id, player__team='blue'))

    def _clue_giver_idx(self):
        if self.current_guessing_team == RED_TEAM_NAME:
            try:
                giver_idx = self.red_team().index(self.red_giver)
            except ValueError:
                giver_idx = -1
        else:
            try:
                giver_idx = self.blue_team().index(self.blue_giver)
            except ValueError:
                giver_idx = -1
        return giver_idx

    # Aux helper methods:
    def _guessed_words_query(self):
        return Point.objects.filter(
            Q(player__game__id=self.id) & Q(round_scored=self.current_round))

    def guessed_words(self):
        points = self._guessed_words_query()
        return [p.word for p in points]

    def all_words(self):
        words = Word.objects.filter(Q(player__game__id=self.id))
        return words
        # return [w.text for w in words]

    def remaining_words(self):
        # points = self._guessed_words_query()
        guessed_words = self.guessed_words()
        guessed_ids = [w.id for w in guessed_words]
        wq = Word.objects.filter(Q(player__game__id=self.id))
        words = wq.exclude(id__in=guessed_ids)
        return words
        # return [w.text for w in words]

    def num_words_remaining(self):
        return len(self.remaining_words())

    def red_team(self):
        return [
            p.user for p in Player.objects.filter(game=self, team=RED_TEAM_NAME).order_by(
                "joined_timestamp")
        ]

    def blue_team(self):
        return [
            p.user for p in Player.objects.filter(game=self, team=BLUE_TEAM_NAME).order_by(
                "joined_timestamp")
        ]

    # #### Game logic methods ####
    def is_round_done(self):
        return self.num_words_remaining() == 0

    def _pick_word(self):
        return random.choice(self.remaining_words())

    def next_word(self):
        self.current_word = self._pick_word()
        self.save(update_fields=['current_word'])
        return self.current_word

    def start_turn(self):
        if not self.current_guessing_team:
            self.current_guessing_team = random.choice(TEAM_NAMES)
            self.save(update_fields=['current_guessing_team'])
        self.pass_clue_giver()
        self.is_live_turn = True
        self.current_word = self._pick_word()
        self.turn_start_timeint = time.time()
        self.save(update_fields=['is_live_turn', 'current_word', 'turn_start_timeint'])

    def end_turn(self):
        self.is_live_turn = False
        self.switch_guess_team()
        self.current_word = None
        self.remaining_seconds = 0
        self.save(update_fields=['is_live_turn', 'current_word', 'remaining_seconds'])

    def end_round(self, remaining_seconds):
        print("end round", self.current_round)
        self.is_live_turn = False
        self.current_round += 1
        self.remaining_seconds = remaining_seconds
        self.save(update_fields=['is_live_turn', 'current_round', 'remaining_seconds'])

    def switch_guess_team(self):
        self.current_guessing_team = RED_TEAM_NAME if self.current_guessing_team == BLUE_TEAM_NAME\
            else BLUE_TEAM_NAME
        self.save(update_fields=['current_guessing_team'])

    def pass_clue_giver(self):
        idx = self._clue_giver_idx()
        if self.current_guessing_team == RED_TEAM_NAME:
            users = self.red_team()
            self.red_giver = users[(idx + 1) % len(users)]
        else:
            users = self.blue_team()
            self.blue_giver = users[(idx + 1) % len(users)]
        self.save(update_fields=['red_giver', 'blue_giver'])

    alphaonly_pattern = re.compile(r'[\W_]+', re.UNICODE)

    def check_guess(self, guesser_user, guess_text):
        # remove all except alphas/numbers
        guess = self.alphaonly_pattern.sub('', guess_text.lower())
        truth = self.alphaonly_pattern.sub('', self.current_word.text.lower())
        print("GUESED (filtered):", guess, truth)
        if guess != truth:
            return False
        # Now go through logic to score, and move to next word
        print("RIGHT")
        msg = "Yes! Point for Team {}!!".format(self.current_guessing_team)
        success = utils.notify_ws_game_update(self.room, msg, None)
        word = Word.objects.get(id=self.current_word.id)
        player = Player.objects.get(game=self, user=guesser_user)
        new_point = Point(player=player, round_scored=self.current_round, word=word)
        new_point.save()  # Updates for guessed_words too

        remaining_words = self.remaining_words()
        print("all, guessed, remaining")
        print(self.all_words(), self.guessed_words(), remaining_words)
        if remaining_words:
            self.next_word()
        else:
            print("ENDING ROUND")
            # self.end_round()  # SHould happen in event loop
        return True

    class Meta:
        app_label = 'core'
        verbose_name = 'game'
        verbose_name_plural = 'games'
        ordering = ('-created_timestamp', )

    def __str__(self):
        return "Game in {}".format(self.room)


class Player(Model):
    """A user in one game becomes a player"""
    game = ForeignKey(Game, on_delete=CASCADE, db_index=True)
    user = ForeignKey(User, on_delete=CASCADE, db_index=True)
    team = CharField(max_length=500, choices=TEAM_CHOICES, null=True, blank=True, db_index=True)
    joined_timestamp = DateTimeField('joined_timestamp',
                                     auto_now_add=True,
                                     editable=False,
                                     db_index=True)

    def __str__(self):
        return "Player {}: {} in {}, team {}".format(self.id, self.user, self.game.room, self.team)


class Word(Model):
    """Word submitted by a player (who is tied to one game)"""
    player = ForeignKey(Player, on_delete=CASCADE, db_index=True)
    text = CharField(max_length=500)

    class Meta:
        unique_together = ('player', 'text')

    def __repr__(self):
        return "Word {}: {}: {}".format(self.id, self.player, self.text)

    def __str__(self):
        return self.text


class Point(Model):
    """A score form correct guess by a User in a game"""
    player = ForeignKey(Player, on_delete=CASCADE, db_index=True)
    word = ForeignKey(Word, on_delete=CASCADE)
    round_scored = models.IntegerField(default=ROUND_CHOICES[0][0], choices=ROUND_CHOICES)


class Message(Model):
    """
    This class represents a chat message. It has a owner (user), timestamp and
    the message body.

    """
    user = ForeignKey(User,
                      on_delete=CASCADE,
                      verbose_name='user',
                      related_name='from_user',
                      db_index=True)
    room = CharField('room', max_length=500)
    timestamp = DateTimeField('timestamp', auto_now_add=True, editable=False, db_index=True)
    body = TextField('body')

    def __str__(self):
        return str(self.id)

    def characters(self):
        return len(self.body)

    def notify_ws_clients(self):
        """
        Inform client there is a new message.
        """
        event = {'type': 'receive_group_message', 'message_id': '{}'.format(self.id)}

        channel_layer = get_channel_layer()
        # print("in models.MessageModel.notify_ws_clients:")
        # print("user.id {}".format(self.user.id))
        room_group_name = "room_group_{}".format(self.room)
        # print("group_send to : ", room_group_name)

        # async_to_sync(channel_layer.group_send)("{}".format(self.user.id), event)
        async_to_sync(channel_layer.group_send)(room_group_name, event)

    def save(self, *args, **kwargs):
        """
        Trims white spaces, saves the message and notifies the recipient via WS
        if the message is new.
        """
        new = self.id
        self.body = self.body.strip()  # Trimming whitespaces from the body
        super(Message, self).save(*args, **kwargs)
        if new is not None:
            return
        # First post the chat
        self.notify_ws_clients()
        # then check if we have a live turn going to check guess
        game, created = Game.objects.get_or_create(room=self.room)
        if game.is_live_turn:
            game.check_guess(self.user, self.body)

    # Meta
    class Meta:
        app_label = 'core'
        verbose_name = 'message'
        verbose_name_plural = 'messages'
        ordering = ('-timestamp', )
