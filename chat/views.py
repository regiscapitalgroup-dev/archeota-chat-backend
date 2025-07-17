import requests
import os
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework import status, generics
from .serializers import (
    QuestionSerializer, 
    AnswerSerializer, 
    ChatSessionSerializer, 
    AgentInteractionLogSerializer)
from .models import AgentInteractionLog, ChatSession
from rest_framework.permissions import IsAuthenticated
from django.db import IntegrityError
import json


AGENT_API_URL = os.getenv("AGENT_API_URL")
REQUEST_TIMEOUT = 20


class ChatAPIView(generics.GenericAPIView):
    serializer_class = QuestionSerializer
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
                        status=status.HTTP_409_CONFLICT 
                    )

                if not created:
                    chat_session.save() 

            except IntegrityError:
                return Response(
                    {"error": "The provided session ID cannot be used. Please try starting a new session."},
                    status=status.HTTP_409_CONFLICT
                )
        else:
            chat_session = ChatSession.objects.create(user=request.user)
            requested_session_id_str = chat_session.session_id

        if chat_session.interactions.count() == 0 and not chat_session.title:
            title_text = user_question[:60] + '...' if len(user_question) > 60 else user_question
            chat_session.title = title_text
            chat_session.save(update_fields=['title', 'last_activity'])


        agent_response_text_for_client = "Error: No actionable response was received from the agent."
        actual_agent_response_or_error = None
        summary = None
        additional_questions = None
        extra_questions = None
        interaction_successful_flag = False
        error_message_for_log = None
        category = None
        attributes = None
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
                    r = api_data['output']

                    if r.startswith("```json"):
                        json_string = r.strip("```json\n").strip("```")
                        json_data = json.loads(json_string)  
                    else:
                        json_data = json.loads(r)
                    
                    if 'general_response' in json_data:
                        actual_agent_response_or_error = json_data['general_response']
                    if 'summary' in json_data:
                        summary = json_data['summary']
                        s = "".join(summary)
                    if 'additional_questions' in json_data:
                        additional_questions = json_data['additional_questions']
                    if 'extra_questions' in json_data:
                        extra_questions = json_data['extra_questions']
                    if 'category' in json_data:
                        category = json_data['category']
                    if 'attributes' in json_data:
                        tmp = json_data['attributes']
                        dict_attributes = dict(item.split('|') for item in tmp)

                    if not actual_agent_response_or_error:
                        actual_agent_response_or_error = r

                else: 
                    actual_agent_response_or_error = response.text
                    additional_questions = None

                if actual_agent_response_or_error is not None:
                    interaction_successful_flag = True
                    agent_answer_text_for_client = actual_agent_response_or_error 

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
                category=category,
                attributes=dict_attributes,
                is_successful=interaction_successful_flag,
                error_message=error_message_for_log 
            )
        except Exception as e_log:
            print(f"CRITICAL ERROR: Could not save AgentInteractionLog: {e_log}")
        
        if not interaction_successful_flag and error_message_for_log:
             return Response({"error": agent_answer_text_for_client, "detail": error_message_for_log}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if requested_session_id_str:
            response_data = {
                'general_response': actual_agent_response_or_error,
                'summary': s,
                'additional_questions': additional_questions,
                'extra_questions': extra_questions,
                'chat_session_id': requested_session_id_str,
                'category': category,
                'attributes': dict_attributes
            }
        else:
            response_data = {
                'general_response': actual_agent_response_or_error,
                'summary': s,
                'additional_questions': additional_questions,
                'extra_questions': extra_questions,
                'chat_session_id': chat_session.session_id,
                'category': category,
                'attributes': dict_attributes
            }
            
        answer_serializer = AnswerSerializer(response_data)      
        return Response(answer_serializer.data, status=status.HTTP_200_OK)

    def get(self, request, *args, **kwargs):
        return Response(
            {"message": "Please use the POST method with a JSON {'question': 'your_question'} to get a response."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED 
        )


class UserChatSessionListView(ListAPIView):
    serializer_class = ChatSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return ChatSession.objects.filter(user=user)


class ChatSessionInteractionListView(ListAPIView):
    serializer_class = AgentInteractionLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        session_uuid = self.kwargs.get('session_uuid')
        chat_session = get_object_or_404(ChatSession, session_id=session_uuid, user=user)
        return AgentInteractionLog.objects.filter(chat_session=chat_session)
    