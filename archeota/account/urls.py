from django.urls import path, include
from account.views import UserRegistrationView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,  # Para obtener el par de tokens (login)
    TokenRefreshView,     # Para refrescar el token de acceso
    TokenBlacklistView,   # Para invalidar (blacklist) un refresh token (logout)
)

urlpatterns = [
    path('register/', UserRegistrationView.as_view(), name='user-register'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    # Refresh: Envía refresh token, recibe nuevo access token
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # Logout: Envía refresh token para añadirlo a la lista negra
    path('api/token/blacklist/', TokenBlacklistView.as_view(), name='token_blacklist'),
]
