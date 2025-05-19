from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model


class AgentInteractionLog(models.Model):
    user = models.ForeignKey(
        get_user_model(), # Referencia a CustomUser
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='agent_interactions',
        verbose_name='usuario'
    )
    question_text = models.TextField(verbose_name='texto de la pregunta')
    answer_text = models.TextField(verbose_name='texto de la respuesta del agente', blank=True, null=True)
    timestamp = models.DateTimeField(default=timezone.now, verbose_name='fecha y hora')
    is_successful = models.BooleanField(default=False, verbose_name='interacción exitosa')
    error_message = models.TextField(blank=True, null=True, verbose_name='mensaje de error (si hubo)')

    def __str__(self):
        user_email = self.user.email if self.user else "Sistema/Anónimo"
        return f"Pregunta de {user_email} a las {self.timestamp.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        verbose_name = "Registro de Interacción con Agente"
        verbose_name_plural = "Registros de Interacciones con Agente"
        ordering = ['-timestamp']


class Asset(models.Model):
    owner = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='chat_asset')
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
