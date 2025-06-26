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


class AssetCategory(models.Model):
    category_name = models.CharField(max_length=100, null=False, blank=False)
    attributes = models.JSONField(null=True, blank=True)


    def __str__(self) -> str:
        return self.category_name
    
    class Meta:
        verbose_name = "Asset Category"
        verbose_name_plural = "Assets Categories"


class Asset(models.Model):
    owner = models.ForeignKey(USER_MODEL, 
                              on_delete=models.CASCADE, 
                              related_name='chat_asset')
    name = models.CharField(max_length=250)
    value = models.CharField(max_length=30, null=True, blank=True)
    value_over_time = models.CharField(max_length=50, null=True, blank=True)
    photo = models.ImageField(upload_to='assets_photos/', null=True, blank=True)
    syntasis_summary = models.TextField(blank=True, null=True)
    full_conversation_history = models.TextField(blank=True, null=True)
    category = models.ForeignKey(AssetCategory, on_delete=models.CASCADE, blank=True, null=True)
    attributes = models.JSONField(null=True, blank=True)
    asset_date = models.DateField(null=True, blank=True, auto_now=True)

    def __str__(self) -> str:
        return self.name
    
    class Meta:
        verbose_name = 'Asset'
        verbose_name_plural = 'Assets'


class ClaimAction(models.Model):
    tycker_symbol = models.CharField(max_length=255, null=True, blank=True)
    company_name = models.TextField(null=True, blank=True)
    exchange = models.TextField(null=True, blank=True)
    lawsuit_type = models.TextField(null=True, blank=True)
    eligibility	= models.CharField(max_length=255, null=True, blank=True)
    potencial_claim	= models.CharField(max_length=255, null=True, blank=True)
    total_settlement_fund = models.CharField(max_length=255, null=True, blank=True)
    filing_date = models.CharField(max_length=255, null=True, blank=True)
    claim_deadline = models.CharField(max_length=255, null=True, blank=True)
    law_firm_handing_case = models.CharField(max_length=255, null=True, blank=True)
    case_docket_number = models.CharField(max_length=255, null=True, blank=True)
    jurisdiction = models.CharField(max_length=255, null=True, blank=True)
    claim_status = models.CharField(max_length=255, null=True, blank=True)
    official_claim_filing_link = models.CharField(max_length=255, null=True, blank=True)
    last_update = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self) -> str:
        return self.tycker_symbol
    
    class Meta:
        verbose_name = "Claim Action"
        verbose_name_plural = "Claim Actions"
    