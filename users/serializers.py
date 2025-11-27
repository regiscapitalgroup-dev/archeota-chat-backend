from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer as SimpleJWTTokenObtainPairSerializer
from .models import Profile, Company, CompanyProfile, Role, Classification, Country
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import send_mail
from django.conf import settings
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth.password_validation import validate_password


CustomUser = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    role = serializers.ChoiceField(choices=CustomUser.Role.choices, required=True)
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)

    country = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    address = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    phone_number = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    national_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    # Clasificación (Recibe el ID)
    classification = serializers.PrimaryKeyRelatedField(
        queryset=Classification.objects.all(),
        required=False,
        allow_null=True
    )

    # Company: Solo útil si eres Super Admin
    company = serializers.PrimaryKeyRelatedField(
        queryset=Company.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = CustomUser
        fields = (
            'id',
            'email',
            'first_name',
            'last_name',
            'role',
            'company',
            'country',
            'classification',
            'address',
            'phone_number',
            'national_id',
            'access',
            'refresh'
        )
        read_only_fields = ('id',)

    def validate(self, data):
            creator = self.context['request'].user
            proposed_role = data.get('role')

            if creator.role == CustomUser.Role.SUPER_ADMINISTRATOR:
                return data

            if creator.role == CustomUser.Role.COMPANY_ADMINISTRATOR:
                if proposed_role in [CustomUser.Role.COMPANY_MANAGER, CustomUser.Role.CLIENT]:
                    return data
                else:
                    raise serializers.ValidationError(
                        "As a Company Administrator, you can only create Managers or Clients."
                    )

            if creator.role == CustomUser.Role.COMPANY_MANAGER:
                if proposed_role == CustomUser.Role.CLIENT:
                    return data
                else:
                    raise serializers.ValidationError(
                        "As a Company Manager, you can only create Clients."
                    )
            raise serializers.ValidationError("You do not have permission to create new users.")

    def create(self, validated_data):
        manager = self.context['request'].user

        # 1. Extraer datos del perfil
        country_data = validated_data.pop('country', None)
        address_data = validated_data.pop('address', None)
        phone_data = validated_data.pop('phone_number', None)
        national_id_data = validated_data.pop('national_id', None)
        classification_data = validated_data.pop('classification', None)
        company_input = validated_data.pop('company', None)

        validated_data['managed_by'] = manager

        user = CustomUser.objects.create_user(
            password=None,
            **validated_data
        )

        user.set_unusable_password()
        user.is_active = False
        user.save()

        creator_company = None

        if manager.role == CustomUser.Role.SUPER_ADMINISTRATOR:
            # Si es Super Admin, usamos la que envió (o None)
            creator_company = company_input
        else:
            # Si no, forzamos la compañía del creador
            if hasattr(manager, 'profile'):
                creator_company = manager.profile.company
        
        #Profile.objects.create(user=user, company=creator_company)
        Profile.objects.create(
            user=user,
            company=creator_company,
            country=country_data,
            address=address_data,
            phone_number=phone_data,
            national_id=national_id_data,
            classification=classification_data
        )

        # 5. Enviar Correo de Activación (Igual que antes)
        self.send_activation_email(user)

        return user

    def send_activation_email(self, user):
        token_generator = PasswordResetTokenGenerator()
        token = token_generator.make_token(user)
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))

        # Ajusta esta URL a tu frontend real
        activation_link = f"https://main.d2r4dlvkgqpbf1.amplifyapp.com/activate-account/{uidb64}/{token}/"

        try:
            subject = 'Welcome! Your account has been created.'
            message = (
                f'Hello {user.first_name},\n\n'
                f'An account has been created for you on our platform.'
                f'To activate it and set your password, please click on the following link:\n\n'
                f'{activation_link}\n\n'
                'This link is for one-time use only and will expire if you change your password.\n\n'
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

        return user

    def to_representation(self, instance):
        """
        Este metodo se asegura de que, al responder el JSON,
        los datos se lean desde el Perfil y no den null.
        """
        data = super().to_representation(instance)

        # Intentamos acceder al perfil del usuario creado
        if hasattr(instance, 'profile'):
            profile = instance.profile

            # Mapeamos manualmente los campos del perfil a la respuesta
            data['country'] = profile.country
            data['address'] = profile.address
            data['phone_number'] = profile.phone_number
            data['national_id'] = profile.national_id

            # Para llaves foráneas devolvemos el ID
            data['company'] = profile.company_id if profile.company else None
            data['classification'] = profile.classification_id if profile.classification else None

        return data


class UserActivationSerializer(serializers.Serializer):
    uidb_64 = serializers.CharField(write_only=True)
    token = serializers.CharField(write_only=True)
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )

    def validate(self, attrs):
        try:
            uid = force_str(urlsafe_base64_decode(attrs['uidb_64']))
            self.user = CustomUser.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
            raise serializers.ValidationError({'uidb64': 'Enlace de activación inválido.'})

        token_generator = PasswordResetTokenGenerator()

        # Verificamos el token.
        # check_token devuelve False si el token expiró, es inválido,
        # o si el password/estado del usuario ya cambió (evitando doble uso).
        if not token_generator.check_token(self.user, attrs['token']):
            raise serializers.ValidationError(
                {'token': 'El enlace de activación es inválido, expiró o ya fue utilizado.'})

        return attrs

    def save(self):
        password = self.validated_data['password']
        self.user.set_password(password)
        self.user.is_active = True
        self.user.save()
        return self.user


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = '__all__'


class UserProfileSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)
    company_id = serializers.IntegerField(source='company.id', read_only=True, allow_null=True)
    classification = serializers.PrimaryKeyRelatedField(
        queryset=Classification.objects.all(),
        allow_null=True,
        required=False
    )

    class Meta:
        model = Profile
        fields = [
            'company',
            'company_id',
            'company_name',
            'phone_number',
            'get_profile_picture',
            'tax_id',
            'national_id',
            'digital_signature',
            'classification',
            'address',
            'country'
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
    role_description = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'first_name', 'last_name', 'role', 'role_description', 'managed_by', 'profile'] 

    def get_role_description(self, obj):
            try:
                role_code = obj.role
                role_instance = Role.objects.get(code=role_code)
                return role_instance.description
            except Role.DoesNotExist:
                return "Unknow Role"                 


class CustomTokenObtainPairSerializer(SimpleJWTTokenObtainPairSerializer): 
    def validate(self, attrs):
        data = super().validate(attrs) 

        user_serializer = UserDetailSerializer(self.user)
        data['user'] = user_serializer.data
        return data


class LogoutSerializer(serializers.Serializer): # Para Logout
    refresh = serializers.CharField()

    default_error_messages = {
        'bad_token': 'The token is invalid or has expired.'
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
        
        user = CustomUser.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=profile_data['company_name'],
            last_name='(Company)',
        )

        CompanyProfile.objects.create(user=user, **profile_data)
        
        refresh = RefreshToken.for_user(user)
        user.access = str(refresh.access_token)
        user.refresh = str(refresh)
        
        return user

class UserUpdateSerializer(serializers.ModelSerializer):
    prodid = UserProfileSerializer()

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'role', 'profile']

    def validate(self, data):
        request = self.context.get('request')
        if not request or not hasattr(request, 'user'):
            return data

        user = request.user
        if user.role not in [CustomUser.Role.SUPER_ADMINISTRATOR,
                             CustomUser.Role.COMPANY_ADMINISTRATOR,
                             CustomUser.Role.COMPANY_MANAGER]:
            # Si el usuario no tiene permisos, lanzamos un error
            raise serializers.ValidationError({
                "profile": {
                    "classification": "No tienes permiso para establecer este campo."
                }
            })
        return data

    def update(self, instance, validated_data):
        # Manejar la actualización anidada
        profile_data = validated_data.pop('profile', None)

        # Actualizar campos de CustomUser (first_name, last_name, role)
        instance = super().update(instance, validated_data)

        # Actualizar campos del Profile
        if profile_data:
            profile_instance = instance.profile

            # Iteramos sobre los datos del perfil y los asignamos
            for attr, value in profile_data.items():
                setattr(profile_instance, attr, value)

            profile_instance.save()

        return instance


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


class ClassificationSerializer(serializers.ModelSerializer):
    # company_id sigue siendo write_only
    company_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = Classification
        fields = ['id', 'name', 'color', 'company_id']
        read_only_fields = ['id']

    def create(self, validated_data):
        # Ya no necesitamos validar roles complejos, solo Super Admin llega aquí.
        company_id_input = validated_data.pop('company_id', None)

        # Validación estricta: Super Admin SIEMPRE debe decir para qué empresa es.
        if not company_id_input:
            raise serializers.ValidationError(
                {"company_id": "Es obligatorio especificar la empresa para crear una clasificación."})

        try:
            target_company = Company.objects.get(pk=company_id_input)
        except Company.DoesNotExist:
            raise serializers.ValidationError({"company_id": "La compañía especificada no existe."})

        # Validar duplicados dentro de esa empresa
        if Classification.objects.filter(company=target_company, name=validated_data['name']).exists():
            raise serializers.ValidationError(
                {"name": f"Ya existe la clasificación '{validated_data['name']}' en la empresa {target_company.name}."})

        return Classification.objects.create(company=target_company, **validated_data)

