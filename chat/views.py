import requests
import os
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import (QuestionSerializer, AnswerSerializer, AssetSerializer, 
ChatSessionSerializer, AgentInteractionLogSerializer)
from .models import AgentInteractionLog, Asset, ChatSession
from rest_framework.permissions import IsAuthenticated
from django.db import IntegrityError
from rest_framework.parsers import MultiPartParser, FormParser # Para subir imágenes
from django.shortcuts import get_object_or_404
import uuid


AGENT_API_URL = os.getenv("AGENT_API_URL")
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
                chat_session, created = ChatSession.objects.get_or_create(
                    session_id=requested_session_id_str,
                    defaults={'user': request.user}
                )
                if not created and chat_session.user != request.user:
                   return Response(
                        {"error": "Session ID conflict or unauthorized ID."},
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
                    {"error": "The provided session ID cannot be used. Please try starting a new session."},
                    status=status.HTTP_409_CONFLICT
                )
        else:
            # No se proveyó ID de sesión, crear una nueva
            chat_session = ChatSession.objects.create(user=request.user)
            requested_session_id_str = chat_session.session_id

        
        # Opcional: si es la primera interacción de una sesión nueva, usar la pregunta como título
        if chat_session.interactions.count() == 0 and not chat_session.title:
            title_text = user_question[:60] + '...' if len(user_question) > 60 else user_question
            chat_session.title = title_text
            chat_session.save(update_fields=['title', 'last_activity'])


        agent_response_text_for_client = "Error: No actionable response was received from the agent."
        actual_agent_response_or_error = None
        interaction_successful_flag = False
        error_message_for_log = None
        status_code_for_response = status.HTTP_500_INTERNAL_SERVER_ERROR

        try:
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

                print(f"actual_agent_response_or_error: {actual_agent_response_or_error}")
                print(f"agent_answer_text_for_client: {agent_answer_text_for_client}")

            except requests.exceptions.JSONDecodeError:
                actual_agent_response_or_error = response.text
                interaction_successful_flag = True 
                agent_answer_text_for_client = actual_agent_response_or_error
            
            except Exception as e_parse: 
                actual_agent_response_or_error = response.text 
                error_message_for_log = f"Error parsing agent JSON: {e_parse}"
                agent_answer_text_for_client = "Error processing agent response." 

        except requests.exceptions.Timeout:
            error_message_for_log = "Timeout: The request to the external agent exceeded the time limit."
            actual_agent_response_or_error = error_message_for_log 
            agent_answer_text_for_client = error_message_for_log
            return Response({"error": error_message_for_log}, status=status.HTTP_504_GATEWAY_TIMEOUT) 

        except requests.exceptions.ConnectionError:
            error_message_for_log = "Connection Error: Could not connect to the external agent service"
            actual_agent_response_or_error = error_message_for_log
            agent_answer_text_for_client = error_message_for_log
            
            return Response({"error": error_message_for_log}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except requests.exceptions.HTTPError as e_http:
            error_message_for_log = f"Agent Error: The agent service returned an HTTP error {e_http.response.status_code}."
            try: 
                actual_agent_response_or_error = e_http.response.text
            except:
                actual_agent_response_or_error = error_message_for_log
            agent_answer_text_for_client = error_message_for_log
            return Response({"error": error_message_for_log, "agent_response": actual_agent_response_or_error}, status=status.HTTP_502_BAD_GATEWAY)
        except requests.exceptions.RequestException as e_req:
            error_message_for_log = f"Network/Request Error: {e_req}"
            actual_agent_response_or_error = error_message_for_log
            agent_answer_text_for_client = error_message_for_log
            return Response({"error": error_message_for_log}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e_general:
            error_message_for_log = f"Unexpected Internal Server Error: {e_general}"
            actual_agent_response_or_error = error_message_for_log
            agent_answer_text_for_client = "Unexpected Internal Server Error"

            print(f"Unexpected Internal Server Error in ChatAPIView: {e_general}")

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
            print(f"CRITICAL ERROR: Could not save AgentInteractionLog: {e_log}")
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
            {"message": "Please use the POST method with a JSON {'question': 'your_question'} to get a response."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED # Method Not Allowed
        )


class UserChatSessionListView(ListAPIView):
    serializer_class = ChatSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return ChatSession.objects.filter(user=user)



class AssetAPIView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [IsAuthenticated] # Esencial si usas request.user

    def get(self, request, pk=None, format=None):
        # (Asumiendo que tu GET sigue filtrando por owner si es necesario)
        if pk:
            # Solo el propietario puede ver el detalle
            asset = get_object_or_404(Asset, pk=pk, owner=request.user)
            serializer = AssetSerializer(asset, context={'request': request})
            return Response(serializer.data)
        else:
            # Listar solo los assets del usuario autenticado
            assets = Asset.objects.filter(owner=request.user)
            serializer = AssetSerializer(assets, many=True, context={'request': request})
            return Response(serializer.data)

    def post(self, request, format=None):
        serializer = AssetSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            # Asigna el owner automáticamente al usuario autenticado
            serializer.save(owner=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk, format=None):
        asset = get_object_or_404(Asset, pk=pk)

        # Comprobación de permisos: solo el propietario puede editar
        if asset.owner != request.user:
            return Response(
                {"detail": "You do not have permission to edit this asset."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = AssetSerializer(asset, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk, format=None):
        asset = get_object_or_404(Asset, pk=pk)

        # Comprobación de permisos
        if asset.owner != request.user:
            return Response(
                {"detail": "You do not have permission to delete this asset."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        asset.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ChatSessionInteractionListView(ListAPIView):
    serializer_class = AgentInteractionLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        session_uuid = self.kwargs.get('session_uuid')
        chat_session = get_object_or_404(ChatSession, session_id=session_uuid, user=user)
        return AgentInteractionLog.objects.filter(chat_session=chat_session)
