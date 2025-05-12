from pathlib import Path

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

    # DRF y autenticación JWT
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework.authtoken', # Puedes omitirlo si solo usas JWT

    # Allauth y sus componentes
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google', # Proveedor específico de Google

    # dj-rest-auth para integrar allauth con DRF
    'dj_rest_auth',
    'dj_rest_auth.registration', # Para endpoints de registro (si usas email/pass también)

    # Tu aplicación
    'chat',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware', # Antes de CommonMiddleware   
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
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

AUTH_USER_MODEL = 'chat.CustomUser'

# Backends de Autenticación (importante el orden)
AUTHENTICATION_BACKENDS = (
    # Necesario para loguearse en el admin de Django con email y contraseña si is_staff=True
    'django.contrib.auth.backends.ModelBackend',
    # Autenticación específica de allauth, ej: login por email y social
    'allauth.account.auth_backends.AuthenticationBackend',
)

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
}

# --- Configuración JWT (djangorestframework-simplejwt) ---
from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60), # O el tiempo que prefieras
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),    # O el tiempo que prefieras
    'ROTATE_REFRESH_TOKENS': True, # Opcional: cambia el refresh token en cada uso
    'BLACKLIST_AFTER_ROTATION': True, # Invalida el refresh token anterior
    'USER_ID_FIELD': 'id', # Campo del CustomUser model a usar como ID
    'USER_ID_CLAIM': 'user_id', # Nombre del claim en el token
}

# --- Configuración dj-rest-auth ---
REST_AUTH = {
    'USE_JWT': True,             # Indicar a dj-rest-auth que use JWT
    'SESSION_LOGIN': False,      # Deshabilitar login de sesión para una API stateless
    'JWT_AUTH_HTTPONLY': False,  # False si el frontend necesita leer el token (considera seguridad)
                                 # Para refresh tokens, HttpOnly cookies son una opción más segura.
    'JWT_AUTH_RETURN_EXPIRATION': True, # Incluir expiración en la respuesta del token
    # 'USER_DETAILS_SERIALIZER': 'path.to.your.CustomUserDetailsSerializer', # Si necesitas personalizar
}

# --- Configuración django-allauth ---
ACCOUNT_ADAPTER = 'allauth.account.adapter.DefaultAccountAdapter'
SOCIALACCOUNT_ADAPTER = 'allauth.socialaccount.adapter.DefaultSocialAccountAdapter'

ACCOUNT_USER_MODEL_USERNAME_FIELD = None # Nuestro CustomUser no tiene 'username'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_EMAIL_VERIFICATION = 'optional' # O 'none' para API y simplificar el flujo inicial.
                                        # 'mandatory' si quieres forzar verificación vía email.
SOCIALACCOUNT_EMAIL_VERIFICATION = ACCOUNT_EMAIL_VERIFICATION
SOCIALACCOUNT_EMAIL_REQUIRED = ACCOUNT_EMAIL_REQUIRED

# Configuración del proveedor Google
# ¡RECUERDA GUARDAR CLIENT_ID Y SECRET DE FORMA SEGURA, NO EN EL CÓDIGO EN PRODUCCIÓN!
# Usa variables de entorno o un sistema de gestión de secretos.
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': 'TU_GOOGLE_CLIENT_ID.apps.googleusercontent.com', # REEMPLAZA
            'secret': 'TU_GOOGLE_CLIENT_SECRET',                          # REEMPLAZA
        },
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online', # 'offline' si necesitas tokens de refresco del lado del servidor
        },
        # Para flujo API, el cliente envía el token, allauth lo verifica
        # La configuración de 'VERIFIED_EMAIL_REQUIRED' se puede añadir aquí si se desea.
        # 'VERIFIED_EMAIL_REQUIRED': True,
    }
}

# Configuración de Email para desarrollo (necesario si ACCOUNT_EMAIL_VERIFICATION no es 'none')
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
