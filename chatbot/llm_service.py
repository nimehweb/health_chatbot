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
    Covers Groq client errors and general network failures.
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
    Reads the user's latest message and the full conversation history,
    then extracts structured information about symptoms, severity and duration.

    Returns a dictionary like:
    {
        "symptoms": ["headache", "fever"],
        "severity": "moderate",
        "duration": "2 days",
        "severity_found": True,
        "duration_found": False,
        "connection_error": False
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
    Asks them to describe what they are specifically experiencing.
    """
    history_text = ""
    for msg in conversation_history:
        role = "User" if msg['type'] == 'user' else "Bot"
        history_text += f"{role}: {msg['content']}\n"

    prompt = f"""You are a caring healthcare assistant.

CONVERSATION SO FAR:
{history_text}

The patient said something vague like "I feel unwell" or "I am not feeling well"
without describing specific symptoms.

Ask them ONE warm, focused question to find out exactly what they 
are physically experiencing. 

Examples of what you want to know:
- Are they having pain somewhere?
- Do they have a fever, cough, headache?
- What part of their body is affected?

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
            "for example, do you have any pain, fever, or other symptoms?"
        )


def generate_followup_question(conversation_history, severity_known,
                               duration_known):
    """
    Generates a focused follow-up question based on exactly what is missing.
    """
    history_text = ""
    for msg in conversation_history:
        role = "User" if msg['type'] == 'user' else "Bot"
        history_text += f"{role}: {msg['content']}\n"

    if not severity_known:
        what_to_ask = "how severe their symptoms are on a scale of mild, moderate, or severe"
    elif not duration_known:
        what_to_ask = "how long they have been experiencing these symptoms"
    else:
        what_to_ask = "if they have any other symptoms"

    prompt = f"""You are a focused healthcare assistant collecting specific 
information from a patient before assessing their condition.

CONVERSATION SO FAR:
{history_text}

Your ONLY job right now is to ask the patient: {what_to_ask}

Rules:
- Ask ONLY about {what_to_ask} - nothing else
- Keep it to ONE short sentence
- Sound caring and natural, like a nurse
- Do NOT ask about anything already covered in the conversation
- Do NOT ask multiple questions at once
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
            return "Could you describe how severe your symptoms feel — mild, moderate, or quite severe?"
        return "How long have you been experiencing these symptoms?"


def generate_additional_symptoms_question(conversation_history):
    """
    Asked exactly once before final assessment.
    Checks if the user has any other symptoms we should know about.
    """
    history_text = ""
    for msg in conversation_history:
        role = "User" if msg['type'] == 'user' else "Bot"
        history_text += f"{role}: {msg['content']}\n"

    prompt = f"""You are a caring healthcare assistant.

CONVERSATION SO FAR:
{history_text}

You have gathered the main symptoms, severity and duration from the patient.
Now ask them ONE short, natural question to check if they have any other 
symptoms you should know about before giving guidance.

- Keep it to one sentence
- Sound warm and caring, not clinical
- Do not list specific symptoms to choose from
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
            "Before I give you guidance, is there anything else "
            "you are experiencing that I should know about?"
        )


def match_symptoms_to_database(extracted_symptoms, database_symptoms):
    """
    Uses the LLM to intelligently match what the user described
    against our database symptom list.

    Falls back to simple string matching on connection errors so the
    conversation can still continue without the LLM.
    """
    if not extracted_symptoms:
        return []

    db_symptoms_text = ", ".join(database_symptoms)

    prompt = f"""You are a medical terminology matcher.

A patient described these symptoms: {', '.join(extracted_symptoms)}

From this list of standard medical terms, identify which ones 
match what the patient described (including synonyms, informal 
language, and related terms):

STANDARD TERMS LIST:
{db_symptoms_text}

Rules:
- Only return terms from the list above, nothing else
- Match based on medical meaning, not just exact words
- "feverish" matches "Fever", "migraine" matches "Headache" etc
- If nothing matches, return an empty list
- Respond ONLY with a JSON array of matching terms like:
  ["Fever", "Headache"]
- No explanation, just the JSON array"""

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
        valid_matches = [s for s in matched if s in database_symptoms]
        return valid_matches

    except Exception as e:
        print(f"Symptom matching error: {e}")
        # On connection error fall back to simple string matching
        # so symptoms still get recorded even without the LLM
        fallback = []
        for extracted in extracted_symptoms:
            for db_sym in database_symptoms:
                if extracted.lower() in db_sym.lower() or \
                   db_sym.lower() in extracted.lower():
                    fallback.append(db_sym)
        return list(set(fallback))