# class ClassificationSerializer(serializers.ModelSerializer):
#     # Campo opcional para que el Super Admin especifique la empresa
#     company_id = serializers.IntegerField(write_only=True, required=False)
#
#     class Meta:
#         model = Classification
#         fields = ['id', 'name', 'color', 'company_id']
#         read_only_fields = ['id']
#
#     def create(self, validated_data):
#         user = self.context['request'].user
#         company_id_input = validated_data.pop('company_id', None)
#         target_company = None
#
#         # 1. Lógica para SUPER ADMIN
#         if user.role == CustomUser.Role.SUPER_ADMINISTRATOR:
#             # OBLIGATORIO: Debe enviar company_id
#             if company_id_input:
#                 try:
#                     target_company = Company.objects.get(pk=company_id_input)
#                 except Company.DoesNotExist:
#                     raise serializers.ValidationError({"company_id": "La compañía especificada no existe."})
#             else:
#                 # Eliminamos el 'elif' que buscaba en su perfil.
#                 raise serializers.ValidationError("Como Super Admin, es obligatorio especificar el 'company_id' para crear una clasificación.")
#
#         # 2. Lógica para COMPANY ADMIN / MANAGER
#         else:
#             # Ellos NO pueden enviar company_id, usamos la suya
#             if not hasattr(user, 'profile') or not user.profile.company:
#                 raise serializers.ValidationError("El usuario no pertenece a ninguna compañía.")
#             target_company = user.profile.company
#
#         # 3. Validar duplicados
#         if Classification.objects.filter(company=target_company, name=validated_data['name']).exists():
#             raise serializers.ValidationError({"name": f"Ya existe la clasificación '{validated_data['name']}' en la empresa {target_company.name}."})
#
#         # 4. Crear
#         return Classification.objects.create(company=target_company, **validated_data)


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ['code', 'name']


class UserBasicSerializer(serializers.ModelSerializer):
    """
    Serializador simple para mostrar información básica de un usuario (ej. el manager).
    """
    class Meta:
        model = CustomUser
        fields = ['id', 'first_name', 'last_name', 'email']


class UserListSerializer(serializers.ModelSerializer):
    """
    Serializador enriquecido para el listado de usuarios.
    """
    # 1. Role: Mostramos la descripción en lugar del código
    role = serializers.SerializerMethodField()

    # 3. Clasificación y Color: Los sacamos del perfil
    classification = serializers.CharField(source='profile.classification.name', read_only=True, allow_null=True)
    color = serializers.CharField(source='profile.classification.color', read_only=True, allow_null=True)

    dependents_count = serializers.SerializerMethodField()

    company = serializers.CharField(source='profile.company.name', read_only=True, allow_null=True)
    address = serializers.CharField(source='profile.address', read_only=True, allow_null=True)

    class Meta:
        model = CustomUser
        fields = [
            'id',
            'first_name',
            'last_name',
            'email',
            'role',  # Ahora será la descripción
            'dependents_count',  # Ahora será un objeto
            'is_active',  # Campo nuevo solicitado
            'classification',  # Campo nuevo
            'color',  # Campo nuevo
            'company',
            'address'
        ]

    def to_representation(self, instance):
        """
        Este metodo se ejecuta justo antes de devolver el JSON.
        Aquí podemos quitar campos dinámicamente.
        """
        # Obtenemos la data estándar con todos los campos
        data = super().to_representation(instance)

        # Obtenemos al usuario que está haciendo la petición (request.user)
        request = self.context.get('request')

        # Si NO existe request o el usuario NO es SUPER_ADMIN...
        if request and request.user.role != CustomUser.Role.SUPER_ADMINISTRATOR:
            data.pop('company', None)

        return data

    def get_role(self, obj):
        """
        Busca la descripción del rol en el modelo Role basándose en el código almacenado en el usuario.
        """
        try:
            role_instance = Role.objects.get(code=obj.role)
            return role_instance.description or role_instance.code  # Fallback al código si no hay descripción
        except Role.DoesNotExist:
            return obj.get_role_display()

    def get_dependents_count(self, obj):
        """
        Devuelve el número de usuarios que dependen de este usuario.
        Si es FINAL_USER, devuelve 0.
        """
        if obj.role == CustomUser.Role.CLIENT:
            return ""

        # Intentamos obtener el valor pre-calculado por la vista (annotate)
        if hasattr(obj, 'dependents_count'):
            return obj.dependents_count

        # Fallback: Si por alguna razón no viene anotado, hacemos la consulta
        return obj.managed_users.count()


