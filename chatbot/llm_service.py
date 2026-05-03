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


def generate_followup_question(conversation_history, severity_known,
                               duration_known):
    """
    Generates a focused follow-up question for whatever slot is missing.
    """
    history_text = ""
    for msg in conversation_history:
        role = "User" if msg['type'] == 'user' else "Bot"
        history_text += f"{role}: {msg['content']}\n"

    if not severity_known:
        what_to_ask = "how severe their symptoms are — mild moderate or severe"
    elif not duration_known:
        what_to_ask = "how long they have been experiencing these symptoms"
    else:
        what_to_ask = "if they have any other symptoms"

    prompt = f"""You are a focused healthcare assistant collecting information
from a patient before assessing their condition.

CONVERSATION SO FAR:
{history_text}

Your ONLY job right now is to ask the patient: {what_to_ask}

Rules:
- Ask ONLY about {what_to_ask} — nothing else
- ONE short sentence
- Sound caring and natural like a nurse
- Do NOT ask about anything already covered in the conversation
- Do NOT say hello or introduce yourself again"""

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
        print(f"Followup error: {e}")
        if _is_connection_error(e):
            return CONNECTION_ERROR_MESSAGE
        if not severity_known:
            return "Could you describe how severe your symptoms feel — mild moderate or quite severe?"
        return "How long have you been experiencing these symptoms?"


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