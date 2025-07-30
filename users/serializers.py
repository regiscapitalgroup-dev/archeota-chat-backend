from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer as SimpleJWTTokenObtainPairSerializer
from .models import Profile, Company, CompanyProfile, Role
from django.contrib.auth.password_validation import validate_password
from django.utils.crypto import get_random_string
from django.core.mail import send_mail
from django.conf import settings


CustomUser = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    role = serializers.ChoiceField(choices=CustomUser.Role.choices, required=True)
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)  

    class Meta:
        model = CustomUser
        fields = ('id', 'email', 'first_name', 'last_name', 'role', 'managed_by','access', 'refresh')
        read_only_fields = ('id', 'managed_by',)



    def validate(self, data):
        creator = self.context['request'].user
        proposed_role = data.get('role')

        allowed = False
        if creator.role == CustomUser.Role.SUPER_ADMINISTRATOR and proposed_role == CustomUser.Role.COMPANY_ADMINISTRATOR:
            allowed = True
        elif creator.role == CustomUser.Role.COMPANY_ADMINISTRATOR and proposed_role == CustomUser.Role.COMPANY_MANAGER:
            allowed = True
        elif creator.role == CustomUser.Role.COMPANY_MANAGER and proposed_role == CustomUser.Role.FINAL_USER:
            allowed = True
        
        if not allowed:
            raise serializers.ValidationError(
                f"A '{creator.get_role_display()}' does not have permission to create a user with the '{dict(CustomUser.Role.choices).get(proposed_role)}' role."
            )
            
        return data

    def create(self, validated_data):
        manager = self.context['request'].user
        password = get_random_string(length=12)
        validated_data['managed_by'] = manager

        user = CustomUser.objects.create_user(
            password=password,
            **validated_data
        )

        creator_company = None

        if hasattr(manager, 'profile') and manager.profile.company:
            creator_company = manager.profile.company
        
        Profile.objects.create(user=user, company=creator_company) 
      
        try:
            subject = 'Welcome! Your account has been created.'
            message = (
                f'Hello {user.first_name},\n\n'
                f'An account has been created for you on our platform.'
                f'Your temporary password is: {password}\n\n'
                'We recommend changing it after your first login..\n\n'
                'Greetings,\n'
                'Archeota App Team.'
            )
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
        except Exception as e:
            print(f"Error al enviar correo a {user.email}: {e}")         

        refresh_token_obj = RefreshToken.for_user(user)

        user.access = str(refresh_token_obj.access_token)
        user.refresh = str(refresh_token_obj)

        return user


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = '__all__'


class UserProfileSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)

    class Meta:
        model = Profile
        fields = [
            'company',
            'company_name',
            'phone_number',
            'tax_id',
            'national_id',
            'digital_signature'
         ]


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = '__all__'


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
            last_name=validated_data['last_name'],
            role=CustomUser.Role.FINAL_USER
        )

        Profile.objects.create(user=user)

        refresh_token_obj = RefreshToken.for_user(user)

        user.access = str(refresh_token_obj.access_token)
        user.refresh = str(refresh_token_obj)

        return user


class UserDetailSerializer(serializers.ModelSerializer): 
    profile = UserProfileSerializer(read_only=True)
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'first_name', 'last_name', 'role', 'managed_by', 'profile'] 


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
