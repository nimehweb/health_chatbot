from .models import UrgencyRule

def evaluate_urgency(reported_symptoms):
    """
    Takes a list of Symptom objects
    Returns the matching urgency level + guidance text
    """

    # Get all rules ordered by priority (highest first)
    rules = UrgencyRule.objects.all()

    for rule in rules:
        rule_symptoms = rule.symptoms.all()

        if rule.requires_all:
            # Check if ALL rule symptoms are in reported symptoms
            if all(symptom in reported_symptoms for symptom in rule_symptoms):
                return rule.urgency_level, rule.guidance_text
        else:
            # Check if ANY symptom matches
            if any(symptom in reported_symptoms for symptom in rule_symptoms):
                return rule.urgency_level, rule.guidance_text

    # Default fallback
    return "self_care", "Monitor symptoms and rest. Seek medical advice if condition worsens."