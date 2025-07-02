from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from asset.views import ImportDataView
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/auth/', include('users.urls')),
    path('api/v1/chat/', include('chat.urls')),
    path('api/v1/assets/', include('asset.urls')),
    path('api/v1/transactions/import-data/', ImportDataView.as_view(), name='import-data'),

    #path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    #path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    #path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),    
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
