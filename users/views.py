from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView as SimpleJWTTokenObtainPairView
# TokenRefreshView se usará directamente en urls.py

from django.contrib.auth import get_user_model

from .serializers import (
    CustomUserSerializer, # Para registro
    UserDetailSerializer,
    CustomTokenObtainPairSerializer, # Para login personalizado
    LogoutSerializer
)

CustomUser = get_user_model()

class UserCreateView(generics.CreateAPIView): # Para Registro
    """
    Vista para crear nuevos usuarios. Devuelve datos del usuario y tokens.
    """
    serializer_class = CustomUserSerializer
    permission_classes = [permissions.AllowAny] # Cualquiera puede registrarse


class LoginView(SimpleJWTTokenObtainPairView): # Para Login
    """
    Vista para el login de usuarios. Utiliza el serializer personalizado
    para devolver tokens y datos del usuario.
    """
    serializer_class = CustomTokenObtainPairSerializer


class UserDetailView(generics.RetrieveAPIView): # Para Detalles del Usuario
    """
    Vista para obtener los detalles del usuario autenticado.
    """
    queryset = CustomUser.objects.all() # Necesario para RetrieveAPIView
    serializer_class = UserDetailSerializer
    permission_classes = [permissions.IsAuthenticated] # Solo usuarios autenticados

    def get_object(self):
        # Devuelve el usuario actualmente autenticado
        return self.request.user


class LogoutView(generics.GenericAPIView): # Para Logout
    """
    Vista para el logout de usuarios. Añade el refresh token a la blacklist.
    """
    serializer_class = LogoutSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save() # Llama al método save del LogoutSerializer para invalidar el token
        return Response({"detail": "Logout exitoso."}, status=status.HTTP_200_OK)