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
                             verbose_name='User')
    start_time = models.DateTimeField(default=timezone.now, 
                                      verbose_name='Begin Session')
    last_activity = models.DateTimeField(auto_now=True, verbose_name='Last Activity')
    title = models.CharField(max_length=255, blank=True, null=True, verbose_name='Title')

    def __str__(self) -> str:
        return f"Session {self.session_id} of {self.user.email}"
    
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


class Asset(models.Model):
    owner = models.ForeignKey(USER_MODEL, 
                              on_delete=models.CASCADE, 
                              related_name='chat_asset')
    name = models.CharField(max_length=250)
    value = models.CharField(max_length=30)
    value_over_time = models.CharField(max_length=50)
    photo = models.ImageField(upload_to='assets_photos/', null=False, blank=False)
    syntasis_summary = models.TextField(blank=True, null=True)
    full_conversation_history = models.TextField(blank=True, null=True)
    asset_date = models.DateField(null=True, blank=True, auto_now=True)

    def __str__(self) -> str:
        return self.name
    
    class Meta:
        verbose_name = 'Asset'
        verbose_name_plural = 'Assets'
