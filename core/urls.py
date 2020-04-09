from django.urls import path, include
from django.views.generic import RedirectView
from django.contrib.auth.decorators import login_required
from rest_framework.routers import DefaultRouter
from core.api import MessageViewSet, UserModelViewSet, GameViewSet
from .views import ChatView, command, game_users

router = DefaultRouter()
router.register(r'message', MessageViewSet, basename='message-api')
router.register(r'user', UserModelViewSet, basename='user-api')
router.register(r'game', GameViewSet, basename='game-api')

urlpatterns = [
    path('api/v1/', include(router.urls)),
    path('command/', command),
    path('game_users/<str:room>', game_users),
    # path('game_state/<str:room>', game_state),
    # Redirect root to /chat/
    path('', RedirectView.as_view(url='room/general')),
    path(
        'room/<str:room>',
        login_required(ChatView.as_view()),
        name='home',
    ),
]
