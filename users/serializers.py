from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer as SimpleJWTTokenObtainPairSerializer
from .models import Profile, Company, Role, CompanyProfile
from django.contrib.auth.password_validation import validate_password


CustomUser = get_user_model()


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = '__all__'


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = '__all__'


class UserProfileSerializer(serializers.ModelSerializer):
    role_code = serializers.CharField(source='role.code', read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)

    class Meta:
        model = Profile
        fields = [
            'role_code',
            'company',
            'company_name',
            'phone_number',
            'national_id',
            'digital_signature'
            
         ]
        
    def get_role_code(self, obj):
        if obj.role and hasattr(obj.role, 'code') and obj.role.code:
            return obj.role.code.upper()
        return None


class CustomUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, min_length=8, style={'input_type': 'password'})
    first_name = serializers.CharField(required=True, max_length=150)
    last_name = serializers.CharField(required=True, max_length=150)

    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)    

    class Meta:
        model = CustomUser
        fields = ['email', 'first_name', 'last_name', 'password', 'access', 'refresh']
        extra_kwargs = {
            'email': {'required': True}
        }

    def create(self, validated_data):
        
        user = CustomUser.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name']
        )

        refresh_token_obj = RefreshToken.for_user(user)

        user.access = str(refresh_token_obj.access_token)
        user.refresh = str(refresh_token_obj)

        return user


class UserDetailSerializer(serializers.ModelSerializer): 
    profile = UserProfileSerializer(read_only=True)
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'first_name', 'last_name', 'profile'] 


class CustomTokenObtainPairSerializer(SimpleJWTTokenObtainPairSerializer): 
    def validate(self, attrs):
        data = super().validate(attrs) 

        user_serializer = UserDetailSerializer(self.user)
        data['user'] = user_serializer.data
        return data


class LogoutSerializer(serializers.Serializer): # Para Logout
    refresh = serializers.CharField()

    default_error_messages = {
        'bad_token': ('El token es inválido o ha expirado.')
    }

    def validate(self, attrs):
        self.token = attrs['refresh']
        return attrs

    def save(self, **kwargs):
        try:
            RefreshToken(self.token).blacklist()
        except Exception: 
            self.fail('bad_token')


class GoogleAuthSerializer(serializers.Serializer):
    id_token = serializers.CharField()


class CompanyProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyProfile
        fields = ['company_name', 'website', 'tax_id']
        

class CompanyRegisterSerializer(serializers.ModelSerializer):
    profile = CompanyProfileSerializer(required=True)
    password = serializers.CharField(write_only=True, required=True, min_length=8)
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)

    class Meta:
        model = CustomUser
        fields = ['email', 'password', 'profile', 'access', 'refresh']

    def create(self, validated_data):
        profile_data = validated_data.pop('profile')
        
        # 1. Crea el CustomUser
        user = CustomUser.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=profile_data['company_name'],
            last_name='(Company)',
        )

        # 2. Crea explícitamente el CompanyProfile asociado
        CompanyProfile.objects.create(user=user, **profile_data)
        
        # 3. Genera tokens
        refresh = RefreshToken.for_user(user)
        user.access = str(refresh.access_token)
        user.refresh = str(refresh)
        
        return user


