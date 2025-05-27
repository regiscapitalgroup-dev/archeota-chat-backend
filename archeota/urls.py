from django.contrib import admin
from django.urls import path, include
from chat.views import ChatAPIView, AssetViewSet

from django.conf import settings # Importar settings
from django.conf.urls.static import static # Importar static
from rest_framework.routers import DefaultRouter

# Crea un router y registra nuestro viewset con él.
router = DefaultRouter()
router.register(r'assets', AssetViewSet, basename='asset') # 'assets' será el prefijo de la URL


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/auth/', include('users.urls')),
    path('api/v1/chat/', ChatAPIView.as_view(), name='chat_api'),
    path('api/v1/', include(router.urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)