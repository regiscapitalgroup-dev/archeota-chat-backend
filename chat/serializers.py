from rest_framework import serializers
from .models import Asset, ChatSession, AgentInteractionLog
from django.contrib.auth import get_user_model

USER_MODEL = get_user_model()


class QuestionSerializer(serializers.Serializer):
    question = serializers.CharField(max_length=2000, trim_whitespace=True) # Aumentamos max_length
    chat_session_id = serializers.UUIDField(required=False, allow_null=True, format='hex_verbose')


class AdditionalQuestionSerializer(serializers.Serializer):
    question = serializers.CharField(max_length=500)


class AnswerSerializer(serializers.Serializer):
    general_response = serializers.CharField()
    additional_questions = AdditionalQuestionSerializer(many=True)
    chat_session_id = serializers.UUIDField(read_only=True, format='hex_verbose')


class AssetSerializer(serializers.ModelSerializer):
    # Campo para mostrar el nombre del propietario (solo lectura)
    owner_username = serializers.CharField(source='owner.username', read_only=True)

    # Opcional: Si quieres un control más explícito sobre el campo 'photo'
    # photo = serializers.ImageField(required=True, allow_null=False)
    # Por defecto, ModelSerializer inferirá 'required=True' y 'allow_null=False'
    # de la definición del modelo (null=False, blank=False).

    class Meta:
        model = Asset
        fields = [
            'id',  # El PK, será read_only por defecto
            'owner_username', # Nuestro campo personalizado de solo lectura para mostrar el owner
            # No incluimos 'owner' (el ForeignKey) aquí si siempre se va a establecer
            # desde request.user en la vista y no queremos que el cliente lo envíe.
            'name',
            'value',
            'value_over_time',
            'photo',
            'syntasis_summary',
            'full_conversation_history',
            'asset_date'  # auto_now=True, será read_only por defecto
        ]
        # No es estrictamente necesario listar 'id' y 'asset_date' en read_only_fields
        # ya que ModelSerializer los trata como read-only por defecto.
        # 'owner_username' ya está definido como read_only=True arriba.
        # Si quisiéramos ser explícitos:
        # read_only_fields = ['id', 'asset_date']


class ChatSessionSerializer(serializers.ModelSerializer):
    email = serializers.ReadOnlyField(source='user.email') # Muestra el email

    class Meta:
        model = ChatSession
        fields = [
            'id',
            'session_id',
            'email',
            'start_time',
            'last_activity',
            'title'
        ]

class AgentInteractionLogSerializer(serializers.ModelSerializer):
    # Opcional: Si quieres mostrar algún detalle de chat_session además de su ID
    # chat_session_uuid = serializers.UUIDField(source='chat_session.session_id', read_only=True)

    class Meta:
        model = AgentInteractionLog
        fields = [
            'id',
            'chat_session',
            'question_text',
            'answer_text',
            'timestamp',
            'is_successful',
            'error_message'
        ]
        # Puedes marcar campos como read_only si es necesario,
        # aunque para una lista no es estrictamente requerido.
        read_only_fields = ['timestamp']
