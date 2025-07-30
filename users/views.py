from rest_framework import generics, permissions, status, viewsets
from rest_framework.response import Response
from django.urls import reverse
from rest_framework_simplejwt.views import TokenObtainPairView as SimpleJWTTokenObtainPairView
from .serializers import (
    GoogleAuthSerializer, 
    UserProfileSerializer, 
    CompanySerializer,
    UserUpdateSerializer, 
    PasswordResetConfirmSerializer,
    CustomUserSerializer, 
    UserDetailSerializer,
    CustomTokenObtainPairSerializer, 
    LogoutSerializer,
    UserSerializer,
    RoleSerializer    
)
from .models import GoogleProfile, Company, Role
from rest_framework.authtoken.models import Token
from google.oauth2 import id_token
from rest_framework.views import APIView
from django.conf import settings
from google.auth.transport import requests
import requests as rq
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.sites.shortcuts import get_current_site
from .permissions import CanManageUserObject, IsCompanyAdministrator, IsCompanyManager

CustomUser = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated, CanManageUserObject]

    def get_queryset(self):
        user = self.request.user

        if user.is_superuser:
            return CustomUser.objects.exclude(id=user.id)
        
        if user.role == 'COMPANY_ADMIN':
            managers = user.managed_users.all() 
            end_users = CustomUser.objects.filter(managed_by__in=managers)
            return managers | end_users

        if user.role == 'COMPANY_MANAGER':
            return user.managed_users.all()

        return CustomUser.objects.none()

    def perform_create(self, serializer):
        serializer.save()


class RoleViewset(viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer



class ProfileDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
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
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return UserUpdateSerializer
        return UserDetailSerializer


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
                    role=CustomUser.Role.FINAL_USER
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


class CompanyViewset(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer


class RegisterView(generics.CreateAPIView):
    serializer_class = CustomUserSerializer
    permission_classes = [permissions.AllowAny]


class ForgotMyPassword(APIView):   
    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'error': 'email is required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return Response({'detail': 'If an account exists with this email, reset instructions will be sent.'}, status=status.HTTP_200_OK)
        
        token_generator = PasswordResetTokenGenerator()
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = token_generator.make_token(user)
        
        reset_link = f"https://main.d2r4dlvkgqpbf1.amplifyapp.com/reset-password/{uidb64}/{token}/"

        subject = 'Archeota: Reset your Password'
        message = (
            f"Hello {user.first_name},\n\n"
            f"Click the link below to reset your password.:\n"
            f"{reset_link}\n\n"
            f"If you did not request this, please ignore this email.\n"
            "The link will expire in 1 hour.\n\n"
            "Thank You."
        )
        try:
            send_mail(subject, message, settings.ADMIN_USER_EMAIL, [user.email])
        except Exception as e:
            print(f"Error sending email: {e}")
            return Response({'error': 'There was a problem sending the email.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({'detail': 'If an account exists with this email, reset instructions will be sent.'}, status=status.HTTP_200_OK)    
    
    
class PasswordResetConfirmView(APIView):

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            uid = force_str(urlsafe_base64_decode(serializer.validated_data['user']))
            user = CustomUser.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
            user = None

        token_generator = PasswordResetTokenGenerator()
        if user is not None and token_generator.check_token(user, serializer.validated_data['token']):
            p = serializer.validated_data['password']
            user.set_password(p)
            user.save()

            data = {"email": user, 'password': p}
            current_site = get_current_site(request).domain
            relative_link = reverse('token-obtain-pair')
            r = rq.post(f'http://{current_site}{relative_link}', data=data) 
            if r.status_code == 200:
                return Response(r.json(), status=status.HTTP_200_OK)
        else:
            return Response({'error': 'The reset link is invalid or has expired.'}, status=status.HTTP_400_BAD_REQUEST)
