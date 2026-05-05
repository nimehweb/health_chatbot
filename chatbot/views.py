import uuid
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import ChatSession, ChatMessage, Symptom
from .serializers import ChatSessionSerializer, SymptomSerializer
from .services import evaluate_urgency, match_diseases
from .llm_service import (
    extract_symptom_info,
    generate_clarification_request,
    generate_followup_question,
    generate_guidance,
    generate_additional_symptoms_question,
    match_symptoms_to_database,
    advance_interview_phase
)

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
    Main conversation handler.
    Uses slot-filling approach to gather symptoms, severity and duration
    before assessing urgency and providing guidance.
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

    # If this session is already complete, let the user know
    if session.stage == 'complete':
        return Response({
            'session_id': session_id,
            'response': "Your assessment is complete. Please start a new chat if you have new symptoms.",
            'stage': 'complete'
        })

    # Step 1: Save the user's message to the database
    ChatMessage.objects.create(
        session=session,
        message_type='user',
        content=user_message
    )

    # Step 2: Build conversation history from all messages in this session
    # This is what we pass to the LLM so it knows what has already been said
    all_messages = session.messages.all()
    conversation_history = [
        {'type': msg.message_type, 'content': msg.content}
        for msg in all_messages
    ]

    # Step 3: Extract symptom information from the user's message
    extracted = extract_symptom_info(conversation_history, user_message)

    # Step 4: Update the session with whatever we just learned

    # Get all symptom names from our database
    all_db_symptoms = list(Symptom.objects.values_list('name', flat=True))


    # Use LLM to intelligently match extracted symptoms to database
    matched_symptom_names = match_symptoms_to_database(
        extracted_symptoms=extracted.get('symptoms', []),
        database_symptoms=all_db_symptoms
    )

    # Add matched symptoms to the session
    for symptom_name in matched_symptom_names:
        try:
            db_symptom = Symptom.objects.get(name=symptom_name)
            session.reported_symptoms.add(db_symptom)
        except Symptom.DoesNotExist:
            pass

    # for symptom_name in extracted.get('symptoms', []):
    #     # Try to find this symptom in our database (case-insensitive match)
    #     for db_symptom in Symptom.objects.all():
    #         if symptom_name.lower() in db_symptom.name.lower() or db_symptom.name.lower() in symptom_name.lower():
    #             session.reported_symptoms.add(db_symptom)

    # Update severity and duration if we just learned them
    if extracted.get('severity_found'):
        session.severity_known = True

    if extracted.get('duration_found'):
        session.duration_known = True

    session.save()

    # Step 5: Advance the interview phase based on what we now know
    # This moves us through the clinical protocol phases
    advance_interview_phase(session, session.severity_known, session.duration_known)

    # Step 6: Decide what to do next based on what we know
    slots_complete = (
        session.reported_symptoms.exists() and
        session.severity_known and
        session.duration_known and
        session.additional_symptoms_asked
    )

    if not slots_complete:
        # Work out specifically what is still missing
        # so we ask in the right order
        if not session.reported_symptoms.exists():
            # We don't even know what symptoms they have yet
            if not matched_symptom_names:
                # Nothing matched - ask for more specific description
                bot_response = generate_clarification_request(
                conversation_history=conversation_history,
                user_message=user_message
            )
            else:
                # Something was extracted but session hasn't updated yet
                # Ask a focused follow-up using the clinical protocol
                bot_response = generate_followup_question(
                conversation_history=conversation_history,
                extracted_data=extracted,
                current_phase=session.current_interview_phase,
                questions_asked_in_phase=session.questions_asked_in_phase
                )


        elif not session.severity_known or not session.duration_known:
            # We have symptoms but still need severity or duration
            bot_response = generate_followup_question(
                conversation_history=conversation_history,
                extracted_data=extracted,
                current_phase=session.current_interview_phase,
                questions_asked_in_phase=session.questions_asked_in_phase
            )

        elif not session.additional_symptoms_asked:
            # We have everything - but we haven't checked for
            # additional symptoms yet. Ask once before assessing.
            bot_response = generate_additional_symptoms_question(
                conversation_history=conversation_history
            )
            # Mark that we have now asked this question
            session.additional_symptoms_asked = True
            session.save()

        # Save the bot's question
        ChatMessage.objects.create(
            session=session,
            message_type='bot',
            content=bot_response
        )

        return Response({
            'session_id': session_id,
            'response': bot_response,
            'stage': 'gathering',
            'slots': {
                'symptoms_found': session.reported_symptoms.exists(),
                'severity_known': session.severity_known,
                'duration_known': session.duration_known,
                'additional_symptoms_asked': session.additional_symptoms_asked
            }
        })

    else:
        # All slots are filled - now we can assess and give guidance
        session.stage = 'assessing'
        session.save()

        # Run the urgency rule engine
        urgency, guidance_text = evaluate_urgency(session.reported_symptoms.all())

        #Run disease matching
        probable_diseases = match_diseases(session.reported_symptoms.all())

        session.current_urgency = urgency
        session.stage = 'complete'
        session.is_complete = True
        session.save()

        # Generate the final empathetic guidance response
        symptoms_list = [s.name for s in session.reported_symptoms.all()]

        bot_response = generate_guidance(
            conversation_history=conversation_history,
            symptoms=symptoms_list,
            severity=extracted.get('severity'),
            duration=extracted.get('duration'),
            urgency=urgency,
            guidance_text=guidance_text,
            probable_diseases=probable_diseases
        )

        # Save the bot's guidance
        ChatMessage.objects.create(
            session=session,
            message_type='bot',
            content=bot_response,
            extracted_symptoms=symptoms_list
        )

        return Response({
            'session_id': session_id,
            'response': bot_response,
            'stage': 'complete',
            'urgency': urgency,
            'symptoms': symptoms_list,
            'probable_diseases': probable_diseases
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