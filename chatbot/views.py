import uuid
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import ChatSession, ChatMessage, Symptom
from .serializers import ChatSessionSerializer, SymptomSerializer
from .services import evaluate_urgency
from .llm_service import generate_natural_response, generate_followup_question 


@api_view(['POST'])
def start_chat(request):
    """
    Start a new chat session.
    """
    session_id = str(uuid.uuid4())[:8]

    session = ChatSession.objects.create(session_id=session_id)

    welcome_msg = ChatMessage.objects.create(
        session=session,
        message_type='bot',
        content="Hello! I'm your healthcare assistant. Please describe your symptoms."
    )

    return Response({
        'session_id': session_id,
        'message': welcome_msg.content
    })


@api_view(['POST'])
def send_message(request):
    """
    Send a message to chatbot with LLM-enhanced responses.
    """
    session_id = request.data.get('session_id')
    user_message = request.data.get('message', '').strip()

    if not session_id or not user_message:
        return Response(
            {'error': 'session_id and message are required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        session = ChatSession.objects.get(session_id=session_id)
    except ChatSession.DoesNotExist:
        return Response(
            {'error': 'Session not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Save user message
    ChatMessage.objects.create(
        session=session,
        message_type='user',
        content=user_message
    )

    # Match symptoms from database
    found_symptoms = []
    user_message_lower = user_message.lower()

    for symptom in Symptom.objects.all():
        if symptom.name.lower() in user_message_lower:
            found_symptoms.append(symptom)
            session.reported_symptoms.add(symptom)

    # Evaluate urgency using rule engine
    urgency, guidance = evaluate_urgency(session.reported_symptoms.all())
    session.current_urgency = urgency
    session.save()

    # 🔥 NEW: Use LLM to generate natural response
    if found_symptoms or urgency == 'emergency':
        # Transform rule-based guidance into natural language
        response_text = generate_natural_response(
            symptoms=[s.name for s in found_symptoms],
            urgency=urgency,
            guidance=guidance,
            user_message=user_message
        )
    else:
        # No symptoms found - ask for clarification
        response_text = generate_followup_question(
            asked_symptoms=[],
            user_message=user_message
        )

    # Save bot response
    ChatMessage.objects.create(
        session=session,
        message_type='bot',
        content=response_text,
        extracted_symptoms=[s.name for s in found_symptoms]
    )

    return Response({
        'session_id': session_id,
        'response': response_text,
        'found_symptoms': [s.name for s in found_symptoms],
        'current_urgency': urgency
    })


@api_view(['GET'])
def get_chat_history(request, session_id):
    try:
        session = ChatSession.objects.get(session_id=session_id)
        serializer = ChatSessionSerializer(session)
        return Response(serializer.data)
    except ChatSession.DoesNotExist:
        return Response(
            {'error': 'Session not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
def list_symptoms(request):
    symptoms = Symptom.objects.all()
    serializer = SymptomSerializer(symptoms, many=True)
    return Response(serializer.data)