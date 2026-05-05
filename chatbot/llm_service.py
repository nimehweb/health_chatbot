import os
from groq import Groq


def get_groq_client():
    api_key = os.getenv('GROQ_API_KEY')
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable not set!")
    return Groq(api_key=api_key)


def _is_connection_error(e):
    """
    Returns True if the exception is a network/connection error.
    """
    error_str = str(e).lower()
    connection_keywords = [
        'connection error', 'connection timeout', 'getaddrinfo',
        'network', 'timeout', 'remotedisconnected', 'connectionreset',
        'connexion', 'unreachable', 'socket', 'ssl'
    ]
    return any(keyword in error_str for keyword in connection_keywords)


CONNECTION_ERROR_MESSAGE = (
    "⚠️ I'm having trouble connecting right now. "
    "Please check your internet connection and try again."
)


def extract_symptom_info(conversation_history, user_message):
    """
    Extracts symptoms, severity and duration from the user's message.

    Returns:
    {
        "symptoms": ["headache", "fever"],
        "severity": "moderate" or None,
        "duration": "2 days" or None,
        "severity_found": True/False,
        "duration_found": True/False,
        "connection_error": True/False
    }
    """
    history_text = ""
    for msg in conversation_history:
        role = "User" if msg['type'] == 'user' else "Bot"
        history_text += f"{role}: {msg['content']}\n"

    prompt = f"""You are a medical information extractor. 
Read this conversation and extract health information from it.

CONVERSATION SO FAR:
{history_text}
LATEST USER MESSAGE: "{user_message}"

Extract the following and respond ONLY in valid JSON, nothing else:
{{
    "symptoms": ["list", "of", "symptoms", "mentioned"],
    "severity": "mild or moderate or severe or null if not mentioned",
    "duration": "how long they have had symptoms or null if not mentioned",
    "severity_found": true or false,
    "duration_found": true or false
}}

Rules:
- symptoms should be plain words like "headache", "fever", "cough"
- severity_found is ONLY true if the user used words like:
  mild, moderate, severe, terrible, slight, bad, worse, unbearable,
  a little, very, extremely, quite, really, not too bad, manageable
- severity_found is FALSE if the user only named their symptoms
  without describing how bad they are
- duration_found is ONLY true if the user mentioned a time period like:
  hours, days, weeks, since yesterday, since this morning, for 2 days etc
- If nothing relevant was found, return empty lists and nulls
- Return ONLY the JSON object, no extra text"""

    try:
        client = get_groq_client()
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=200
        )
        import json
        raw = response.choices[0].message.content.strip()
        return json.loads(raw)

    except Exception as e:
        print(f"Extraction error: {e}")
        return {
            "symptoms": [],
            "severity": None,
            "duration": None,
            "severity_found": False,
            "duration_found": False,
            "connection_error": _is_connection_error(e)
        }


def generate_clarification_request(conversation_history, user_message):
    """
    Called when the user's message is too vague to extract any symptoms.
    """
    history_text = ""
    for msg in conversation_history:
        role = "User" if msg['type'] == 'user' else "Bot"
        history_text += f"{role}: {msg['content']}\n"

    prompt = f"""You are a caring healthcare assistant.

CONVERSATION SO FAR:
{history_text}

The patient said something vague without describing specific symptoms.
Ask them ONE warm focused question to find out exactly what they 
are physically experiencing — for example do they have pain fever
cough or something else?

Rules:
- ONE question only
- Warm and caring tone
- Do not list all possible symptoms for them to choose from
- Do not say hello again"""

    try:
        client = get_groq_client()
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=80
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"Clarification error: {e}")
        if _is_connection_error(e):
            return CONNECTION_ERROR_MESSAGE
        return (
            "I'm sorry to hear you're not feeling well. "
            "Could you describe what you're specifically experiencing — "
            "for example do you have any pain fever or other symptoms?"
        )


