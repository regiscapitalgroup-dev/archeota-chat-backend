from rest_framework import generics, permissions, status, viewsets, filters
from rest_framework.response import Response
from django.urls import reverse
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
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
    RoleSerializer,
    ClassificationSerializer,
    CountrySerializer,
    UserListSerializer,
    UserManagementDetailSerializer,
    UserManagementUpdateSerializer,
    UserProfilePictureSerializer,
    UserActivationSerializer,
    ManagerSelectSerializer,
    ClientAssignmentListSerializer,
    AssignmentActionSerializer,
    ExternalRegisterSerializer
)
from .models import GoogleProfile, Company, Role, Profile, Classification, Country
from rest_framework.authtoken.models import Token
from google.oauth2 import id_token
from rest_framework.views import APIView
from django.conf import settings
from google.auth.transport import requests
import requests as rq
from django.db.models import Q, Count
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.sites.shortcuts import get_current_site
from .permissions import (
    CanManageUserObject,
    IsCompanyAdministrator,
    IsCompanyManager,
    IsSuperAdmin,
    IsAdminOrCompanyAdmin,
    IsCatalogManager
)
from django.db.models import Prefetch


CustomUser = get_user_model()


class AssignmentViewSet(viewsets.GenericViewSet):
    """
    Módulo de reasignación de cartera.
    Permite a Admins mover clientes entre managers de la misma empresa.
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminOrCompanyAdmin]

    filter_backends = [filters.SearchFilter]
    search_fields = [
        'first_name',
        'last_name',
        'email',
        'profile__national_id',
        'profile__phone_number'
    ]

    # 1. Listar Managers Disponibles
    @action(detail=False, methods=['GET'])
    def managers(self, request):
        """
        GET /api/v1/auth/assignment/managers/?company_id=X
        Lista los managers disponibles para asignar.
        """
        company_id = request.query_params.get('company_id')
        user = request.user

        if user.role == CustomUser.Role.SUPER_ADMINISTRATOR:
            # Base: Todos los managers activos
            queryset = CustomUser.objects.filter(
                role=CustomUser.Role.COMPANY_MANAGER,
                is_active=True
            ).select_related('profile', 'profile__company')  # Optimización DB

            # Filtro Opcional
            if company_id:
                queryset = queryset.filter(profile__company_id=company_id)

        elif user.role == CustomUser.Role.COMPANY_ADMINISTRATOR:
            # Restricción Fuerte: Solo su empresa
            queryset = CustomUser.objects.filter(
                role=CustomUser.Role.COMPANY_MANAGER,
                profile__company=user.profile.company,
                is_active=True
            ).select_related('profile', 'profile__company')

        else:
            # Capa de seguridad extra (aunque IsAdminOrCompanyAdmin ya protege)
            return Response({"error": "No autorizado"}, status=status.HTTP_403_FORBIDDEN)

        serializer = ManagerSelectSerializer(queryset, many=True)
        return Response(serializer.data)

    # 2. Listar Clientes YA asignados a un Manager
    @action(detail=True, methods=['GET'], url_path='assigned-clients')
    def assigned_clients(self, request, pk=None):
        """
        Lista clientes asignados al manager.
        Soporta búsqueda: ?search=termino
        """
        try:
            manager = CustomUser.objects.get(pk=pk, role=CustomUser.Role.COMPANY_MANAGER)

            if request.user.role == CustomUser.Role.COMPANY_ADMINISTRATOR:
                if manager.profile.company != request.user.profile.company:
                    return Response({"error": "No autorizado"}, status=status.HTTP_403_FORBIDDEN)

            # Queryset base
            clients_qs = CustomUser.objects.filter(
                role=CustomUser.Role.CLIENT,
                managed_by=manager,
                is_active=True
            ).select_related('profile', 'profile__company', 'profile__classification')

            # --- APLICAR FILTROS DE BÚSQUEDA AQUÍ ---
            clients_qs = self.filter_queryset(clients_qs)
            # ----------------------------------------

            serializer = ClientAssignmentListSerializer(clients_qs, many=True)
            return Response(serializer.data)

        except CustomUser.DoesNotExist:
            return Response({"error": "Manager no encontrado"}, status=status.HTTP_404_NOT_FOUND)

    # 3. Listar Clientes DISPONIBLES (De la misma empresa, pero NO de este manager)
    @action(detail=True, methods=['GET'], url_path='available-clients')
    def available_clients(self, request, pk=None):
        """
        Lista clientes disponibles (no asignados a este manager).
        Soporta búsqueda: ?search=termino
        """
        try:
            manager = CustomUser.objects.get(pk=pk, role=CustomUser.Role.COMPANY_MANAGER)
            company = manager.profile.company

            if request.user.role == CustomUser.Role.COMPANY_ADMINISTRATOR:
                if company != request.user.profile.company:
                    return Response({"error": "No autorizado"}, status=status.HTTP_403_FORBIDDEN)

            # Queryset base
            clients_qs = CustomUser.objects.filter(
                role=CustomUser.Role.CLIENT,
                profile__company=company,
                is_active=True
            ).exclude(
                managed_by=manager
            ).select_related('profile', 'profile__company', 'profile__classification')

            # --- APLICAR FILTROS DE BÚSQUEDA AQUÍ ---
            clients_qs = self.filter_queryset(clients_qs)
            # ----------------------------------------

            serializer = ClientAssignmentListSerializer(clients_qs, many=True)
            return Response(serializer.data)

        except CustomUser.DoesNotExist:
            return Response({"error": "Manager no encontrado"}, status=status.HTTP_404_NOT_FOUND)

    # 4. Acción: Asignar Cliente
    @action(detail=False, methods=['POST'], url_path='assign')
    def assign_client(self, request):
        """
        POST /api/v1/auth/assignment/assign/
        Body: { "client_id": 10, "manager_id": 5 }
        Mueve el cliente al manager especificado.
        """
        serializer = AssignmentActionSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            client = serializer.validated_data['client_obj']
            manager = serializer.validated_data['manager_obj']

            # Ejecutar cambio
            client.managed_by = manager
            client.save(update_fields=['managed_by'])

            return Response(
                {"status": "success", "message": f"Client {client.first_name} assigned to {manager.first_name}"})

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # 5. Acción: Desasignar Cliente
    @action(detail=False, methods=['POST'], url_path='unassign')
    def unassign_client(self, request):
        """
        POST /api/v1/auth/assignment/unassign/
        Body: { "client_id": 10 }
        Deja al cliente sin manager (managed_by = None).
        """
        # Usamos el mismo serializer, manager_id no es requerido
        serializer = AssignmentActionSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            client = serializer.validated_data['client_obj']

            # Ejecutar desasignación
            client.managed_by = None
            client.save(update_fields=['managed_by'])

            return Response({"status": "success", "message": f"Cliente {client.first_name} desasignado."})

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserViewSet(viewsets.ModelViewSet):
    # serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated, CanManageUserObject]

    def get_queryset(self):
            user = self.request.user

            dependents_prefetch = Prefetch(
                'managed_users',
                queryset=CustomUser.objects.select_related('profile', 'profile__classification')
            )

            # 1. El SUPER_ADMIN puede ver a todos los usuarios
            if user.role == CustomUser.Role.SUPER_ADMINISTRATOR:
                return CustomUser.objects.all().select_related(
                    'profile', 'profile__classification'
                ).annotate(
                    dependents_count=Count('managed_users')
                )

            # 2. El COMPANY_ADMIN ve a los managers y usuarios finales de su propia compañía
            if user.role == CustomUser.Role.COMPANY_ADMINISTRATOR:
                try:
                    admin_company = user.profile.company
                except CustomUser.profile.RelatedObjectDoesNotExist:
                    return CustomUser.objects.none()

                if not admin_company:
                    return CustomUser.objects.none()

                return CustomUser.objects.filter(
                    Q(profile__company=admin_company),
                    Q(managed_by=user) | Q(managed_by__managed_by=user)
                ).select_related(
                    'profile', 'profile__classification'
                ).annotate(
                    dependents_count=Count('managed_users')  # <-- AÑADIR ANNOTATE
                )

            # 3. El COMPANY_MANAGER ve solo a los usuarios finales que él gestiona
            if user.role == CustomUser.Role.COMPANY_MANAGER:
                try:
                    manager_company = user.profile.company
                except CustomUser.profile.RelatedObjectDoesNotExist:
                    return CustomUser.objects.none()

                if not manager_company:
                    return CustomUser.objects.none()

                # Nota: Los FINAL_USER siempre tendrán 0 dependientes,
                # pero agregamos el annotate para consistencia.
                return CustomUser.objects.filter(
                    profile__company=manager_company,
                    managed_by=user,
                    role=CustomUser.Role.CLIENT
                ).select_related(
                    'profile', 'profile__classification', 'managed_by'
                ).prefetch_related( # <-- AÑADIR ESTO PARA OPTIMIZAR DETALLE
                    dependents_prefetch
                ).annotate(
                    dependents_count=Count('managed_users')  # <-- AÑADIR ANNOTATE
                )

            # Por defecto (ej. para un FINAL_USER), no se devuelve ningún usuario
            return CustomUser.objects.none()

    def get_serializer_class(self):
        """
        Usa UserListSerializer para listados y UserSerializer
        """
        if self.action == 'list':
            return UserListSerializer

        if self.action == 'retrieve':
            return UserManagementDetailSerializer

        if self.action in ['update', 'partial_update']:
            return UserManagementUpdateSerializer

        if self.action == 'upload_picture':
            return UserProfilePictureSerializer

        return UserSerializer

    @action(detail=True, methods=['POST'], url_path='upload-picture', parser_classes=[MultiPartParser, FormParser])
    def upload_picture(self, request, pk=None):
        """
        Endpoint específico para subir la foto de perfil.
        URL: POST /api/v1/auth/users/{id}/upload-picture/
        """
        user = self.get_object()  # Obtiene el usuario por ID (valida permisos automáticamente)

        serializer = UserProfilePictureSerializer(data=request.data)

        if serializer.is_valid():
            serializer.update(user, serializer.validated_data)

            # Devolvemos la URL de la nueva foto
            return Response({
                "status": "success",
                "profile_picture_url": user.profile.get_profile_picture
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def perform_create(self, serializer):
        serializer.save()


class RoleViewset(viewsets.ModelViewSet):
    serializer_class = RoleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # 1. Base: Obtener todos los roles
        queryset = Role.objects.all()

        # 2. Regla General: Nadie puede ver/asignar el rol SUPER_ADMIN desde este endpoint
        # (Los Super Admins se crean por consola o procesos especiales)
        queryset = queryset.exclude(code=CustomUser.Role.SUPER_ADMINISTRATOR)

        # 3. Filtros por Jerarquía
        if user.role == CustomUser.Role.SUPER_ADMINISTRATOR:
            # Super Admin ve _todo (COMPANY_ADMIN, COMPANY_MANAGER, CLIENT)
            return queryset

        if user.role == CustomUser.Role.COMPANY_ADMINISTRATOR:
            # Company Admin solo puede crear Managers o Clientes
            return queryset.filter(code__in=[
                CustomUser.Role.COMPANY_MANAGER,
                CustomUser.Role.CLIENT
            ])

        if user.role == CustomUser.Role.COMPANY_MANAGER:
            # Company Manager solo puede crear Clientes
            return queryset.filter(code=CustomUser.Role.CLIENT)

        # Si es CLIENT o rol desconocido, no ve ningún rol
        return Role.objects.none()


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
    permission_classes = [permissions.AllowAny]
    serializer_class = GoogleAuthSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        id_token_str = serializer.validated_data['id_token']

        try:
            idinfo = id_token.verify_oauth2_token(
                id_token_str, requests.Request(), settings.GOOGLE_OAUTH_CLIENT_ID
            )

            userid = idinfo.get('sub')
            email = idinfo.get('email')
            if not email:
                return Response({"error": "Email not provided by Google token."}, status=status.HTTP_400_BAD_REQUEST)

            first_name = idinfo.get('given_name', '')
            last_name = idinfo.get('family_name', '')
            name = idinfo.get('name', '')
            picture_url = idinfo.get('picture', '')

            try:
                user = CustomUser.objects.get(email=email)
                created = False
            except CustomUser.DoesNotExist:
                user = CustomUser.objects.create_user(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    role=CustomUser.Role.FINAL_USER
                )
                user.set_unusable_password()
                user.save()
                created = True

            # Ensure profile exists and update missing profile picture
            profile, _ = Profile.objects.get_or_create(user=user)
            if picture_url and not profile.profile_picture_url:
                profile.profile_picture_url = picture_url
                profile.save()

            # Sync Google profile
            google_profile, _ = GoogleProfile.objects.get_or_create(user=user)
            if userid:
                google_profile.google_id = userid
            if picture_url:
                google_profile.profile_picture_url = picture_url
            google_profile.save()

            # Optionally keep DRF token creation for backward compatibility
            Token.objects.get_or_create(user=user)

            refresh_token_obj = RefreshToken.for_user(user)

            return Response({
                "message": "Login successful",
                "user_id": user.id,
                "email": user.email,
                "profile_picture_url": google_profile.profile_picture_url,
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
    permission_classes = [IsSuperAdmin]


class RegisterView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    permission_classes = [permissions.AllowAny]  # Público
    serializer_class = ExternalRegisterSerializer


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


class ClassificationViewSet(viewsets.ModelViewSet):
    """
    CRUD de Clasificaciones por Empresa.
    Solo Managers o Admins pueden acceder.
    """
    serializer_class = ClassificationSerializer

    def get_permissions(self):
        """
        Define permisos dinámicos según la acción.
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            # Solo el Super Admin puede modificar el catálogo
            permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]
        else:
            # Todos (Managers incluidos) pueden leer para asignar
            permission_classes = [permissions.IsAuthenticated, IsCatalogManager]

        return [permission() for permission in permission_classes]


    def get_queryset(self):
        user = self.request.user

        if user.role == CustomUser.Role.SUPER_ADMINISTRATOR:
            company_id = self.request.query_params.get('company_id')
            if company_id:
                return Classification.objects.filter(company_id=company_id).order_by('name')
            return Classification.objects.all().order_by('company__name', 'name')

            # 2. OTROS ROLES: Solo ven lo de su empresa
        if not hasattr(user, 'profile') or not user.profile.company:
            return Classification.objects.none()

        # Filtro: Solo devolvemos las clasificaciones de SU empresa
        return Classification.objects.filter(company=user.profile.company).order_by('name')


class CountriesListView(generics.ListAPIView):
    queryset = Country.objects.all().order_by('name')
    serializer_class = CountrySerializer
    permission_classes = [permissions.IsAuthenticated]


class UserActivationView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        # --- DEBUGGING PRINTS (Borrar después de arreglar) ---
        print("--- DEBUG ACTIVACIÓN ---")
        print(f"Content-Type recibido: {request.content_type}")
        print(f"Datos crudos (request.data): {request.data}")
        # -----------------------------------------------------

        serializer = UserActivationSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()
            return Response({
                "message": "Cuenta activada exitosamente. Ya puedes iniciar sesión.",
                "email": user.email
            }, status=status.HTTP_200_OK)

        # --- DEBUG ERROR ---
        print(f"Errores del serializador: {serializer.errors}")
        # -------------------
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