def generate_guidance(conversation_history, symptoms, severity,
                      duration, urgency, guidance_text,
                      probable_diseases=None):
    """
    Called only when all slots are filled and urgency has been assessed.
    Transforms the clinical guidance into a warm, natural response.

    NOTE: probable_diseases is accepted but intentionally NOT used in
    the response. This is a symptoms guidance system, not a diagnosis
    tool. Mentioning disease names confuses users and causes unnecessary
    fear when the matching may be wrong.
    """

    # Emergency cases get a direct response — no softening needed
    if urgency == 'emergency':
        return (
            "🚨 This sounds like it needs immediate attention.\n\n"
            f"{guidance_text}\n\n"
            "Please do not wait. This is not a diagnosis — "
            "seek emergency care now."
        )

    # ── RAG: retrieve relevant knowledge base articles ────────────
    rag_context = ""
    if symptoms:
        try:
            from chatbot.rag_service import retrieve_context
            symptom_query = ", ".join(symptoms)
            rag_context = retrieve_context(symptom_query, n_results=2)
        except Exception as e:
            print(f"[RAG] Could not retrieve context: {e}")
            rag_context = ""

    history_text = ""
    for msg in conversation_history:
        role = "User" if msg['type'] == 'user' else "Bot"
        history_text += f"{role}: {msg['content']}\n"

    rag_section = ""
    if rag_context:
        rag_section = f"""
SYMPTOM KNOWLEDGE BASE (use this to enrich your guidance):
{rag_context}
"""

    prompt = f"""You are an empathetic Nigerian healthcare assistant 
giving guidance to a patient about their symptoms.

CONVERSATION SUMMARY:
{history_text}

WHAT WE KNOW:
- Symptoms: {', '.join(symptoms) if symptoms else 'not specified'}
- Severity: {severity or 'not specified'}
- Duration: {duration or 'not specified'}
- Urgency level: {urgency}
{rag_section}
CLINICAL GUIDANCE TO COMMUNICATE:
{guidance_text}

Rewrite this guidance in a warm, caring, conversational tone 
relevant to the Nigerian healthcare context.

VERY IMPORTANT RULES:
- Do NOT mention any disease names or medical conditions
- Do NOT say "your symptoms are consistent with [anything]"
- Do NOT attempt to diagnose — focus only on what to DO
- Where the knowledge base has relevant self-care tips or warning
  signs, weave ONE or TWO points in naturally

Structure your response as:
1. Brief acknowledgment of what they are going through (1 sentence)
2. Clear advice on what they should do next (2-3 sentences)
3. One specific warning sign to watch out for (1 sentence)
4. A reminder that this is not a medical diagnosis and they 
   should see a qualified healthcare professional (1 sentence)

Keep it concise, warm and relevant to Nigeria."""

    try:
        client = get_groq_client()
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=450
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"Guidance error: {e}")
        if _is_connection_error(e):
            return CONNECTION_ERROR_MESSAGE
        return (
            f"Based on your symptoms ({', '.join(symptoms)}), "
            f"here is some guidance:\n\n{guidance_text}\n\n"
            "Please note this is not a medical diagnosis. "
            "See a qualified healthcare professional."
        )