from django.urls import path
from .views import ChatAPIView, AssetAPIView

urlpatterns = [
    path('chat/', ChatAPIView.as_view(), name='chat_api'),
    path('assets/', AssetAPIView.as_view(), name='asset-list-create'),
    path('assets/<int:pk>/', AssetAPIView.as_view(), name='asset-detail-update-delete')    
]