def _get_fallback_question(phase, known_info):
    """
    Fallback questions when LLM fails — still clinically sensible.
    Used when the API is unavailable or times out.
    """
    fallbacks = {
        'intro': "What brought you in today? What symptoms are you experiencing?",
        'core_characterization': (
            "How would you describe the pain or discomfort — "
            "is it sharp, dull, burning, or something else?"
        ),
        'associated_symptoms': (
            "Are you experiencing any other symptoms "
            "like fever, nausea, shortness of breath, or chills?"
        ),
        'history_meds': (
            "Do you have any chronic medical conditions "
            "or take any regular medications?"
        ),
        'complete': "Is there anything else you'd like to tell me?",
    }
    return fallbacks.get(phase, "Is there anything else you'd like to tell me?")


def generate_followup_question(conversation_history, extracted_data,
                               current_phase, questions_asked_in_phase):
    """
    Uses a clinical interview protocol to ask the NEXT BEST QUESTION
    based on what we've learned so far — not just checking boolean slots.
    
    This implements dynamic interviewing:
    - Phase 1 (intro): Core symptom characterization (onset, duration, quality, severity, location)
    - Phase 2 (core_characterization): Modifying factors and associated symptoms
    - Phase 3 (associated_symptoms): Past medical history and medications
    - Phase 4 (history_meds): Assessment complete
    
    Args:
        conversation_history: List of dicts with 'type' and 'content'
        extracted_data: Dict with 'symptoms', 'severity', 'duration', etc.
        current_phase: Current interview phase (string)
        questions_asked_in_phase: Number of questions asked in this phase (int)
    """
    history_text = "\n".join([
        f"{msg['type'].upper()}: {msg['content']}" 
        for msg in conversation_history
    ])
    
    # Compile what we already know
    known_info = {
        "symptoms": extracted_data.get("symptoms", []),
        "severity": extracted_data.get("severity"),
        "duration": extracted_data.get("duration"),
        "associated_symptoms": extracted_data.get("associated_symptoms", []),
        "past_medical_history": extracted_data.get("past_medical_history"),
        "medications": extracted_data.get("medications"),
    }

    import json
    
    prompt = f"""You are an experienced physician conducting a systematic medical interview.
Your goal is to gather just enough information to provide accurate GUIDANCE and TRIAGE 
(NOT diagnosis — never attempt to diagnose).

CLINICAL INTERVIEW PROTOCOL:

Phase 1 (Intro): Establish main complaint
- Onset: When did this start?
- Duration: How long has it been?
- Quality: What does it feel like? (sharp, dull, throbbing, burning, etc.)
- Severity: On a scale of 1-10? Or mild/moderate/severe?
- Location: Where exactly is it?

Phase 2 (Core Characterization): Associated symptoms and modifying factors
- What other symptoms accompany the main complaint?
- What makes it better? What makes it worse?
- Any fever, chills, sweating, nausea, vomiting?
- Has this happened before?

Phase 3 (Associated Symptoms): Medical and medication history
- Relevant past medical conditions?
- Current medications or supplements?
- Allergies?
- Recent travel or exposures?

Phase 4 (History/Meds): Complete and prepare for guidance
- Any other important information?

---

CONVERSATION SO FAR:
{history_text}

WHAT WE KNOW SO FAR:
{json.dumps(known_info, indent=2)}

CURRENT INTERVIEW PHASE: {current_phase} (Question #{questions_asked_in_phase + 1})

YOUR TASK:
Ask ONE specific, clinical follow-up question that will provide the MOST VALUABLE 
next piece of information. This question should:
- NOT repeat anything already discussed in the conversation
- Be specific to THIS patient's presentation (not generic)
- Be under 18 words
- Sound natural and caring, like a real healthcare provider
- Help narrow down appropriate guidance and triage level
- Push the interview forward through the phases

Return ONLY the question as plain text, no explanation or quotation marks."""

    try:
        client = get_groq_client()
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            max_tokens=60
        )
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        print(f"Followup error: {e}")
        if _is_connection_error(e):
            return CONNECTION_ERROR_MESSAGE
        return _get_fallback_question(current_phase, known_info)


