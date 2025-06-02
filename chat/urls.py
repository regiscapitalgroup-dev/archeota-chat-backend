from django.urls import path
from .views import ChatAPIView, AssetAPIView, UserChatSessionListView, ChatSessionInteractionListView

urlpatterns = [
    path('chat/', ChatAPIView.as_view(), name='chat_api'),
    path('chat/sessions/', UserChatSessionListView.as_view(), name='user-chat-session-list'),
    path('chat/sessions/<uuid:session_uuid>/', ChatSessionInteractionListView.as_view(),
         name='chat-session-interaction-list'),
    path('assets/', AssetAPIView.as_view(), name='asset-list-create'),
    path('assets/<int:pk>/', AssetAPIView.as_view(), name='asset-detail-update-delete')    
]
