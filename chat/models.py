from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
import uuid

USER_MODEL = get_user_model()

class ChatSession(models.Model):
    session_id = models.UUIDField(default=uuid.uuid4, 
                                  editable=False, 
                                  db_index=True, 
                                  verbose_name='Session ID')
    user = models.ForeignKey(USER_MODEL, 
                             on_delete=models.CASCADE, 
                             related_name='char_sessions', 
                             verbose_name='User',
                             null=True,
                             blank=True)
    start_time = models.DateTimeField(default=timezone.now, 
                                      verbose_name='Begin Session')
    last_activity = models.DateTimeField(auto_now=True, verbose_name='Last Activity')
    title = models.CharField(max_length=255, blank=True, null=True, verbose_name='Title')

    def __str__(self) -> str:
        user_email = self.user.email if self.user else "Anonymous"
        return f"Session {self.session_id} of {user_email}"
    
    class Meta:
        verbose_name = 'Chat Session'
        verbose_name_plural = 'Chat Sessions'
        ordering=['-last_activity']


class AgentInteractionLog(models.Model):     
    chat_session = models.ForeignKey(
        ChatSession, on_delete=models.CASCADE, 
        related_name='interactions',
        verbose_name='chat session'
    )
    question_text = models.TextField(verbose_name='texto de la pregunta')
    answer_text = models.TextField(verbose_name='texto de la respuesta del agente', blank=True, null=True)
    summary = models.TextField(null=True, blank=True)
    category = models.CharField(max_length=100, null=True, blank=True)
    attributes = models.JSONField(null=True, blank=True)
    summary = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(default=timezone.now, verbose_name='fecha y hora')
    is_successful = models.BooleanField(default=False, verbose_name='interacción exitosa')
    error_message = models.TextField(blank=True, null=True, verbose_name='mensaje de error (si hubo)')

    def __str__(self):
        user_email = self.chat_session.user.email if self.chat_session and self.chat_session.user else "N/A"
        return f"Interacción en sesión {self.chat_session.session_id} ({user_email}) a las {self.timestamp.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        verbose_name = "Registro de Interacción con Agente"
        verbose_name_plural = "Registros de Interacciones con Agente"
        ordering = ['-timestamp']
