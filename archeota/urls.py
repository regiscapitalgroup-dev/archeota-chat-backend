from django.contrib import admin
from django.urls import path, include, re_path
from accounts.views import GoogleLogin, GoogleLoginCallback, LoginPage
from chat.views import ChatAPIView, AssetViewSet
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from django.conf import settings # Importar settings
from django.conf.urls.static import static # Importar static
from rest_framework.routers import DefaultRouter

# Crea un router y registra nuestro viewset con él.
router = DefaultRouter()
router.register(r'assets', AssetViewSet, basename='asset') # 'assets' será el prefijo de la URL


urlpatterns = [
    path('admin/', admin.site.urls),
    path("login/", LoginPage.as_view(), name="login"),
    path("api/v1/auth/", include("dj_rest_auth.urls")),
    re_path(r"^api/v1/auth/accounts/", include("allauth.urls")),
    path("api/v1/auth/registration/", include("dj_rest_auth.registration.urls")),
    path("api/v1/auth/google/", GoogleLogin.as_view(), name="google_login"),
    path("api/v1/auth/google/callback/", GoogleLoginCallback.as_view(), name="google_login_callback"),
    path('api/v1/chat/', ChatAPIView.as_view(), name='chat_api'),
    path('api/v1/schema/', SpectacularAPIView.as_view(), name='schema'),
    # Optional UI:
    path('api/v1/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/v1/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('api/v1/', include(router.urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)