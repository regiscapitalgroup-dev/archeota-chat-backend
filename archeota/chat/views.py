import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status 
from .serializers import QuestionSerializer, AnswerSerializer
from .models import AgentInteractionLog
from rest_framework.permissions import AllowAny


AGENT_API_URL = "http://35.92.83.198:5678/webhook/ArcheotaAgent"
REQUEST_TIMEOUT = 20


class ChatAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        question_serializer = QuestionSerializer(data=request.data)
        if not question_serializer.is_valid():
            return Response(question_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user_question = question_serializer.validated_data['question']

        agent_params = {'question': user_question}
        agent_answer_text = "Error: No se recibió respuesta procesable del agente." # Default

        actual_agent_response_or_error = None
        interaction_successful_flag = False
        error_message_for_log = None
        try:
            response = requests.get(
                AGENT_API_URL,
                params=agent_params,
                timeout=REQUEST_TIMEOUT
            )
            
            response.raise_for_status()

            try:
                api_data = response.json()
                if 'output' in api_data: 
                    actual_agent_response_or_error = api_data['output']
                else: 
                    actual_agent_response_or_error = response.text

                if actual_agent_response_or_error is not None:
                    interaction_successful_flag = True
                    agent_answer_text_for_client = actual_agent_response_or_error 


            except requests.exceptions.JSONDecodeError:
                actual_agent_response_or_error = response.text
                interaction_successful_flag = True 
                agent_answer_text_for_client = actual_agent_response_or_error
            
            except Exception as e_parse: 
                actual_agent_response_or_error = response.text 
                error_message_for_log = f"Error parseando JSON de agente: {e_parse}"
                agent_answer_text_for_client = "Error procesando respuesta del agente." 

        except requests.exceptions.Timeout:
            error_message_for_log = "Timeout: La solicitud al agente externo excedió el tiempo límite."
            actual_agent_response_or_error = error_message_for_log 
            agent_answer_text_for_client = error_message_for_log 
            return Response({"error": error_message_for_log}, status=status.HTTP_504_GATEWAY_TIMEOUT) 
        except requests.exceptions.ConnectionError:
            error_message_for_log = "Error de Conexión: No se pudo conectar con el servicio del agente externo."
            actual_agent_response_or_error = error_message_for_log
            agent_answer_text_for_client = error_message_for_log
            return Response({"error": error_message_for_log}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except requests.exceptions.HTTPError as e_http:
            error_message_for_log = f"Error del Agente: El servicio del agente devolvió un error HTTP {e_http.response.status_code}."
            try: 
                actual_agent_response_or_error = e_http.response.text
            except:
                actual_agent_response_or_error = error_message_for_log
            agent_answer_text_for_client = error_message_for_log
            return Response({"error": error_message_for_log, "agent_response": actual_agent_response_or_error}, status=status.HTTP_502_BAD_GATEWAY)
        except requests.exceptions.RequestException as e_req:
            error_message_for_log = f"Error de Red/Solicitud: {e_req}"
            actual_agent_response_or_error = error_message_for_log
            agent_answer_text_for_client = error_message_for_log
            return Response({"error": error_message_for_log}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e_general:
            error_message_for_log = f"Error Interno del Servidor Inesperado: {e_general}"
            actual_agent_response_or_error = error_message_for_log
            agent_answer_text_for_client = "Ocurrió un error inesperado."

            print(f"Error inesperado en ChatAPIView: {e_general}")
        try:
            AgentInteractionLog.objects.create(
                # user=authenticated_user,
                question_text=user_question,
                answer_text=actual_agent_response_or_error, 
                is_successful=interaction_successful_flag,
                error_message=error_message_for_log 
            )
        except Exception as e_log:
            print(f"ERROR CRÍTICO: No se pudo guardar AgentInteractionLog: {e_log}")
            # import logging
            # logger = logging.getLogger(__name__)
            # logger.error(f"Failed to save AgentInteractionLog: {e_log}", exc_info=True)
        
        if not interaction_successful_flag and error_message_for_log:
             return Response({"error": agent_answer_text_for_client, "detail": error_message_for_log}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


        response_data = {
            'question': user_question,
            'answer': agent_answer_text_for_client
        }

        answer_serializer = AnswerSerializer(response_data)
        return Response(answer_serializer.data, status=status.HTTP_200_OK)

    def get(self, request, *args, **kwargs):
        return Response(
            {"message": "Por favor, use el método POST con un JSON {'question': 'su_pregunta'} para obtener una respuesta."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED # Method Not Allowed
        )
