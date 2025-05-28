from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer as SimpleJWTTokenObtainPairSerializer


CustomUser = get_user_model()


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


class UserDetailSerializer(serializers.ModelSerializer): # Para Detalles de Usuario
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'first_name', 'last_name'] # Ajusta según los campos que quieras mostrar


class CustomTokenObtainPairSerializer(SimpleJWTTokenObtainPairSerializer): # Para Login, añadiendo datos del usuario
    """
    Personaliza el serializer de TokenObtainPair para añadir datos del usuario
    en la respuesta del login.
    """
    def validate(self, attrs):
        data = super().validate(attrs) # Llama al validador padre para obtener tokens
        
        # Añadir datos del usuario a la respuesta
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
        # No es necesario importar TokenError si confías en que simplejwt lo maneje internamente
        # al llamar a blacklist()
        try:
            RefreshToken(self.token).blacklist()
        except Exception: # Captura una excepción más genérica si TokenError no es suficiente
            self.fail('bad_token')


class GoogleAuthSerializer(serializers.Serializer):
    id_token = serializers.CharField()
