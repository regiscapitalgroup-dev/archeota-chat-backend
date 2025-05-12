from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView # Para JWT si no usas dj-rest-auth para login normal

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/chat/', include('chat.urls')),
    
    # Endpoints de dj-rest-auth para login/logout/reset pass (email/pass) y registro
    path('api/auth/', include('dj_rest_auth.urls')),
    path('api/auth/registration/', include('dj_rest_auth.registration.urls')),

    # Endpoint específico para Google Login a través de dj-rest-auth
    # dj-rest-auth utiliza allauth para la lógica social.
    # La URL para el login social con Google (y otros proveedores) es manejada
    # por las vistas que dj-rest-auth importa o adapta de allauth.
    # Si instalaste dj-rest-auth[with_social], estas URLs deberían funcionar.
    # La URL específica del proveedor se construye a menudo a partir del 'key' del proveedor
    # o se proveen módulos de URL específicos como 'dj_rest_auth.social.urls_google'.
    # Este último es el que causó el error antes, y debería funcionar si la instalación es correcta.
    path('api/auth/google/', include('dj_rest_auth.social.urls_google')), # Para el flujo de login/connect de Google

    # Aquí irían tus otras URLs de API, por ejemplo:
    # path('api/your_app_name/', include('your_app_name.urls')),
]