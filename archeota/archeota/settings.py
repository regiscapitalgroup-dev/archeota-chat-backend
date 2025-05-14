from pathlib import Path
from datetime import timedelta
from decouple import config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-z-64d7-b%cm3*t(5o*dj8#!*cyna!s*5232-149uwxc_d4l1c0'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'django.contrib.sites', # Requerido por allauth

    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'rest_framework.authtoken', 

    # Allauth y sus componentes
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    # Proveedor específico de Google para allauth
    'allauth.socialaccount.providers.google',

    # dj-rest-auth para integrar allauth con DRF
    'dj_rest_auth',
    'sslserver',
    'accounts',
    'chat',
    
]

SITE_ID = 1

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware', # Antes de CommonMiddleware   
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'djangorestframework_camel_case.middleware.CamelCaseMiddleWare',
    'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'archeota.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'archeota.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'accounts.CustomUser'


GOOGLE_OAUTH_CLIENT_ID=config("GOOGLE_OAUTH_CLIENT_ID")
GOOGLE_OAUTH_CLIENT_SECRET=config("GOOGLE_OAUTH_CLIENT_SECRET")
GOOGLE_OAUTH_CALLBACK_URL=config("GOOGLE_OAUTH_CALLBACK_URL")

# Backends de Autenticación
AUTHENTICATION_BACKENDS = (
    # Backend de allauth (maneja social y, opcionalmente, email/password)
    'allauth.account.auth_backends.AuthenticationBackend',
    # Backend de Django por defecto (necesario para login en admin con superuser)
    'django.contrib.auth.backends.ModelBackend',
)

# Requerido por django.contrib.sites
SITE_ID = 1

# --- Configuración DRF ---
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        # Cambia según tus necesidades, ej: IsAuthenticatedOrReadOnly
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'djangorestframework_camel_case.render.CamelCaseJSONRenderer',
        'djangorestframework_camel_case.render.CamelCaseBrowsableAPIRenderer',
    ),

    'DEFAULT_PARSER_CLASSES': (
        'djangorestframework_camel_case.parser.CamelCaseFormParser',
        'djangorestframework_camel_case.parser.CamelCaseMultiPartParser',
        'djangorestframework_camel_case.parser.CamelCaseJSONParser',
    ),    
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60), # Duración del token de acceso (ej: 1 hora)
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),   # Duración del token de refresco (ej: 7 días)
    'ROTATE_REFRESH_TOKENS': True, # El refresh token cambia en cada uso (más seguro)
    'BLACKLIST_AFTER_ROTATION': True, # Invalida el refresh token anterior después de la rotación
                                      # Requiere 'rest_framework_simplejwt.token_blacklist' en INSTALLED_APPS
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY, # Reutiliza la SECRET_KEY de Django
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    'JWK_URL': None,
    'LEEWAY': 0,

    'AUTH_HEADER_TYPES': ('Bearer',), # Espera 'Bearer <token>' en la cabecera Authorization
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id', # PK de tu CustomUser model
    'USER_ID_CLAIM': 'user_id', # Nombre del claim que contendrá el ID de usuario
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',

    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'TOKEN_USER_CLASS': 'rest_framework_simplejwt.models.TokenUser',

    'JTI_CLAIM': 'jti', # JWT ID

    'UPDATE_LAST_LOGIN': True, # Actualiza el campo last_login del usuario al loguearse
}

# --- Configuración dj-rest-auth ---
REST_AUTH = {
    'USE_JWT': True,                 # Fundamental: dj-rest-auth usará JWT
    'SESSION_LOGIN': False,          # No usaremos sesiones de Django para la API
    'JWT_AUTH_HTTPONLY': False,      # Permite al cliente JS acceder a los tokens si es necesario
                                     # (para refresh tokens, HttpOnly cookies es más seguro si el cliente lo soporta)
    'JWT_AUTH_RETURN_EXPIRATION': True, # Incluir la expiración del token en la respuesta
    # Opcional: Serializer para detalles del usuario devueltos por /user/ endpoint
    # 'USER_DETAILS_SERIALIZER': 'your_app_name.serializers.CustomUserDetailsSerializer',
    # Opcional: Serializer para el login (si no usas el de simplejwt directamente)
    # 'LOGIN_SERIALIZER': 'dj_rest_auth.serializers.LoginSerializer',
}

# --- Configuración django-allauth (adaptada para API) ---
ACCOUNT_ADAPTER = 'allauth.account.adapter.DefaultAccountAdapter'
SOCIALACCOUNT_ADAPTER = 'allauth.socialaccount.adapter.DefaultSocialAccountAdapter'

ACCOUNT_USER_MODEL_USERNAME_FIELD = None # Tu CustomUser no tiene 'username'
ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*']
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_EMAIL_VERIFICATION = 'none' # Para API, 'none' u 'optional' suele ser más simple.
                                     # 'mandatory' requeriría un flujo de verificación de email.
SOCIALACCOUNT_EMAIL_VERIFICATION = ACCOUNT_EMAIL_VERIFICATION # Heredar de ACCOUNT_
SOCIALACCOUNT_EMAIL_REQUIRED = True        # Heredar de ACCOUNT_
SOCIALACCOUNT_AUTO_SIGNUP = True     # Crear automáticamente un usuario Django si el login social es exitoso
                                     # y no hay cuenta existente con ese email.

# Configuración del proveedor Google para allauth
# ¡RECUERDA OBTENER CLIENT_ID Y SECRET DE GOOGLE CLOUD CONSOLE!
# ¡NO LOS GUARDES DIRECTAMENTE EN EL CÓDIGO EN PRODUCCIÓN! Usa variables de entorno.
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': GOOGLE_OAUTH_CLIENT_ID, 
            'secret': GOOGLE_OAUTH_CLIENT_SECRET, 
        },
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        },
        # Es buena idea requerir que Google haya verificado el email
        'VERIFIED_EMAIL_REQUIRED': True,
    }
}

# Configuración de Email (para desarrollo, si necesitas enviar correos de verificación)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
