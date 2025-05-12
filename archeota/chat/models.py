from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from django.conf import settings # Para obtener el modelo de usuario AUTH_USER_MODEL


# your_app_name/models.py
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('El campo Email es obligatorio')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser debe tener is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser debe tener is_superuser=True.')
        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, verbose_name='correo electrónico')
    first_name = models.CharField(max_length=150, blank=True, verbose_name='nombres')
    last_name = models.CharField(max_length=150, blank=True, verbose_name='apellidos')
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = CustomUserManager()
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    def __str__(self):
        return self.email

class AgentInteractionLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, # Referencia a tu CustomUser
        on_delete=models.SET_NULL, # Si el usuario se borra, mantenemos el log pero sin asociar usuario
        null=True, # Permite logs incluso si el usuario es anónimo (si lo permitieras) o se borra
        blank=True, # No requerido en formularios (aunque aquí se llena programáticamente)
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
