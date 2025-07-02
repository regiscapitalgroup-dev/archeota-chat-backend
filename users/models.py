from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _ 
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.db.models.signals import post_save


class Role(models.Model):
    code = models.CharField(max_length=50, unique=True, help_text="Role Code")
    description = models.TextField(blank=True, null=True, help_text="Role Description")
    is_active = models.BooleanField(default=True, blank=False, null=False, help_text='Role Active')

    def __str__(self):
        return self.code

    class Meta:
        verbose_name = "Rol"
        verbose_name_plural = "Roles"


@receiver(post_migrate)
def create_initial_roles(sender, **kwargs):
    if sender.name == 'users':
        Role = sender.get_model('Role')
        ROLES = ['final_user', 'company', 'administrator']
        for role_name in ROLES:
            Role.objects.get_or_create(code=role_name)


class Company(models.Model):
    name = models.CharField(max_length=200, help_text="Company's Name")

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Company"
        verbose_name_plural = "Companies"


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_('email is required'))
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
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))

        extra_fields.setdefault('first_name', 'Admin')
        extra_fields.setdefault('last_name', 'User')
        
        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(_('email address'), unique=True)
    first_name = models.CharField(_('first name'), max_length=150)
    last_name = models.CharField(_('last name'), max_length=150)
    
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True) 
    date_joined = models.DateTimeField(default=timezone.now)
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True, related_name="users")

    objects = CustomUserManager()

    USERNAME_FIELD = 'email' 
    REQUIRED_FIELDS = ['first_name', 'last_name'] 

    def __str__(self):
        return self.email
    
    
class Profile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='profile')
    # role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True, related_name="users")
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True, related_name="companies")
    phone_number = models.CharField(max_length=30, blank=True, null=True, verbose_name=_('Phone Number'))
    # avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name=_('avatar'))
    national_id = models.CharField(max_length=100, blank=True, null=True, verbose_name=_('National ID'))
    digital_signature = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Profile de {self.user.email}'
    
    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "Users Profiles"   


@receiver(post_save, sender=CustomUser)
def create_user_profile_on_registration(sender, instance, created, **kwargs):
    """
    Crea un perfil vacío (UserProfile o CompanyProfile) para un nuevo usuario
    basado en el rol asignado durante el registro.
    """
    # Solo se ejecuta cuando se crea un nuevo usuario
    if created and instance.role:
        if instance.role.code == 'final_user':
            Profile.objects.create(user=instance)
        elif instance.role.name == 'company':
            CompanyProfile.objects.create(user=instance)         


class CompanyProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='companyprofile')
    company_name = models.CharField(max_length=255)
    website = models.URLField(blank=True, null=True)
    tax_id = models.CharField(max_length=50, blank=True, null=True, verbose_name="ID Fiscal")
    
    def __str__(self):
        return f'Perfil de Compañía de {self.user.email}'        


class GoogleProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    google_id = models.CharField(max_length=255, unique=True, blank=True, null=True)

    def __str__(self):
        return f"Google Profile for {self.user.email}"
