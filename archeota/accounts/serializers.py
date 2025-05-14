from rest_framework import serializers
from .models import CustomUser # O from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from dj_rest_auth.serializers import SocialLoginSerializer


class CustomGoogleLoginSerializer(SocialLoginSerializer):
    # El frontend envía 'credential', que es el id_token de Google
    credential = serializers.CharField(required=True, write_only=True)

    # Opcional: si quieres capturar estos campos aunque no se usen para la lógica de auth
    clientId = serializers.CharField(required=False, write_only=True, allow_blank=True)
    select_by = serializers.CharField(required=False, write_only=True, allow_blank=True)

    def validate(self, attrs):
        # Mapeamos el valor de 'credential' al campo 'id_token'
        # que el adaptador de Google de allauth (usado por SocialLoginView) espera.
        # SocialLoginSerializer y el adaptador buscarán 'id_token' o 'access_token'.

        id_token_from_credential = attrs.pop('credential', None)
        if id_token_from_credential:
            attrs['id_token'] = id_token_from_credential # Aquí hacemos el mapeo

        # Eliminamos los otros campos si no los vamos a usar,
        # para que no interfieran con la validación del adaptador.
        attrs.pop('clientId', None)
        attrs.pop('select_by', None)

        # Llamamos a la validación del padre (SocialLoginSerializer)
        # que a su vez llamará al adapter.complete_login()
        try:
            attrs = super().validate(attrs)
        except serializers.ValidationError as e:
            # Puedes inspeccionar 'e.detail' si necesitas depurar errores del adaptador
            raise e
        return attrs


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Añadir claims personalizados al token si es necesario
        # token['first_name'] = user.first_name
        # token['email'] = user.email
        # ...

        return token

    # Opcional: para añadir datos extra a la respuesta del login, no solo al token
    # def validate(self, attrs):
    #     data = super().validate(attrs)
    #     # data['user_id'] = self.user.id
    #     # data['email'] = self.user.email
    #     # data['first_name'] = self.user.first_name
    #     return data


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer para el registro de nuevos usuarios.
    Maneja la validación de contraseña y la creación del usuario.
    Usa 'password2' para la confirmación de la contraseña.
    """
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        # validators=[validate_password] # Opcional: descomentar para validación robusta
    )

    class Meta:
        model = CustomUser
        # --- CAMBIO DE NOMBRE DEL CAMPO EN FIELDS ---
        fields = ('email', 'first_name', 'last_name', 'password')
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
            'email': {'required': True},
        }

    def validate(self, attrs):
        """
        Validación a nivel de objeto.
        Verifica que las contraseñas (password y password2) coincidan.
        """
        password = attrs.get('password')

        # Opcional: Ejecutar validadores de contraseña de Django aquí
        try:
            validate_password(password, user=None) # user=None para creación
        except DjangoValidationError as e:
            raise serializers.ValidationError({'password': list(e.messages)})

        return attrs

    def create(self, validated_data):
        """
        Crea y retorna una nueva instancia de CustomUser.
        """
        # --- CAMBIO DE NOMBRE DEL CAMPO AL HACER POP ---
        password = validated_data.pop('password')

        user = CustomUser.objects.create_user(password=password, **validated_data)
        return user
