from django.contrib import admin
from .models import AgentInteractionLog, Asset, ChatSession


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('session_id', 'user_email', 'start_time', 'last_activity', 'title_shortened')
    list_filter = ('user', 'start_time', 'last_activity')
    search_fields = ('session_id', 'user__email', 'title')
    readonly_fields = ('session_id', 'start_time', 'last_activity')

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email del Usuario'

    def title_shortened(self, obj):
        if obj.title and len(obj.title) > 50:
            return obj.title[:50] + '...'
        return obj.title
    title_shortened.short_description = 'Título'


@admin.register(AgentInteractionLog)
class AgentInteractionLogAdmin(admin.ModelAdmin):
    # Actualiza para reflejar la relación con ChatSession
    list_display = ('get_session_id', 'get_user_email_from_session', 'question_text_shortened', 'answer_text_shortened', 'timestamp', 'is_successful')
    list_filter = ('timestamp', 'is_successful', 'chat_session__user')
    search_fields = ('question_text', 'answer_text', 'chat_session__session_id', 'chat_session__user__email')
    readonly_fields = ('timestamp', 'chat_session', 'question_text', 'answer_text', 'is_successful', 'error_message')

    def get_session_id(self, obj):
        return obj.chat_session.session_id
    get_session_id.short_description = 'ID Sesión'
    get_session_id.admin_order_field = 'chat_session__session_id'

    def get_user_email_from_session(self, obj):
        return obj.chat_session.user.email if obj.chat_session and obj.chat_session.user else "N/A"
    get_user_email_from_session.short_description = 'Email Usuario (Sesión)'
    get_user_email_from_session.admin_order_field = 'chat_session__user__email'

    # ... (tus métodos _shortened existentes) ...
    def question_text_shortened(self, obj):
        # ...
        pass
    def answer_text_shortened(self, obj):
        # ...
        pass

    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return True # O False si no quieres permitir borrar
    