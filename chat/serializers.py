from rest_framework import serializers
from .models import Asset


class QuestionSerializer(serializers.Serializer):
    question = serializers.CharField(max_length=2000, trim_whitespace=True) # Aumentamos max_length
    chat_session_id = serializers.UUIDField(required=False, allow_null=True, format='hex_verbose')


class AnswerSerializer(serializers.Serializer):
    question = serializers.CharField(read_only=True)
    answer = serializers.CharField(read_only=True)
    chat_session_id = serializers.UUIDField(read_only=True, format='hex_verbose')


class AssetSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.email')
    
    class Meta:
        model = Asset
        fields = 'id', 'owner', 'name', 'value', 'value_over_time', 'photo', 'syntasis_summary', 'full_conversation_history',   # Incluye todos los campos del modelo Asset
