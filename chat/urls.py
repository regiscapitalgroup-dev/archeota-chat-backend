from django.urls import path
from .views import ChatAPIView, UserChatSessionListView, ChatSessionInteractionListView, AssociateChatSessionView

urlpatterns = [
    path('', ChatAPIView.as_view(), name='chat_api'),
    path('sessions/', UserChatSessionListView.as_view(), name='user-chat-session-list'),
    path('sessions/associate/', AssociateChatSessionView.as_view(), name='chat-session-associate'),
    path('sessions/<uuid:session_uuid>/', ChatSessionInteractionListView.as_view(),
         name='chat-session-interaction-list'),  
]
