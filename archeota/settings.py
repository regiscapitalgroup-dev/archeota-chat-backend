import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv
import dj_database_url

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['https://main.d2r4dlvkgqpbf1.amplifyapp.com', 
                 'https://archeota-chat-backend-e8799cd9ed08.herokuapp.com',
                 'localhost', '127.0.0.1', '*']

CSRF_TRUSTED_ORIGINS = [
    'https://archeota-chat-backend-e8799cd9ed08.herokuapp.com',
]

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "rest_framework.authtoken",
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist', 
    "users",
    "chat",
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware', # Antes de CommonMiddleware   
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'djangorestframework_camel_case.middleware.CamelCaseMiddleWare',
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

#DATABASES = {
#    'default': {
#        'ENGINE': 'django.db.backends.sqlite3',
#        'NAME': BASE_DIR / 'db.sqlite3',
#    }
#}

DATABASES = {
  'default': dj_database_url.config(
       default=os.getenv('DATABASE_URL')
    )
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

TIME_ZONE = 'America/Monterrey'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / "staticfiles"


# Configuración para archivos subidos por el usuario (media)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media' # BASE_DIR es tu directorio raíz del proyecto

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'users.CustomUser'

# django-cors-headers
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
    CORS_ALLOW_CREDENTIALS = True
else:
    CORS_ALLOWED_ORIGINS = [
        "http://localhost:3000/",
        "https://main.d2r4dlvkgqpbf1.amplifyapp.com",
    ]



# djangorestframework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
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

AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",
)

# djangorestframework-simplejwt
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=2), # Duración del token de acceso
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),    # Duración del token de refresco
    "ROTATE_REFRESH_TOKENS": False, # Si es True, cada vez que se refresca, se da un nuevo refresh token
    "BLACKLIST_AFTER_ROTATION": True, # Si ROTATE_REFRESH_TOKENS es True, el viejo refresh token se añade a la blacklist
    "UPDATE_LAST_LOGIN": True, # Actualiza el campo last_login del usuario al loguearse

    "ALGORITHM": "HS256",
    # "SIGNING_KEY": settings.SECRET_KEY, # Ya está por defecto
    "AUTH_HEADER_TYPES": ("Bearer",), # Tipo de cabecera de autenticación
    "USER_ID_FIELD": "id", # Campo del modelo de usuario para el user_id en el token
    "USER_ID_CLAIM": "user_id", # Nombre del claim para el user_id
}

# dj-rest-auth
REST_AUTH = {
    'USE_JWT': True, # Indispensable para usar JWT
    'JWT_AUTH_HTTPONLY': False, # True: El token no es accesible por JS en el cliente (más seguro si usas cookies)
                                # False: El token es accesible por JS (necesario si no usas cookies y manejas tokens en JS)
    'JWT_AUTH_COOKIE': 'access-token',          # Nombre de la cookie para el token de acceso
    'JWT_AUTH_REFRESH_COOKIE': 'refresh-token', # Nombre de la cookie para el token de refresco
    'SESSION_LOGIN': False, # Deshabilitar login por sesión si solo usas JWT

    # Serializers personalizados
    'USER_DETAILS_SERIALIZER': 'users.serializers.CustomUserDetailsSerializer',
    'REGISTER_SERIALIZER': 'users.serializers.CustomRegisterSerializer',
    # 'LOGIN_SERIALIZER': 'dj_rest_auth.serializers.LoginSerializer', # El default funciona bien con email
    
    # Para que el registro devuelva el usuario y los tokens
    'REGISTER_VIEW_SETS_USER_DETAILS': True, 
}

GOOGLE_OAUTH_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
