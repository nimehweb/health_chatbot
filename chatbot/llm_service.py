import os
from groq import Groq


def get_groq_client():
    api_key = os.getenv('GROQ_API_KEY')
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable not set!")
    return Groq(api_key=api_key)


def extract_symptom_info(conversation_history, user_message):
    """
    Reads the user's latest message and the full conversation history,
    then extracts structured information about symptoms, severity and duration.

    Returns a dictionary like:
    {
        "symptoms": ["headache", "fever"],
        "severity": "moderate",       <- or None if not mentioned
        "duration": "2 days",         <- or None if not mentioned
        "severity_found": True,
        "duration_found": False
    }
    """

    # We format the conversation history into a readable string for the LLM
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
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,  # Low temperature = more consistent, predictable output
            max_tokens=200
        )

        import json
        raw = response.choices[0].message.content.strip()
        return json.loads(raw)

    except Exception as e:
        print(f"Extraction error: {e}")
        # Safe fallback - return empty data so the conversation can continue
        return {
            "symptoms": [],
            "severity": None,
            "duration": None,
            "severity_found": False,
            "duration_found": False
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
        return "I'm sorry to hear you're not feeling well. Could you describe what you're specifically experiencing — for example, do you have any pain, fever, or other symptoms?"

def generate_followup_question(conversation_history, severity_known, duration_known):
    """
    Generates a focused follow-up question based on exactly what is missing.
    Asks in a specific order: symptoms first, then severity, then duration.
    """

    history_text = ""
    for msg in conversation_history:
        role = "User" if msg['type'] == 'user' else "Bot"
        history_text += f"{role}: {msg['content']}\n"

    # Determine exactly what is missing and what to ask
    if not severity_known and not duration_known:
        what_to_ask = "how severe their symptoms are on a scale of mild, moderate, or severe"
    elif not severity_known:
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
        return "Before I give you guidance, is there anything else you are experiencing that I should know about?"

def match_symptoms_to_database(extracted_symptoms, database_symptoms):
    """
    Uses the LLM to intelligently match what the user described
    against our database symptom list.

    For example:
    - "feverish" matches "Fever"
    - "migraine" matches "Headache"
    - "throwing up" matches "Vomiting"

    Returns a list of database symptom names that match.
    """

    if not extracted_symptoms:
        return []

    # Format the database symptoms as a simple list for the LLM
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

        # Sometimes the LLM wraps it in ```json ... ``` so we clean that
        raw = raw.replace("```json", "").replace("```", "").strip()

        matched = json.loads(raw)

        # Make sure we only return things actually in our database
        valid_matches = [s for s in matched if s in database_symptoms]
        return valid_matches

    except Exception as e:
        print(f"Symptom matching error: {e}")
        return []

def generate_guidance(conversation_history, symptoms, severity,
                      duration, urgency, guidance_text,
                      probable_diseases=None):
    """
    Called only when all slots are filled and urgency has been assessed.
    Transforms the clinical guidance into a warm, natural response.
    Now includes probable disease information for richer guidance.
    """

    # Emergency cases get a direct response - no LLM softening needed
    if urgency == 'emergency':
        return (
            f"🚨 This sounds like it needs immediate attention.\n\n"
            f"{guidance_text}\n\n"
            f"Please do not wait. This is not a diagnosis — "
            f"seek emergency care now."
        )

    history_text = ""
    for msg in conversation_history:
        role = "User" if msg['type'] == 'user' else "Bot"
        history_text += f"{role}: {msg['content']}\n"

    # Format probable diseases for the prompt
    diseases_text = ""
    if probable_diseases:
        diseases_text = "\nPROBABLE CONDITIONS (for context only):\n"
        for d in probable_diseases:
            diseases_text += (
                f"- {d['name']} "
                f"({d['match_percentage']}% symptom match): "
                f"{d['description']}\n"
            )

    prompt = f"""You are an empathetic Nigerian healthcare assistant 
giving guidance to a patient.

CONVERSATION SUMMARY:
{history_text}

WHAT WE KNOW:
- Symptoms: {', '.join(symptoms) if symptoms else 'not specified'}
- Severity: {severity or 'not specified'}
- Duration: {duration or 'not specified'}
- Urgency level: {urgency}
{diseases_text}
CLINICAL GUIDANCE TO COMMUNICATE:
{guidance_text}

Rewrite this guidance in a warm, caring, conversational tone 
relevant to the Nigerian healthcare context.

Structure your response as:
1. Brief acknowledgment of what they are going through (1 sentence)
2. If probable conditions exist, mention the most likely one 
   naturally - do not say "85% match", just say 
   "your symptoms are consistent with..." 
3. Clear advice on what they should do (2-3 sentences)
4. One specific thing to watch out for (1 sentence)
5. A reminder that this is not a medical diagnosis and they 
   should see a qualified healthcare professional (1 sentence)

Keep it concise, human and relevant to Nigeria. 
Do not add medical facts not in the guidance above."""

    try:
        client = get_groq_client()
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=400
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"Guidance error: {e}")
        disease_note = ""
        if probable_diseases:
            top = probable_diseases[0]
            disease_note = (
                f" Your symptoms are most consistent "
                f"with {top['name']}."
            )
        return (
            f"Based on what you've described "
            f"({', '.join(symptoms)}),{disease_note} "
            f"here is some guidance:\n\n{guidance_text}\n\n"
            f"Please note this is not a medical diagnosis. "
            f"See a qualified healthcare professional."
        )
