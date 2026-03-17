import os
from groq import Groq

# Initialize client (will use environment variable or direct key)
def get_groq_client():
    """Initialize Groq client with API key"""
    api_key = os.getenv('GROQ_API_KEY')
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable not set!")
    return Groq(api_key=api_key)

def generate_natural_response(symptoms, urgency, guidance, user_message):
    """
    Use LLM to transform medical guidance into natural, empathetic response
    
    Args:
        symptoms: List of detected symptom names
        urgency: String (emergency, urgent, moderate, self_care)
        guidance: Original rule-based guidance text
        user_message: What the user originally said
    
    Returns:
        Natural language response string
    """
    
    # Don't use LLM for emergencies - use direct, clear instructions
    if urgency == 'emergency':
        return f"🚨 URGENT MEDICAL ATTENTION REQUIRED\n\nBased on your symptoms ({', '.join(symptoms)}), you may be experiencing a serious condition.\n\n{guidance}\n\nThis is not a diagnosis. Please seek immediate professional care."
    
    # Build prompt for LLM
    prompt = f"""You are a helpful, empathetic healthcare assistant. A user has described their symptoms, and a medical rule engine has analyzed them.

USER'S MESSAGE: "{user_message}"

DETECTED SYMPTOMS: {', '.join(symptoms) if symptoms else 'None specifically detected'}

URGENCY LEVEL: {urgency}

MEDICAL GUIDANCE TO CONVEY: {guidance}

Your task: Rewrite this guidance in a warm, natural, conversational tone. Be empathetic but professional. Include:
1. Acknowledgment of their symptoms
2. Clear explanation of what they should do
3. Reassurance (but not false reassurance)
4. A disclaimer that this is not medical advice

Keep it concise (2-3 short paragraphs). Do NOT add new medical facts not in the guidance."""

    try:
        client = get_groq_client()
        
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",  # Fast, cheap, good quality
            messages=[
                {"role": "system", "content": "You are a helpful healthcare assistant. Provide empathetic, clear guidance based on medical rules."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,  # Balance creativity and consistency
            max_tokens=300    # Keep responses concise
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        # Fallback to original guidance if LLM fails
        print(f"LLM Error: {e}")
        return f"Based on your symptoms ({', '.join(symptoms)}): {guidance}\n\nNote: This is preliminary guidance, not a medical diagnosis."

def generate_followup_question(asked_symptoms, user_message):
    """
    Generate a natural follow-up question to gather more symptom info
    """
    remaining_common = ['Fever', 'Headache', 'Cough', 'Nausea', 'Fatigue', 'Body Pain']
    to_ask = [s for s in remaining_common if s not in asked_symptoms][:2]
    
    if not to_ask:
        return "Are there any other symptoms you'd like to mention?"
    
    prompt = f"""The user said: "{user_message}"
We've already noted these symptoms: {', '.join(asked_symptoms) if asked_symptoms else 'None yet'}.
Ask naturally if they also have: {', '.join(to_ask)}.
Keep it to one short, conversational question."""
    
    try:
        client = get_groq_client()
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=100
        )
        return response.choices[0].message.content
    except:
        return f"Do you also have {', '.join(to_ask)}?"