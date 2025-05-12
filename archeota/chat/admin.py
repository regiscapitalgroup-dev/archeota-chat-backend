from django.contrib import admin
from .models import CustomUser, AgentInteractionLog # Asegúrate que CustomUser esté importado si no lo has registrado aún

# Si aún no has registrado tu CustomUser model, aquí un ejemplo básico:
# from django.contrib.auth.admin import UserAdmin
# class CustomUserAdmin(UserAdmin):
#     list_display = ('email', 'first_name', 'last_name', 'is_staff', 'date_joined', 'is_active')
#     search_fields = ('email', 'first_name', 'last_name')
#     ordering = ('-date_joined',)
#     # Necesitas definir fieldsets y add_fieldsets si heredas de UserAdmin con un CustomUser
#     # Esto puede ser complejo; revisa la documentación de Django para CustomUser y UserAdmin.
#     # Por ahora, una registración simple:
# if not admin.site.is_registered(CustomUser): # Evitar registrarlo dos veces
#    admin.site.register(CustomUser) # O usa CustomUserAdmin si lo defines


@admin.register(AgentInteractionLog)
class AgentInteractionLogAdmin(admin.ModelAdmin):
    list_display = ('get_user_email', 'question_text_shortened', 'answer_text_shortened', 'timestamp', 'is_successful')
    list_filter = ('timestamp', 'is_successful', 'user') # Permite filtrar por estos campos
    search_fields = ('question_text', 'answer_text', 'user__email') # Búsqueda por texto y email de usuario
    readonly_fields = ('timestamp', 'user', 'question_text', 'answer_text', 'is_successful', 'error_message') # Hacer todos los campos de solo lectura en el detalle

    def get_user_email(self, obj):
        return obj.user.email if obj.user else "N/A"
    get_user_email.short_description = 'Email del Usuario'
    get_user_email.admin_order_field = 'user__email' # Permite ordenar por email

    def question_text_shortened(self, obj):
        return (obj.question_text[:75] + '...') if len(obj.question_text) > 75 else obj.question_text
    question_text_shortened.short_description = 'Pregunta'

    def answer_text_shortened(self, obj):
        if obj.answer_text:
            return (obj.answer_text[:75] + '...') if len(obj.answer_text) > 75 else obj.answer_text
        return "N/A"
    answer_text_shortened.short_description = 'Respuesta del Agente'

    # Para evitar que se puedan añadir o borrar logs desde el admin (usualmente se crean solo programáticamente)
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False # O True si quieres permitir borrar logs
    