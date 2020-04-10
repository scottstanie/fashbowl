from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from .views import SignUpView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    path('signup/', SignUpView.as_view(), name='signup'),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
