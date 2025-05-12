from rest_framework import serializers


class QuestionSerializer(serializers.Serializer):
    """Serializer para validar la pregunta entrante."""
    # Define el campo esperado en el JSON de la petición POST
    question = serializers.CharField(max_length=2000, trim_whitespace=True) # Aumentamos max_length

    # No necesitamos más campos por ahora

class AnswerSerializer(serializers.Serializer):
    """Serializer para formatear la respuesta JSON saliente."""
    # Incluimos la pregunta original para dar contexto
    question = serializers.CharField(read_only=True)
    # El campo principal con la respuesta del agente
    answer = serializers.CharField(read_only=True)
