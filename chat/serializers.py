from rest_framework import serializers
from .models import ChatSession, AgentInteractionLog 
from django.contrib.auth import get_user_model


USER_MODEL = get_user_model()


class QuestionSerializer(serializers.Serializer):
    question = serializers.CharField(max_length=2000, trim_whitespace=True) 
    chat_session_id = serializers.UUIDField(required=False, allow_null=True, format='hex_verbose')


class AdditionalQuestionSerializer(serializers.Serializer):
    question = serializers.CharField(max_length=500)


class AnswerSerializer(serializers.Serializer):
    general_response = serializers.CharField()
    summary = serializers.CharField()
    additional_questions = AdditionalQuestionSerializer(many=True) 
    extra_questions = AdditionalQuestionSerializer(many=True)
    chat_session_id = serializers.UUIDField(read_only=True, format='hex_verbose')
    category = serializers.CharField(required=False)
    attributes = serializers.DictField(required=False)


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
    last_question = serializers.SerializerMethodField()
    last_answer = serializers.SerializerMethodField()

    class Meta:
        model = AgentInteractionLog
        fields = [
            'id',
            'chat_session',
            'question_text',
            'answer_text',
            'last_question',
            'last_answer',
            'summary',
            'category',
            'attributes',
            'timestamp',
            'is_successful',
            'error_message'
        ]
        read_only_fields = ['timestamp']

    def get_last_question(self, obj):
        last_interaction = self.context.get('last_interaction')
        return last_interaction.question_text if last_interaction else None

    def get_last_answer(self, obj):
        last_interaction = self.context.get('last_interaction')
        return last_interaction.answer_text if last_interaction else None
