from django.db import models
from django.utils import timezone
from django.conf import settings 


class AgentInteractionLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, # Referencia a CustomUser
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