class UserDependentSerializer(serializers.ModelSerializer):
    """
    Serializador específico para la lista anidada de dependientes.
    Muestra solo los datos solicitados: nombre, país, ID nacional y clasificación.
    """
    # Campos extraídos del perfil
    country = serializers.CharField(source='profile.country', read_only=True, allow_null=True)
    national_id = serializers.CharField(source='profile.national_id', read_only=True, allow_null=True)
    classification_name = serializers.CharField(source='profile.classification.name', read_only=True, allow_null=True)
    classification_color = serializers.CharField(source='profile.classification.color', read_only=True, allow_null=True)

    # Opcional: Incluimos la descripción del rol para contexto (ej. "Cliente")
    role = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            'id',  # Siempre útil para referencias
            'first_name',
            'last_name',
            'role',  # Descripción del rol
            'country',  # Nuevo
            'national_id',  # Nuevo
            'classification_name',
            'classification_color'
        ]

    def get_role(self, obj):
        # Reutilizamos la lógica para mostrar la descripción bonita
        try:
            role_instance = Role.objects.get(code=obj.role)
            return role_instance.description or role_instance.code
        except Role.DoesNotExist:
            return obj.get_role_display()



class UserManagementDetailSerializer(serializers.ModelSerializer):
    """
    Serializador para ver el detalle completo de un usuario subordinado.
    """
    company_id = serializers.IntegerField(source='profile.company.id', read_only=True, allow_null=True)
    company_name = serializers.CharField(source='profile.company.name', read_only=True, allow_null=True)

    country = serializers.CharField(source='profile.country', read_only=True, allow_null=True)
    classification_id = serializers.CharField(source='profile.classification.id', read_only=True, allow_null=True)
    classification_name = serializers.CharField(source='profile.classification.name', read_only=True, allow_null=True)
    classification_color = serializers.CharField(source='profile.classification.color', read_only=True, allow_null=True)
    address = serializers.CharField(source='profile.address', read_only=True, allow_null=True)
    phone_number = serializers.CharField(source='profile.phone_number', read_only=True, allow_null=True)
    national_id = serializers.CharField(source='profile.national_id', read_only=True, allow_null=True)

    # --- NUEVO CAMPO: FOTO DE PERFIL ---
    # Usamos la propiedad del modelo 'get_profile_picture'
    profile_picture = serializers.CharField(source='profile.get_profile_picture', read_only=True, allow_null=True)
    # -----------------------------------

    role_description = serializers.SerializerMethodField()
    managed_by = UserBasicSerializer(read_only=True)

    dependents = UserDependentSerializer(source='managed_users', many=True, read_only=True)

    class Meta:
        model = CustomUser
        fields = [
            'id',
            'first_name',
            'last_name',
            'email',
            'role',
            'role_description',
            'is_active',
            'company_id',
            'company_name',
            'managed_by',
            'country',
            'classification_id',
            'classification_name',
            'classification_color',
            'address',
            'phone_number',
            'national_id',
            'profile_picture',
            'dependents'
        ]

    def get_role_description(self, obj):
        try:
            role_instance = Role.objects.get(code=obj.role)
            return role_instance.description or role_instance.code
        except Role.DoesNotExist:
            return obj.get_role_display()

    def to_representation(self, instance):
        """
        Lógica dinámica: Ocultar 'dependents' si la lista está vacía o el usuario es CLIENT.
        """
        data = super().to_representation(instance)

        # Verificamos si la lista de dependientes está vacía
        # (Nota: instance.managed_users.exists() es eficiente si no se ha pre-cargado)
        if not data['dependents']:
            data.pop('dependents', None)

        return data


