import requests
import uuid
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets
from .serializers import QuestionSerializer, AnswerSerializer, AssetSerializer
from .models import AgentInteractionLog, Asset, ChatSession
from rest_framework.permissions import IsAuthenticated
from django.db import IntegrityError


AGENT_API_URL = "http://35.92.83.198:5678/webhook/ArcheotaSpecialist"
REQUEST_TIMEOUT = 20


class ChatAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        question_serializer = QuestionSerializer(data=request.data)
        if not question_serializer.is_valid():
            return Response(question_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user_question = question_serializer.validated_data['question']
        requested_session_id_str = question_serializer.validated_data.get('chat_session_id')
        chat_session = None

        if requested_session_id_str:
            try:
                # Intenta obtener la sesión existente para el usuario
                chat_session, created = ChatSession.objects.get_or_create(
                    session_id=requested_session_id_str,
                    defaults={'user': request.user}
                )
                if not created and chat_session.user != request.user:
                    # El UUID existe pero pertenece a otro usuario. Esto es un conflicto.
                    # El cliente no debería poder "robar" o usar el session_id de otro.
                    # Devolvemos un error. El cliente deberá iniciar una nueva sesión (sin session_id).
                    return Response(
                        {"error": "Conflicto de ID de sesión o ID no autorizado."},
                        status=status.HTTP_409_CONFLICT # 409 Conflict es apropiado
                    )

                if not created:
                    # Si la sesión ya existía y fue obtenida, actualizamos su actividad.
                    chat_session.save() # Dispara auto_now en last_activity

            except IntegrityError:
                # Caso MUY raro: El cliente envió un UUID que ya existe globalmente (para OTRO usuario)
                # Y la base de datos previno la creación duplicada debido a unique=True en session_id.
                # (Este IntegrityError ocurriría si el user no estuviera en la parte de 'get' de get_or_create
                # y solo en 'defaults', pero como está en 'get', la verificación anterior es más probable)
                # Devolvemos un error para que el cliente sepa que este ID no se puede usar.
                return Response(
                    {"error": "El ID de sesión proporcionado no se puede usar. Intenta iniciar una nueva sesión."},
                    status=status.HTTP_409_CONFLICT
                )
        else:
            # No se proveyó ID de sesión, crear una nueva
            chat_session = ChatSession.objects.create(user=request.user)
        
        # Opcional: si es la primera interacción de una sesión nueva, usar la pregunta como título
        if chat_session.interactions.count() == 0 and not chat_session.title:
            title_text = user_question[:60] + '...' if len(user_question) > 60 else user_question
            chat_session.title = title_text
            chat_session.save(update_fields=['title', 'last_activity'])


        agent_response_text_for_client = "Error: No se recibió respuesta procesable del agente."
        actual_agent_response_or_error = None
        interaction_successful_flag = False
        error_message_for_log = None
        status_code_for_response = status.HTTP_500_INTERNAL_SERVER_ERROR

        try:
            if not requested_session_id_str:
                agent_params = {'sesionid': '', 'question': user_question}
            else:
                agent_params = {'sesionid': requested_session_id_str, 'question': user_question}
                
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

        if error_message_for_log and not agent_response_text_for_client.startswith("Error:"):
             agent_response_text_for_client = error_message_for_log
        if not actual_agent_response_or_error: 
            actual_agent_response_or_error = agent_response_text_for_client           
        
        try:
            AgentInteractionLog.objects.create(
                chat_session=chat_session,
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

        if requested_session_id_str:
            response_data = {
                'question': user_question,
                'answer': agent_answer_text_for_client,
                'chat_session_id': requested_session_id_str
            }
        else:
            response_data = {
                'question': user_question,
                'answer': agent_answer_text_for_client,
                'chat_session_id': chat_session.session_id
            }

        answer_serializer = AnswerSerializer(response_data)
        return Response(answer_serializer.data, status=status.HTTP_200_OK)

    def get(self, request, *args, **kwargs):
        return Response(
            {"message": "Por favor, use el método POST con un JSON {'question': 'su_pregunta'} para obtener una respuesta."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED # Method Not Allowed
        )


class AssetViewSet(viewsets.ModelViewSet):
    """
    API endpoint que permite crear, leer, actualizar y borrar Assets.
    Solo accesible por usuarios autenticados.
    """
    queryset = Asset.objects.all()
    serializer_class = AssetSerializer
    permission_classes = [IsAuthenticated] # Solo usuarios autenticados

    # Opcional: Si tienes un campo 'owner' en el modelo Asset y quieres
    # que se asigne automáticamente al usuario que crea el asset:
    # def perform_create(self, serializer):
    #     serializer.save(owner=self.request.user)

    # Opcional: Si quieres que los usuarios solo vean/modifiquen sus propios assets
    # (requiere el campo 'owner' en el modelo Asset):
    # def get_queryset(self):
    #     return Asset.objects.filter(owner=self.request.user)
