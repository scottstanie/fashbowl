from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.authentication import SessionAuthentication

from fashbowl import settings
from core.serializers import MessageSerializer, UserSerializer, GameSerializer
from core.models import Message, Game


class CsrfExemptSessionAuthentication(SessionAuthentication):
    """
    SessionAuthentication scheme used by DRF. DRF's SessionAuthentication uses
    Django's session framework for authentication which requires CSRF to be
    checked. In this case we are going to disable CSRF tokens for the API.
    """
    def enforce_csrf(self, request):
        return


class MessagePagination(PageNumberPagination):
    """
    Limit message prefetch to one page.
    """
    page_size = settings.MESSAGES_TO_LOAD


class MessageViewSet(ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    allowed_methods = ('GET', 'POST', 'HEAD', 'OPTIONS')
    authentication_classes = (CsrfExemptSessionAuthentication, )
    pagination_class = MessagePagination

    def list(self, request, *args, **kwargs):
        print('api list:')
        # print(' request, ', dir(request))
        # print(' request.query_params, ', request.query_params)
        # print('args kwargs', args, kwargs)
        room = request.query_params['room']
        self.queryset = self.queryset.filter(Q(room=room))
        return super(MessageViewSet, self).list(request, *args, **kwargs)

    # TODO: unclear if i still need to override without the extra logic
    def retrieve(self, request, *args, **kwargs):
        # room = request.query_params['room']
        msg = get_object_or_404(
            self.queryset.filter(
                # Q(recipient=request.user) | Q(user=request.user), Q(pk=kwargs['pk'])))
                # or url room?
                # Q(room=request.room),
                Q(pk=kwargs['pk'])))
        serializer = self.get_serializer(msg)
        return Response(serializer.data)


class UserModelViewSet(ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    allowed_methods = ('GET', 'HEAD', 'OPTIONS')
    pagination_class = None  # Get all user

    def list(self, request, *args, **kwargs):
        print("LIST: room =", request.query_params)
        room = request.query_params.get('room')
        if room:
            self.queryset = self.queryset.filter(Q(room=room))
        # # Get all users except yourself (me: why??)
        # self.queryset = self.queryset.exclude(id=request.user.id)
        return super(UserModelViewSet, self).list(request, *args, **kwargs)


class GameViewSet(ModelViewSet):
    queryset = Game.objects.all()
    serializer_class = GameSerializer
    allowed_methods = ('GET', 'POST', 'HEAD', 'OPTIONS')
    authentication_classes = (CsrfExemptSessionAuthentication, )

    def list(self, request, *args, **kwargs):
        print("LIST: room =", request.query_params)
        room = request.query_params.get('room')
        if room:
            self.queryset = self.queryset.filter(Q(room=room))
        # # Get all users except yourself (me: why??)
        # self.queryset = self.queryset.exclude(id=request.user.id)
        return super(GameViewSet, self).list(request, *args, **kwargs)