def generate_additional_symptoms_question(conversation_history):
    """
    Asked exactly once before final assessment to check for anything missed.
    """
    history_text = ""
    for msg in conversation_history:
        role = "User" if msg['type'] == 'user' else "Bot"
        history_text += f"{role}: {msg['content']}\n"

    prompt = f"""You are a caring healthcare assistant.

CONVERSATION SO FAR:
{history_text}

You have gathered the main symptoms severity and duration.
Ask ONE short warm question to check if the patient has any other
symptoms you should know about before giving guidance.

- One sentence only
- Warm and caring not clinical
- Do not list specific symptoms
- Do not repeat anything already asked"""

    try:
        client = get_groq_client()
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=80
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"Additional symptoms question error: {e}")
        if _is_connection_error(e):
            return CONNECTION_ERROR_MESSAGE
        return (
            "Before I give you guidance is there anything else "
            "you are experiencing that I should know about?"
        )


def match_symptoms_to_database(extracted_symptoms, database_symptoms):
    """
    Uses the LLM to match what the user described to your symptom database.
    Falls back to simple string matching on connection errors.
    """
    if not extracted_symptoms:
        return []

    db_symptoms_text = ", ".join(database_symptoms)

    prompt = f"""You are a medical terminology matcher.

A patient described these symptoms: {', '.join(extracted_symptoms)}

From this list of standard medical terms identify which ones 
match what the patient described including synonyms and informal language:

STANDARD TERMS LIST:
{db_symptoms_text}

Rules:
- Only return terms from the list above
- Match based on medical meaning not just exact words
- "feverish" matches "Fever" — "migraine" matches "Headache"
- If nothing matches return an empty list
- Respond ONLY with a JSON array like: ["Fever", "Headache"]
- No explanation just the JSON array"""

    try:
        client = get_groq_client()
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=100
        )
        import json
        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        matched = json.loads(raw)
        return [s for s in matched if s in database_symptoms]

    except Exception as e:
        print(f"Symptom matching error: {e}")
        # Simple string fallback so symptoms still get recorded
        fallback = []
        for extracted in extracted_symptoms:
            for db_sym in database_symptoms:
                if extracted.lower() in db_sym.lower() or \
                   db_sym.lower() in extracted.lower():
                    fallback.append(db_sym)
        return list(set(fallback))


def _retrieve_selfcare_context(symptoms):
    """
    Retrieves self-care content from the knowledge base using RAG.
    Returns an empty string if RAG is unavailable or fails — the
    guidance will still work without it using the urgency rule alone.
    """
    if not symptoms:
        return ""
    try:
        from chatbot.rag_service import retrieve_context
        query = ", ".join(symptoms)
        return retrieve_context(query, n_results=2)
    except Exception as e:
        print(f"[RAG] retrieval error: {e}")
        return ""