class UnifiedRegisterSerializer(serializers.ModelSerializer):
    user_profile = UserProfileSerializer(required=False)
    company_profile = CompanyProfileSerializer(required=False)

    password = serializers.CharField(write_only=True, required=True, min_length=8)
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)

    class Meta:
        model = CustomUser
        fields = [
            'email', 'first_name', 'last_name', 'password', 'role',
            'user_profile', 'company_profile', 'access', 'refresh'
        ]
        # Hacemos first_name y last_name opcionales aquí, los validaremos después
        extra_kwargs = {
            'first_name': {'required': False},
            'last_name': {'required': False},
        }

    def validate(self, data):
        """
        Validación personalizada para requerir campos según el rol.
        """
        # Obtenemos el rol que la vista nos pasó en el contexto.
        role = self.context.get('role_code')

        if not role:
            raise serializers.ValidationError("El rol no fue proporcionado por la vista.")

        if role == 'final_user':
            if not data.get('user_profile'):
                raise serializers.ValidationError({"user_profile": "Este campo es requerido para usuarios."})
            if not data.get('first_name') or not data.get('last_name'):
                raise serializers.ValidationError({"detail": "first_name y last_name son requeridos para usuarios."})
            if data.get('company_profile'):
                raise serializers.ValidationError({"company_profile": "Este campo no es permitido para usuarios."})

        elif role == 'company':
            if not data.get('company_profile'):
                raise serializers.ValidationError({"company_profile": "Este campo es requerido para compañías."})
            if data.get('user_profile'):
                raise serializers.ValidationError({"user_profile": "Este campo no es permitido para compañías."})

        return data

    def create(self, validated_data):
        # Extraemos los datos de los perfiles
        user_profile_data = validated_data.pop('user_profile', None)
        company_profile_data = validated_data.pop('company_profile', None)

        # Obtenemos el rol del contexto
        role = self.context['role_code']
        
        # Para compañías, usamos el nombre de la compañía como first_name
        if role == 'company':
            validated_data['first_name'] = company_profile_data['company_name']
            validated_data['last_name'] = '(Company)'

        # Creamos el usuario con su rol
        user = CustomUser.objects.create_user(role=role, **validated_data)
        
        # Creamos el perfil correspondiente basado en el rol
        if role == 'final_user':
            Profile.objects.filter(user=user).update(**user_profile_data)
        elif role == 'company':
            CompanyProfile.objects.filter(user=user).update(**company_profile_data)

        # Generamos los tokens
        refresh = RefreshToken.for_user(user)
        user.access = str(refresh.access_token)
        user.refresh = str(refresh)
        
        user.refresh_from_db() # Recargamos para que la respuesta incluya los perfiles
        return user

class SimplifiedRegisterSerializer(serializers.ModelSerializer):
    """
    Serializer para un registro simple. Solo requiere email y password.
    Acepta un 'role_name' opcional. Por defecto es 'USER'.
    """
    # Campo opcional, solo para escritura, no se mostrará en la respuesta.
    role_name = serializers.CharField(write_only=True, required=False)
    
    password = serializers.CharField(write_only=True, required=True, min_length=8)
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)

    class Meta:
        model = CustomUser
        # Solo los campos esenciales. 'role' se manejará internamente.
        fields = ['email', 'password', 'first_name', 'last_name', 'role_name', 'access', 'refresh']

    def validate_role_name(self, value):
        """
        Valida que el rol proporcionado exista en la base de datos.
        """
        if not Role.objects.filter(code=value).exists():
            raise serializers.ValidationError(f"El rol '{value}' no es válido.")
        return value

    def create(self, validated_data):
        # Usa el rol proporcionado o establece 'USER' como default.
        role_name = validated_data.pop('role_code', 'final_user')
        
        # Obtenemos la instancia del Rol.
        try:
            role_instance = Role.objects.get(code=role_name)
        except Role.DoesNotExist:
            # Esta validación es una segunda capa de seguridad.
            raise serializers.ValidationError("Rol no encontrado.")

        # Creamos el usuario, asignando la instancia del rol.
        # La señal se encargará del perfil automáticamente.
        user = CustomUser.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            role=role_instance
        )

        # Generamos los tokens
        refresh = RefreshToken.for_user(user)
        user.access = str(refresh.access_token)
        user.refresh = str(refresh)

        return user

class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'role']


class PasswordResetConfirmSerializer(serializers.Serializer):
    user = serializers.CharField(write_only=True, required=True)
    token = serializers.CharField(write_only=True, required=True)
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password], 
        style={'input_type': 'password'}
    )

    def validate(self, attrs):
        return attrs
