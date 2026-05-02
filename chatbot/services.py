import math
from .models import UrgencyRule, Disease, Symptom

def evaluate_urgency(reported_symptoms):
    """
    Takes a queryset of Symptom objects.
    Returns the matching urgency level + guidance text.

    Checks rules in priority order (highest first).
    For each rule:
    - requires_all=True: ALL rule symptoms must be in reported symptoms
    - requires_all=False: ANY one rule symptom triggers it
    """
    reported_symptom_ids = set(
        reported_symptoms.values_list('id', flat=True)
    )

    if not reported_symptom_ids:
        return "self_care", "Please monitor your symptoms and rest. Seek medical advice if your condition worsens."

    rules = UrgencyRule.objects.prefetch_related('symptoms').all()

    for rule in rules:
        rule_symptom_ids = set(
            rule.symptoms.values_list('id', flat=True)
        )

        if not rule_symptom_ids:
            continue

        if rule.requires_all:
            if rule_symptom_ids.issubset(reported_symptom_ids):
                return rule.urgency_level, rule.guidance_text
        else:
            if rule_symptom_ids & reported_symptom_ids:
                return rule.urgency_level, rule.guidance_text

    return "self_care", "Monitor your symptoms and rest. Seek medical advice if your condition worsens."


def _compute_idf_weights(all_diseases):
    """
    Compute Inverse Document Frequency (IDF) weights for every symptom
    across all diseases in the database.
    """
    total_diseases = len(all_diseases)

    if total_diseases == 0:
        return {}

    symptom_disease_count = {}
    for disease in all_diseases:
        for symptom_id in disease['symptom_ids']:
            symptom_disease_count[symptom_id] = (
                symptom_disease_count.get(symptom_id, 0) + 1
            )

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

    Key fix: raised the minimum threshold and added a minimum symptom
    count requirement so diseases with only 1 matching symptom out of
    many don't surface as probable conditions.
    """
    reported_symptom_ids = set(
        reported_symptoms.values_list('id', flat=True)
    )

    if not reported_symptom_ids:
        return []

    diseases = Disease.objects.prefetch_related('symptoms').all()

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

    idf_weights = _compute_idf_weights(all_diseases_data)

    matches = []

    for entry in all_diseases_data:
        disease = entry['disease']
        disease_symptom_ids = entry['symptom_ids']

        matching_ids = reported_symptom_ids & disease_symptom_ids

        if not matching_ids:
            continue

        # ── New guard: require at least 2 matching symptoms ──────
        # This stops a disease with 10 symptoms from appearing just
        # because 1 common symptom (like Headache) matched.
        if len(matching_ids) < 2:
            continue

        weighted_match = sum(
            idf_weights.get(sid, 1.0) for sid in matching_ids
        )
        weighted_total = sum(
            idf_weights.get(sid, 1.0) for sid in disease_symptom_ids
        )

        if weighted_total == 0:
            continue

        match_percentage = round((weighted_match / weighted_total) * 100)

        # ── Raised threshold from 40% to 50% ────────────────────
        # 40% was too easy to hit with just one or two common symptoms.
        if match_percentage >= 50:
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

    matches.sort(key=lambda x: x['match_percentage'], reverse=True)
    return matches[:3]


def get_symptom_variants(symptom_names):
    """
    Given a list of symptom names reported by the user (e.g. ['Fever',
    'Headache']), also return related/broader variants from the database.

    For example 'Fever' should also pull in 'High Fever' and 'Mild Fever'
    so urgency rules and disease matching work correctly even when the LLM
    matched the general term.

    Returns the original queryset expanded with variants.
    """
    VARIANT_MAP = {
        'Fever': ['High Fever', 'Mild Fever', 'Fever'],
        'High Fever': ['High Fever', 'Fever'],
        'Mild Fever': ['Mild Fever', 'Fever'],
        'Cough': ['Cough', 'Mucus in Cough', 'Blood in Cough'],
        'Headache': ['Headache'],
        'Body Pain': ['Muscle Pain', 'Body Pain', 'General Malaise'],
        'Stomach Pain': ['Abdominal Pain', 'Stomach Pain', 'Belly Pain'],
        'Urination Pain': ['Burning Urination', 'Frequent Urination'],
    }

    expanded = set(symptom_names)
    for name in symptom_names:
        if name in VARIANT_MAP:
            expanded.update(VARIANT_MAP[name])

    return list(expanded)