from django.contrib import admin
from django.urls import path, include


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('chat.urls')),
    path('auth/', include('accounts.urls')),


    # --- Endpoints de dj-rest-auth ---
    # Para login, logout, password reset (si también usas email/password vía dj-rest-auth)
    # path('api/auth/', include('dj_rest_auth.urls')),
    # Para registro email/password vía dj-rest-auth (si lo quieres junto a tu /api/register/)
    # Puedes comentar esta línea si tu /api/register/ es el único método de registro email/pass.
    # path('api/auth/registration/', include('dj_rest_auth.registration.urls')),

    # --- Endpoint para Google Social Login vía dj-rest-auth ---
    # Esta es la URL que tu cliente llamará después de obtener un token de Google.
    # El `include('dj_rest_auth.social.urls_google')` debería funcionar si
    # `dj-rest-auth[with_social]` está bien instalado y el provider de Google está en INSTALLED_APPS.
    # path('api/auth/google/', include('dj_rest_auth.social.urls_google')),
]