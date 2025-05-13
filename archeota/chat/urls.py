from django.urls import path
from .views import ChatAPIView # Importar la nueva vista APIView


urlpatterns = [
    # La URL raíz dentro de esta app ('api/chat/' según el archivo principal)
    # apunta al método .as_view() de la clase ChatAPIView
    path('chat/', ChatAPIView.as_view(), name='chat_api'),
]
