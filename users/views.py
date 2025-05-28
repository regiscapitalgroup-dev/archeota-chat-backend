from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView as SimpleJWTTokenObtainPairView
from .serializers import GoogleAuthSerializer
from .models import GoogleProfile
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate, login
from google.oauth2 import id_token
from rest_framework.views import APIView
from django.conf import settings
from google.auth.transport import requests
from rest_framework_simplejwt.tokens import RefreshToken

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
    

class GoogleLoginView(APIView):
    """
    Handles Google ID Token verification and user authentication.
    """
    serializer_class = GoogleAuthSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        id_token_str = serializer.validated_data['id_token']

        try:
            # Specify the CLIENT_ID of the app that accesses the backend:
            # (THIS IS CRUCIAL) - Make sure this matches your FE's client ID.
            idinfo = id_token.verify_oauth2_token(
                id_token_str, requests.Request(), settings.GOOGLE_OAUTH_CLIENT_ID
            )

            # Or, if you need to verify against a list of client IDs:
            # idinfo = id_token.verify_oauth2_token(id_token_str, requests.Request())
            # if idinfo['aud'] not in [CLIENT_ID_1, CLIENT_ID_2, CLIENT_ID_3]:
            #     raise ValueError('Could not verify audience.')

            # ID token is valid. Get the user's Google ID and profile information.
            userid = idinfo['sub']
            email = idinfo['email']
            first_name = idinfo.get('given_name', '')
            last_name = idinfo.get('family_name', '')
            name = idinfo.get('name', '') # Full name

            # Find or create the user
            try:
                user = CustomUser.objects.get(email=email)
            except CustomUser.DoesNotExist:
                # Create a new user if not found
                user = CustomUser.objects.create_user(
                    email=email,
                    # username=email, # Or generate a unique username
                    first_name=first_name,
                    last_name=last_name,
                    # password=User.objects.make_random_password() # Consider setting an unusable password
                )
                user.set_unusable_password() # Mark password as unusable for social logins
                user.save()

            # Optional: Link Google ID to user profile
            # from .models import GoogleProfile
            google_profile, created = GoogleProfile.objects.get_or_create(user=user)
            google_profile.google_id = userid
            google_profile.save()

            # Log the user in (optional, if you're using DRF's Token Authentication
            # and not Django sessions)
            # This part is more for session-based authentication or if you need to trigger signals.
            # If using TokenAuthentication or JWT, you'll generate a token.
            # login(request, user)

            # Generate or retrieve authentication token for DRF
            token, created = Token.objects.get_or_create(user=user)
            
            refresh_token_obj = RefreshToken.for_user(user)

            return Response({
                "message": "Login successful",
                "user_id": user.id,
                "email": user.email,
                #"token": token.key, # Return the token to the frontend
                "access": str(refresh_token_obj.access_token),
                "refresh": str(refresh_token_obj), 

            }, status=status.HTTP_200_OK)

        except ValueError as e:
            # Invalid token
            return Response({"error": f"Invalid Google ID Token: {e}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": f"An unexpected error occurred: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
