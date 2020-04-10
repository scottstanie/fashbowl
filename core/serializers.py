from django.contrib.auth.models import User
# from django.shortcuts import get_object_or_404
from core.models import Message, Game, Word
from rest_framework.serializers import ModelSerializer, CharField, IntegerField


class MessageSerializer(ModelSerializer):
    user = CharField(source='user.username', read_only=True)

    def create(self, validated_data):
        # print('serial, create:')
        user = self.context['request'].user
        # print('self.context', self.context)
        # validated data {'room': 'general', 'body': 'ok'}
        room = validated_data['room']
        msg_body = validated_data['body']
        msg = Message(room=room, body=msg_body, user=user)
        msg.save()
        return msg

    class Meta:
        model = Message
        fields = ('id', 'user', 'room', 'timestamp', 'body')


class UserSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ('username', )


class GameSerializer(ModelSerializer):
    # red_giver = CharField(source='red_giver.username', read_only=True)
    # blue_giver = CharField(source='blue_giver.username', read_only=True)
    clue_giver = CharField(read_only=True)
    current_word = CharField(source='current_word.text', read_only=True)
    red_points = IntegerField(read_only=True)
    blue_points = IntegerField(read_only=True)
    num_words_remaining = IntegerField(read_only=True)

    class Meta:
        model = Game
        depth = 0

        fields = (
            'id',
            'room',
            'created_timestamp',
            'red_points',
            'blue_points',
            'current_round',
            'turn_start_timeint',
            'turn_length',
            'remaining_seconds',
            'is_live_turn',
            'red_giver',
            'blue_giver',
            'clue_giver',
            'current_guessing_team',
            'current_word',
            'num_words_remaining',
        )


class WordSerializer(ModelSerializer):
    class Meta:
        model = Word
        fields = ('text', )
