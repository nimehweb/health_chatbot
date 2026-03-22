from .models import UrgencyRule, Disease

def evaluate_urgency(reported_symptoms):
    """
    Takes a queryset of Symptom objects.
    Returns the matching urgency level + guidance text.
    
    Checks rules in priority order (highest first).
    For each rule:
    - requires_all=True: ALL rule symptoms must be in reported symptoms
    - requires_all=False: ANY one rule symptom triggers it
    """
    
    # Convert queryset to a set of IDs for fast lookup
    # This avoids repeated database queries inside the loop
    reported_symptom_ids = set(
        reported_symptoms.values_list('id', flat=True)
    )

    if not reported_symptom_ids:
        return "self_care", "Please monitor your symptoms and rest. Seek medical advice if your condition worsens."

    # Get all rules ordered by priority (highest first)
    # prefetch_related loads all rule symptoms in one query
    rules = UrgencyRule.objects.prefetch_related('symptoms').all()

    for rule in rules:
        rule_symptom_ids = set(
            rule.symptoms.values_list('id', flat=True)
        )

        if not rule_symptom_ids:
            continue

        if rule.requires_all:
            # ALL rule symptoms must be present
            if rule_symptom_ids.issubset(reported_symptom_ids):
                return rule.urgency_level, rule.guidance_text
        else:
            # ANY one rule symptom is enough
            if rule_symptom_ids & reported_symptom_ids:
                return rule.urgency_level, rule.guidance_text

    # No rule matched - default to self care
    return "self_care", "Monitor your symptoms and rest. Seek medical advice if your condition worsens."

def match_diseases(reported_symptoms):
    """
    Matches reported symptoms against known diseases
    and returns the top 3 most probable conditions.

    Uses symptom overlap scoring:
    - Score = number of matching symptoms / total disease symptoms
    - Only considers diseases with at least 40% symptom overlap
    - Returns results sorted by score (highest first)

    Returns a list of dicts like:
    [
        {
            'name': 'Malaria',
            'description': 'A mosquito-borne...',
            'match_percentage': 85,
            'urgency_level': 'urgent',
            'precautions': ['drink fluids', 'see doctor']
        },
        ...
    ]
    """

    # Convert reported symptoms to a set of IDs for fast comparison
    reported_symptom_ids = set(
        reported_symptoms.values_list('id', flat=True)
    )

    if not reported_symptom_ids:
        return []

    # Load all diseases with their symptoms in one query
    diseases = Disease.objects.prefetch_related('symptoms').all()

    matches = []

    for disease in diseases:
        disease_symptom_ids = set(
            disease.symptoms.values_list('id', flat=True)
        )

        if not disease_symptom_ids:
            continue

        # Count how many reported symptoms match this disease
        matching_ids = reported_symptom_ids & disease_symptom_ids
        match_count = len(matching_ids)

        if match_count == 0:
            continue

        # Calculate match percentage based on disease symptoms
        # e.g. if disease has 8 symptoms and user has 6 of them = 75%
        match_percentage = round(
            (match_count / len(disease_symptom_ids)) * 100
        )

        # Only include diseases with meaningful overlap
        # 40% threshold avoids false positives
        if match_percentage >= 40:
            # Parse precautions from comma-separated string
            precautions = []
            if disease.precautions:
                precautions = [
                    p.strip()
                    for p in disease.precautions.split(',')
                    if p.strip()
                ]

            matches.append({
                'name': disease.name,
                'description': disease.description,
                'match_percentage': match_percentage,
                'urgency_level': disease.urgency_level,
                'precautions': precautions
            })

    # Sort by match percentage (highest first)
    matches.sort(key=lambda x: x['match_percentage'], reverse=True)

    # Return only top 3 to avoid overwhelming the user
    return matches[:3]