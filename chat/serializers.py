from rest_framework import serializers
from .models import Asset, ChatSession, AgentInteractionLog
from django.contrib.auth import get_user_model

USER_MODEL = get_user_model()


class QuestionSerializer(serializers.Serializer):
    question = serializers.CharField(max_length=2000, trim_whitespace=True) # Aumentamos max_length
    chat_session_id = serializers.UUIDField(required=False, allow_null=True, format='hex_verbose')


class AnswerSerializer(serializers.Serializer):
    question = serializers.CharField(read_only=True)
    answer = serializers.CharField(read_only=True)
    chat_session_id = serializers.UUIDField(read_only=True, format='hex_verbose')


class AssetPlainSerializer(serializers.Serializer):
    # Campos del modelo definidos explícitamente
    id = serializers.IntegerField(read_only=True)

    name = serializers.CharField(max_length=250)
    value = serializers.CharField(max_length=30)
    value_over_time = serializers.CharField(max_length=50)
    photo = serializers.ImageField(
        required=True,      # Corresponde a null=False, blank=False
        allow_null=False    # Corresponde a null=False
    )
    syntasis_summary = serializers.CharField(
        allow_blank=True,   # Corresponde a blank=True
        allow_null=True,    # Corresponde a null=True
        required=False,     # No es requerido si blank y null son True
        style={'base_template': 'textarea.html'} # Opcional, para renderizado en forms de DRF
    )
    full_conversation_history = serializers.CharField(
        allow_blank=True,
        allow_null=True,
        required=False,
        style={'base_template': 'textarea.html'}
    )
    asset_date = serializers.DateField(
        read_only=True      # auto_now=True implica que es gestionado por el modelo
    )

    def create(self, validated_data):
        """
        Crea y devuelve una nueva instancia de `Asset`, dados los datos validados.
        """
        # Si 'owner' no se establece por `CurrentUserDefault()` y esperas que la vista lo pase:
        # owner = validated_data.pop('owner', None) # o self.context['request'].user
        # if not owner and self.context.get('request'):
        #     owner = self.context['request'].user
        #     validated_data['owner'] = owner # Asegúrate de que owner esté en validated_data

        # Si owner viene en validated_data (porque es PrimaryKeyRelatedField y no CurrentUserDefault)
        # entonces se pasa directamente.
        return Asset.objects.create(**validated_data)

    def update(self, instance, validated_data):
        """
        Actualiza y devuelve una instancia existente de `Asset`, dados los datos validados.
        """
        instance.owner = validated_data.get('owner', instance.owner)
        instance.name = validated_data.get('name', instance.name)
        instance.value = validated_data.get('value', instance.value)
        instance.value_over_time = validated_data.get('value_over_time', instance.value_over_time)

        # Para ImageField, si se proporciona un nuevo archivo, se actualiza.
        # Si no se proporciona, se mantiene el existente.
        # Si se proporciona `None` o `False` y el campo lo permite, se podría borrar la imagen.
        # En tu caso, `photo` es `null=False, blank=False`, por lo que siempre debe tener un valor.
        # DRF maneja la actualización de ImageField de forma similar a ModelSerializer.
        instance.photo = validated_data.get('photo', instance.photo)

        instance.syntasis_summary = validated_data.get('syntasis_summary', instance.syntasis_summary)
        instance.full_conversation_history = validated_data.get('full_conversation_history', instance.full_conversation_history)

        # asset_date es read_only y se actualiza por auto_now=True en el modelo
        instance.save()
        return instance

    # Opcional: validaciones a nivel de campo o a nivel de objeto
    # def validate_name(self, value):
    #     """
    #     Comprueba que el nombre del asset no sea algo prohibido.
    #     """
    #     if "prohibido" in value.lower():
    #         raise serializers.ValidationError("El nombre contiene una palabra prohibida.")
    #     return value

    # def validate(self, data):
    #     """
    #     Comprueba condiciones entre múltiples campos.
    #     """
    #     # Ejemplo: if data['start_date'] > data['end_date']:
    #     #     raise serializers.ValidationError("La fecha de fin no puede ser anterior a la fecha de inicio")
    #     return data


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
    chat_session_uuid = serializers.UUIDField(source='chat_session.session_id', read_only=True)

    class Meta:
        model = AgentInteractionLog
        fields = [
            'id',
            'chat_session', # Por defecto, mostrará el ID de ChatSession
            'chat_session_uuid', # Si añadiste el campo arriba
            'question_text',
            'answer_text',
            'timestamp',
            'is_successful',
            'error_message'
        ]
        # Puedes marcar campos como read_only si es necesario,
        # aunque para una lista no es estrictamente requerido.
        read_only_fields = ['timestamp']
