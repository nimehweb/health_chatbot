import math
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

def _compute_idf_weights(all_diseases):
    """
    Compute Inverse Document Frequency (IDF) weights for every symptom
    across all diseases in the database.

    Formula: IDF(symptom) = log(total_diseases / diseases_containing_symptom)

    A symptom that appears in only 1 out of 19 diseases gets a high weight
    (it is a strong discriminator). A symptom that appears in 15 out of 19
    diseases gets a low weight (it is too common to be useful on its own).

    Returns a dict mapping symptom_id -> float weight.
    """
    total_diseases = len(all_diseases)

    if total_diseases == 0:
        return {}

    # Count how many diseases contain each symptom
    symptom_disease_count = {}
    for disease in all_diseases:
        for symptom_id in disease['symptom_ids']:
            symptom_disease_count[symptom_id] = (
                symptom_disease_count.get(symptom_id, 0) + 1
            )

    # Compute IDF for each symptom
    # We add 1 inside log to avoid log(1) = 0 for symptoms unique to one disease
    # and to keep weights positive and meaningful across the range
    idf_weights = {}
    for symptom_id, doc_count in symptom_disease_count.items():
        idf_weights[symptom_id] = math.log(
            (total_diseases + 1) / (doc_count + 1)
        ) + 1

    return idf_weights

def match_diseases(reported_symptoms):
    """
    Matches reported symptoms against known diseases and returns the top 3
    most probable conditions using IDF-weighted symptom scoring.

    How the scoring works
    ---------------------
    Rather than treating every symptom equally (old approach), each symptom
    is assigned an Inverse Document Frequency (IDF) weight that reflects how
    *specific* it is to a particular disease:

      - A symptom like "Fatigue" appears in almost every disease -> low weight
        (it doesn't help us tell diseases apart)
      - A symptom like "Blood in Cough" appears in very few diseases -> high
        weight (it is a strong indicator of something specific like TB)

    The weighted match score for a disease is:

        score = sum(IDF weights of matching symptoms)
                -------------------------------------------
                sum(IDF weights of ALL disease symptoms)

    This means matching a rare, specific symptom contributes more to the
    score than matching a common one. The threshold is still 40% but now
    reflects weighted relevance rather than raw symptom count.

    Returns a list of dicts (top 3, sorted by score descending):
    [
        {
            'name': 'Malaria',
            'description': '...',
            'match_percentage': 85,
            'urgency_level': 'urgent',
            'precautions': ['drink fluids', ...]
        },
        ...
    ]
    """
    reported_symptom_ids = set(
        reported_symptoms.values_list('id', flat=True)
    )

    if not reported_symptom_ids:
        return []

    # Load all diseases with their symptoms in one query
    diseases = Disease.objects.prefetch_related('symptoms').all()

    # Build a list we can iterate over twice:
    # once to compute IDF, once to score each disease
    all_diseases_data = []
    for disease in diseases:
        symptom_ids = set(disease.symptoms.values_list('id', flat=True))
        if symptom_ids:
            all_diseases_data.append({
                'disease': disease,
                'symptom_ids': symptom_ids,
            })

    if not all_diseases_data:
        return []

    # Step 1 — compute IDF weights once across the whole disease corpus
    idf_weights = _compute_idf_weights(all_diseases_data)

    # Step 2 — score each disease using weighted overlap
    matches = []

    for entry in all_diseases_data:
        disease = entry['disease']
        disease_symptom_ids = entry['symptom_ids']

        # Symptoms the user reported that this disease also has
        matching_ids = reported_symptom_ids & disease_symptom_ids

        if not matching_ids:
            continue

        # Weighted score: sum of IDF weights for matching symptoms
        # divided by sum of IDF weights for all symptoms in this disease
        weighted_match = sum(
            idf_weights.get(sid, 1.0) for sid in matching_ids
        )
        weighted_total = sum(
            idf_weights.get(sid, 1.0) for sid in disease_symptom_ids
        )

        if weighted_total == 0:
            continue

        match_percentage = round((weighted_match / weighted_total) * 100)

        # Same 40% threshold as before — but now it means weighted relevance
        if match_percentage >= 40:
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
                'precautions': precautions,
            })

    # Sort by weighted score (highest first), return top 3
    matches.sort(key=lambda x: x['match_percentage'], reverse=True)
    return matches[:3]