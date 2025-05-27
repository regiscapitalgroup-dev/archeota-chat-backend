from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView # Vista integrada para refrescar token

from .views import (
    UserCreateView,
    LoginView,
    UserDetailView,
    LogoutView
)

urlpatterns = [
    # Autenticación y Registro
    path('register/', UserCreateView.as_view(), name='user-register'),
    path('login/', LoginView.as_view(), name='token-obtain-pair'), # login, obtiene access y refresh tokens
    path('login/refresh/', TokenRefreshView.as_view(), name='token-refresh'), # refresca el access token
    path('logout/', LogoutView.as_view(), name='user-logout'),

    # Gestión de Usuario
    path('user/', UserDetailView.as_view(), name='user-detail'), # Obtiene detalles del usuario autenticado
]