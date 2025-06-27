from rest_framework import serializers
from .models import Asset, ChatSession, AgentInteractionLog, AssetCategory  
from django.contrib.auth import get_user_model

USER_MODEL = get_user_model()


class QuestionSerializer(serializers.Serializer):
    question = serializers.CharField(max_length=2000, trim_whitespace=True) 
    chat_session_id = serializers.UUIDField(required=False, allow_null=True, format='hex_verbose')


class AdditionalQuestionSerializer(serializers.Serializer):
    question = serializers.CharField(max_length=500)


class AnswerSerializer(serializers.Serializer):
    general_response = serializers.CharField()
    additional_questions = AdditionalQuestionSerializer(many=True)
    chat_session_id = serializers.UUIDField(read_only=True, format='hex_verbose')
    category = serializers.CharField(required=False)
    attributes = serializers.DictField(required=False)


class AssetSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source='owner.username', read_only=True)

    class Meta:
        model = Asset
        fields = [
            'id', 
            'owner_username', 
            'name',
            'value',
            'value_over_time',
            'photo',
            'syntasis_summary',
            'full_conversation_history',
            'category',
            'attributes',
            'asset_date' 
        ]


class ChatSessionSerializer(serializers.ModelSerializer):
    email = serializers.ReadOnlyField(source='user.email') 

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
        read_only_fields = ['timestamp']


class AssetCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetCategory
        fields = ['id', 'category_name', 'attributes']
