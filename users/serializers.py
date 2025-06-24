from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer as SimpleJWTTokenObtainPairSerializer
from .models import Profile


CustomUser = get_user_model()


class UserProfileSerializer(serializers.ModelSerializer):
    role_id = serializers.IntegerField(source='role.id', read_only=True, allow_null=True)
    role_code = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = [
            'phone_number',
            'national_id',
            'role_id', 
            'role_code',
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