class ProfileDataSerializer(serializers.ModelSerializer):
    """
    Serializador auxiliar para editar datos del perfil,
    EXCLUYENDO la foto.
    """
    country = serializers.CharField(required=False) # Mapeo si usas el nombre
    # O usa PrimaryKeyRelatedField si envias IDs para pais y clasificacion

    company = serializers.PrimaryKeyRelatedField(
        queryset=Company.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = Profile
        fields = [
            'phone_number',
            'tax_id',
            'national_id',
            'country',
            'address',
            'classification',
            'company'
        ]

    def validate_company(self, value):
        """
        Validación de seguridad:
        Solo el SUPER_ADMIN puede cambiar la compañía de un usuario.
        """
        user = self.context['request'].user

        # Si el usuario NO es Super Admin y está intentando enviar este campo...
        if user.role != CustomUser.Role.SUPER_ADMINISTRATOR:
            # ... lanzamos un error de permiso.
            raise serializers.ValidationError(
                "You do not have permission to change a user's carrier."
            )
        return value


class UserManagementUpdateSerializer(serializers.ModelSerializer):
    """
    Permite a un Manager editar datos del usuario y cambiar su password.
    NO permite cambiar 'managed_by' ni la foto.
    """
    password = serializers.CharField(write_only=True, required=False, style={'input_type': 'password'})
    profile = ProfileDataSerializer(required=False)
    # country = serializers.CharField(source='country', read_only=True, allow_null=True)

    class Meta:
        model = CustomUser
        fields = [
            'first_name',
            'last_name',
            'email',
            'role',
            'is_active',
            'password',
            'profile'
        ]

    def to_internal_value(self, data):
        data = data.copy()
        profile_fields = {'country', 'phone_number', 'address', 'national_id'}
        profile_data = {}
        for field in profile_fields:
            if field in data:
                profile_data[field] = data.pop(field)

        if profile_data:
            data['profile'] = profile_data

        return super().to_internal_value(data)

    def update(self, instance, validated_data):
        # 1. Actualizar Password si viene en el request
        password = validated_data.pop('password', None)
        if password:
            instance.set_password(password)

        # 2. Actualizar datos del Perfil
        profile_data = validated_data.pop('profile', None)
        if profile_data:
            profile = instance.profile
            for attr, value in profile_data.items():
                setattr(profile, attr, value)
            profile.save()

        # 3. Actualizar resto de datos del Usuario (first_name, role, etc.)
        return super().update(instance, validated_data)


# --- 3. SERIALIZADOR EXCLUSIVO PARA FOTO ---
class UserProfilePictureSerializer(serializers.Serializer):
    profile_picture = serializers.ImageField(write_only=True, required=True)

    def update(self, instance, validated_data):
        profile = instance.profile
        profile.profile_picture_file = validated_data['profile_picture']
        profile.save()
        return instance


class ManagerSelectSerializer(serializers.ModelSerializer):
    """Lista simple de managers para el dropdown de selección"""
    full_name = serializers.SerializerMethodField()

    company_id = serializers.IntegerField(source='profile.company.id', read_only=True, allow_null=True)
    company_name = serializers.CharField(source='profile.company.name', read_only=True, allow_null=True)

    class Meta:
        model = CustomUser
        fields = [
            'id',
            'first_name',
            'last_name',
            'full_name',
            'email',
            'company_id',
            'company_name'
        ]

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"


class ClientAssignmentListSerializer(serializers.ModelSerializer):
    """
    Lista de clientes con detalles visuales para la reasignación.
    Campos: ID, Nombre, Apellido, País, National ID, Clasificación (Nombre+Color).
    """
    country = serializers.CharField(source='profile.country', read_only=True, allow_null=True)
    national_id = serializers.CharField(source='profile.national_id', read_only=True, allow_null=True)
    classification_name = serializers.CharField(source='profile.classification.name', read_only=True, allow_null=True)
    classification_color = serializers.CharField(source='profile.classification.color', read_only=True, allow_null=True)
    classification_id = serializers.IntegerField(source='profile.classification.id', read_only=True, allow_null=True)

    class Meta:
        model = CustomUser
        fields = [
            'id',
            'first_name',
            'last_name',
            'country',
            'national_id',
            'classification_name',
            'classification_color',
            'classification_id'
        ]


class AssignmentActionSerializer(serializers.Serializer):
    """
    Valida la asignación de un cliente a un manager.
    """
    client_id = serializers.IntegerField(required=True)
    # manager_id es opcional porque en "desasignar" no se usa
    manager_id = serializers.IntegerField(required=False, allow_null=True)

    def validate(self, data):
        user = self.context['request'].user
        client_id = data.get('client_id')
        manager_id = data.get('manager_id')

        # 1. Validar Cliente
        try:
            client = CustomUser.objects.get(pk=client_id, role=CustomUser.Role.CLIENT)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError({"client_id": "Cliente no encontrado."})

        # 2. Validar Manager (si se envía)
        manager = None
        if manager_id:
            try:
                manager = CustomUser.objects.get(pk=manager_id, role=CustomUser.Role.COMPANY_MANAGER)
            except CustomUser.DoesNotExist:
                raise serializers.ValidationError({"manager_id": "Manager no encontrado."})

        # 3. Validación de Compañía (Crucial para seguridad multi-tenant)
        # Si soy Company Admin, el cliente y el manager deben ser de MI empresa.
        if user.role == CustomUser.Role.COMPANY_ADMINISTRATOR:
            user_company = user.profile.company
            if client.profile.company != user_company:
                raise serializers.ValidationError("No puedes gestionar clientes de otra compañía.")
            if manager and manager.profile.company != user_company:
                raise serializers.ValidationError("No puedes asignar a un manager de otra compañía.")

        # Si soy Super Admin, cliente y manager deben ser de la MISMA empresa entre ellos.
        if user.role == CustomUser.Role.SUPER_ADMINISTRATOR and manager:
            if client.profile.company != manager.profile.company:
                raise serializers.ValidationError("El cliente y el manager deben pertenecer a la misma compañía.")

        # Guardamos los objetos en el contexto para usarlos en la vista
        data['client_obj'] = client
        data['manager_obj'] = manager
        return data


class ExternalRegisterSerializer(serializers.ModelSerializer):
    """
    Serializador para registro público de usuarios externos (sin compañía).
    """

    # Campos del Perfil (Entradas del formulario)
    country = serializers.CharField(required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    phone_number = serializers.CharField(required=False, allow_blank=True)
    national_id = serializers.CharField(required=False, allow_blank=True)

    # Salida de tokens
    #access = serializers.CharField(read_only=True)
    #refresh = serializers.CharField(read_only=True)

    class Meta:
        model = CustomUser
        fields = [
            'id',
            'email',
            'first_name',
            'last_name',
            'country',
            'address',
            'phone_number',
            'national_id',
            #'access',
            #'refresh'
        ]
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
            'email': {'required': True}
        }

    def create(self, validated_data):
        # 1. Extraer datos del perfil
        country_data = validated_data.pop('country', None)
        address_data = validated_data.pop('address', None)
        phone_data = validated_data.pop('phone_number', None)
        national_id_data = validated_data.pop('national_id', None)

        # 2. Crear Usuario Base
        # Forzamos el rol FINAL_USER y que esté inactivo
        user = CustomUser.objects.create_user(
            password=None,
            role=CustomUser.Role.FINAL_USER,
            is_active=False,
            **validated_data
        )

        # 3. Crear Perfil asociado (Sin Compañía)
        Profile.objects.create(
            user=user,
            company=None,  # <-- Sin compañía
            country=country_data,  # Mapeo: country -> pais
            address=address_data,  # Mapeo: address -> direccion
            phone_number=phone_data,
            national_id=national_id_data,
            # clasificacion se queda en null por defecto
        )

        # 4. Generar Tokens automáticamente para login inmediato
        #refresh_token = RefreshToken.for_user(user)
        #user.access = str(refresh_token.access_token)
        #user.refresh = str(refresh_token)
        self.send_activation_email(user)

        return user

    def send_activation_email(self, user):
        token_generator = PasswordResetTokenGenerator()
        token = token_generator.make_token(user)
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))

        current_site = settings.SITE_URL

        # Ajusta esta URL a tu frontend real
        activation_link = f"{current_site}/activate-account/{uidb64}/{token}/"

        try:
            subject = 'Welcome! Your account has been created.'
            message = (
                f'Hello {user.first_name},\n\n'
                f'An account has been created for you on our platform.'
                f'To activate it and set your password, please click on the following link:\n\n'
                f'{activation_link}\n\n'
                'This link is for one-time use only and will expire if you change your password.\n\n'
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

        return user

    def to_representation(self, instance):
        """
        Asegurar que la respuesta incluya los datos del perfil recién creado.
        """
        data = super().to_representation(instance)
        if hasattr(instance, 'profile'):
            profile = instance.profile
            data['country'] = profile.country
            data['address'] = profile.address
            data['phone_number'] = profile.phone_number
            data['national_id'] = profile.national_id
        return data
