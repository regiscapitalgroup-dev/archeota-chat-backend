from rest_framework import generics, permissions, status, viewsets
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView as SimpleJWTTokenObtainPairView
from .serializers import GoogleAuthSerializer, UserProfileSerializer, RoleSerializer, CompanySerializer
from .models import GoogleProfile, Role, Company
from rest_framework.authtoken.models import Token
from google.oauth2 import id_token
from rest_framework.views import APIView
from django.conf import settings
from google.auth.transport import requests
from rest_framework_simplejwt.tokens import RefreshToken

from django.contrib.auth import get_user_model

from .serializers import (
    CustomUserSerializer, 
    UserDetailSerializer,
    CustomTokenObtainPairSerializer, 
    LogoutSerializer
)

CustomUser = get_user_model()

class UserCreateView(generics.CreateAPIView): 
    serializer_class = CustomUserSerializer
    permission_classes = [permissions.AllowAny] 


class ProfileDetailView(generics.RetrieveUpdateAPIView):
    """
    Vista para ver y actualizar el perfil del usuario autenticado.
    """
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        # Devuelve el perfil del usuario que hace la petición
        return self.request.user.profile

    def perform_update(self, serializer):
        serializer.save(user=self.request.user)


class LoginView(SimpleJWTTokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class UserDetailView(generics.RetrieveAPIView): 
    queryset = CustomUser.objects.all() 
    serializer_class = UserDetailSerializer
    permission_classes = [permissions.IsAuthenticated] 

    def get_object(self):
        return self.request.user


class LogoutView(generics.GenericAPIView): 
    serializer_class = LogoutSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save() 
        return Response({"detail": "Successful logout."}, status=status.HTTP_200_OK)
    

class GoogleLoginView(APIView):
    serializer_class = GoogleAuthSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        id_token_str = serializer.validated_data['id_token']

        try:
            idinfo = id_token.verify_oauth2_token(
                id_token_str, requests.Request(), settings.GOOGLE_OAUTH_CLIENT_ID
            )

            userid = idinfo['sub']
            email = idinfo['email']
            first_name = idinfo.get('given_name', '')
            last_name = idinfo.get('family_name', '')
            name = idinfo.get('name', '') 

            try:
                user = CustomUser.objects.get(email=email)
            except CustomUser.DoesNotExist:
                user = CustomUser.objects.create_user(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                )
                user.set_unusable_password()
                user.save()

            google_profile, created = GoogleProfile.objects.get_or_create(user=user)
            google_profile.google_id = userid
            google_profile.save()

            token, created = Token.objects.get_or_create(user=user)
            
            refresh_token_obj = RefreshToken.for_user(user)

            return Response({
                "message": "Login successful",
                "user_id": user.id,
                "email": user.email,
                "access": str(refresh_token_obj.access_token),
                "refresh": str(refresh_token_obj), 

            }, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response({"error": f"Invalid Google ID Token: {e}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": f"An unexpected error occurred: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RoleViewset(viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer


class CompanyViewset(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