def generate_guidance(conversation_history, symptoms, severity,
                      duration, urgency, guidance_text,
                      probable_diseases=None):
    """
    Generates the final guidance response for the user.

    Two clearly separated sources of information are used:

    SOURCE 1 — Urgency rule guidance_text
        Answers: how serious is this, what action should they take,
        how soon should they seek care. This is the authoritative
        instruction. The LLM must follow it exactly.

    SOURCE 2 — RAG knowledge base article (self-care focused)
        Answers: what can the patient do at home while waiting,
        and what warning signs should they watch for. This is
        supplementary — it enriches the response but never
        overrides Source 1.

    This separation prevents the two sources from contradicting
    each other because they answer different questions.
    """

    # Emergency: skip the LLM entirely — direct and clear is safer
    if urgency == 'emergency':
        return (
            "🚨 This sounds like it needs immediate attention.\n\n"
            f"{guidance_text}\n\n"
            "Please do not wait. This is not a diagnosis — "
            "seek emergency care now."
        )

    # Retrieve self-care context from knowledge base
    selfcare_context = _retrieve_selfcare_context(symptoms)

    # Build conversation summary for context
    history_text = ""
    for msg in conversation_history:
        role = "User" if msg['type'] == 'user' else "Bot"
        history_text += f"{role}: {msg['content']}\n"

    # Only include the self-care section if RAG returned something useful
    selfcare_section = ""
    if selfcare_context:
        selfcare_section = f"""
--- SELF-CARE KNOWLEDGE BASE ---
The following is factual self-care information for these symptoms.
Use ONLY the points under "SELF-CARE WHILE WAITING" and
"WARNING SIGNS" from this content — ignore everything else:

{selfcare_context}
--- END SELF-CARE KNOWLEDGE BASE ---
"""

    prompt = f"""You are an empathetic Nigerian healthcare assistant
giving structured guidance to a patient about their symptoms.

PATIENT INFORMATION:
- Symptoms reported: {', '.join(symptoms) if symptoms else 'not specified'}
- Severity: {severity or 'not specified'}
- Duration: {duration or 'not specified'}
- Urgency level: {urgency}

CONVERSATION HISTORY:
{history_text}
{selfcare_section}
--- CLINICAL GUIDANCE (follow this exactly) ---
{guidance_text}
--- END CLINICAL GUIDANCE ---

Your task is to write a clear warm response using BOTH sources above.
Structure your response in this exact order:

1. ACKNOWLEDGEMENT (1 sentence)
   Acknowledge how the patient is feeling based on their symptoms
   and severity. Be warm and human.

2. WHAT TO DO NEXT (2-3 sentences)
   Rewrite the CLINICAL GUIDANCE above in natural conversational
   language. Follow it exactly — do not change the urgency or
   timing. Do not add or remove any action it recommends.

3. SELF-CARE TIPS (1-2 sentences, only if self-care context exists)
   Add ONE or TWO practical self-care tips from the knowledge base
   that the patient can do RIGHT NOW while waiting or recovering.
   These must come from the SELF-CARE WHILE WAITING section only.
   Skip this section entirely if no self-care context was provided.

4. WARNING SIGN (1 sentence)
   State ONE clear warning sign from either the clinical guidance
   or the knowledge base WARNING SIGNS section that should prompt
   the patient to seek more urgent care.

5. DISCLAIMER (1 sentence)
   Remind the patient that this is not a medical diagnosis and they
   should see a qualified healthcare professional.

STRICT RULES:
- Do NOT mention any disease names or medical conditions
- Do NOT contradict the clinical guidance — it always takes priority
- Do NOT invent self-care tips not present in the knowledge base
- Do NOT copy text word for word — paraphrase naturally
- Keep the whole response under 150 words
- Write in warm conversational English suited to Nigeria"""

    try:
        client = get_groq_client()
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=400
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"Guidance error: {e}")
        if _is_connection_error(e):
            return CONNECTION_ERROR_MESSAGE
        # If LLM fails entirely, return the raw guidance text directly
        # It is already well-written enough to show the user
        return (
            f"{guidance_text}\n\n"
            "Please note this is not a medical diagnosis. "
            "See a qualified healthcare professional."
        )


def advance_interview_phase(session, severity_known, duration_known):
    """
    Advances the interview to the next phase when the current phase
    has gathered enough information.
    
    Phases advance as:
    - intro → core_characterization (when severity AND duration known)
    - core_characterization → associated_symptoms (after 2-3 questions)
    - associated_symptoms → history_meds (after 2-3 questions)
    - history_meds → complete (after asking about medical history)
    
    Args:
        session: ChatSession instance
        severity_known: Boolean
        duration_known: Boolean
    """
    current = session.current_interview_phase
    
    # Intro phase: move forward once we have severity and duration
    if current == 'intro':
        if severity_known and duration_known:
            session.current_interview_phase = 'core_characterization'
            session.questions_asked_in_phase = 0
    
    # Core characterization: move forward after asking 2-3 questions
    elif current == 'core_characterization':
        if session.questions_asked_in_phase >= 2:
            session.current_interview_phase = 'associated_symptoms'
            session.questions_asked_in_phase = 0
    
    # Associated symptoms: move forward after asking 2-3 questions
    elif current == 'associated_symptoms':
        if session.questions_asked_in_phase >= 2:
            session.current_interview_phase = 'history_meds'
            session.questions_asked_in_phase = 0
    
    # History/Meds: move to complete after asking questions
    elif current == 'history_meds':
        if session.questions_asked_in_phase >= 1:
            session.current_interview_phase = 'complete'
            session.questions_asked_in_phase = 0
    
    # Increment the question counter for this phase
    session.questions_asked_in_phase += 1
    session.save()