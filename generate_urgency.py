import csv
import os

output_path = os.path.join('chatbot', 'data', 'nigeria_urgency_rules.csv')

rules = [

    # ── EMERGENCY RULES (priority 90-100) ──────────────────────
    # These are life threatening - immediate action needed
    {
        'name': 'Heart Attack',
        'urgency_level': 'emergency',
        'requires_all': 'True',
        'priority': 100,
        'guidance_text': (
            '🚨 Call emergency services immediately. '
            'These symptoms suggest a possible heart attack. '
            'Do not drive yourself. Chew aspirin if available '
            'and not allergic. Sit upright and stay calm while '
            'waiting for help.'
        ),
        'symptoms': 'Chest Pain, Shortness of Breath, Sweating, Vomiting'
    },
    {
        'name': 'Severe Breathing Emergency',
        'urgency_level': 'emergency',
        'requires_all': 'True',
        'priority': 98,
        'guidance_text': (
            '🚨 Severe difficulty breathing requires immediate '
            'emergency care. Call emergency services now or go '
            'to the nearest hospital immediately. If prescribed '
            'an inhaler, use it while waiting for help.'
        ),
        'symptoms': 'Shortness of Breath, Chest Pain'
    },
    {
        'name': 'High Fever with Altered Consciousness',
        'urgency_level': 'emergency',
        'requires_all': 'True',
        'priority': 96,
        'guidance_text': (
            '🚨 High fever with confusion or altered consciousness '
            'is a medical emergency. This could indicate severe '
            'malaria, meningitis, or typhoid complications. '
            'Call emergency services or go to hospital immediately. '
            'Cool the person with a damp cloth while waiting.'
        ),
        'symptoms': 'High Fever, Altered Consciousness'
    },
    {
        'name': 'Meningitis Warning Signs',
        'urgency_level': 'emergency',
        'requires_all': 'True',
        'priority': 95,
        'guidance_text': (
            '🚨 Stiff neck with high fever and headache can indicate '
            'meningitis which is a medical emergency in Nigeria. '
            'Go to the nearest hospital immediately. '
            'Do not wait to see if symptoms improve.'
        ),
        'symptoms': 'Stiff Neck, High Fever, Headache'
    },
    {
        'name': 'Severe Dehydration Emergency',
        'urgency_level': 'emergency',
        'requires_all': 'True',
        'priority': 93,
        'guidance_text': (
            '🚨 Severe dehydration with vomiting and diarrhea '
            'can be life threatening, especially in children. '
            'This may indicate cholera or severe gastroenteritis. '
            'Seek emergency care immediately. Give oral rehydration '
            'solution (ORS) if conscious while going to hospital.'
        ),
        'symptoms': 'Dehydration, Vomiting, Diarrhea'
    },
    {
        'name': 'Tuberculosis Blood in Cough',
        'urgency_level': 'emergency',
        'requires_all': 'True',
        'priority': 91,
        'guidance_text': (
            '🚨 Coughing up blood is a serious warning sign. '
            'This could indicate advanced tuberculosis or another '
            'serious lung condition. Go to hospital immediately. '
            'Cover your mouth when coughing to avoid spreading infection.'
        ),
        'symptoms': 'Cough, Blood in Cough'
    },

    # ── URGENT RULES (priority 60-89) ──────────────────────────
    # Serious Nigerian diseases - see doctor within 24 hours
    {
        'name': 'Malaria',
        'urgency_level': 'urgent',
        'requires_all': 'True',
        'priority': 88,
        'guidance_text': (
            'Your symptoms strongly suggest malaria which is very '
            'common in Nigeria. See a doctor or go to a clinic today '
            'for a rapid malaria test. Do not self-medicate. '
            'Stay hydrated, rest, and use a mosquito net. '
            'If fever rises above 39°C or you feel confused, '
            'go to hospital immediately.'
        ),
        'symptoms': 'High Fever, Chills, Sweating, Headache'
    },
    {
        'name': 'Typhoid Fever',
        'urgency_level': 'urgent',
        'requires_all': 'True',
        'priority': 85,
        'guidance_text': (
            'Your symptoms are consistent with typhoid fever. '
            'See a doctor within 24 hours for proper testing. '
            'Typhoid requires antibiotic treatment - do not delay. '
            'Drink only clean boiled water, eat light easily '
            'digestible foods, and rest completely.'
        ),
        'symptoms': 'High Fever, Abdominal Pain, Nausea, Headache'
    },
    {
        'name': 'Tuberculosis Symptoms',
        'urgency_level': 'urgent',
        'requires_all': 'True',
        'priority': 83,
        'guidance_text': (
            'Your symptoms may indicate tuberculosis which is '
            'treatable but requires prompt medical attention. '
            'See a doctor today. TB treatment is free at government '
            'hospitals in Nigeria through the NTBLCP program. '
            'Cover your mouth when coughing and avoid close contact '
            'with others until you are assessed.'
        ),
        'symptoms': 'Cough, High Fever, Weight Loss, Sweating'
    },
    {
        'name': 'Pneumonia',
        'urgency_level': 'urgent',
        'requires_all': 'True',
        'priority': 81,
        'guidance_text': (
            'Your symptoms suggest pneumonia which requires '
            'prompt medical treatment. See a doctor today. '
            'Pneumonia needs antibiotics - home remedies alone '
            'are not sufficient. Rest completely, stay warm, '
            'and drink plenty of fluids while seeking care.'
        ),
        'symptoms': 'High Fever, Cough, Shortness of Breath, Chills'
    },
    {
        'name': 'Dengue Fever',
        'urgency_level': 'urgent',
        'requires_all': 'True',
        'priority': 79,
        'guidance_text': (
            'Your symptoms suggest possible dengue fever. '
            'See a doctor today for a blood test. '
            'Do NOT take aspirin or ibuprofen - use only '
            'paracetamol for pain and fever. Stay very well '
            'hydrated. Watch for severe abdominal pain or '
            'bleeding which needs emergency care.'
        ),
        'symptoms': 'High Fever, Joint Pain, Headache, Skin Rash'
    },
    {
        'name': 'Hepatitis',
        'urgency_level': 'urgent',
        'requires_all': 'True',
        'priority': 77,
        'guidance_text': (
            'Yellowing of the skin or eyes with these symptoms '
            'suggests possible hepatitis or liver problem. '
            'See a doctor within 24 hours for liver function tests. '
            'Avoid alcohol completely, eat light low-fat meals, '
            'and rest. Hepatitis B is very common in Nigeria - '
            'vaccination is available.'
        ),
        'symptoms': 'Yellowing of Skin, Yellowing of Eyes, Fatigue'
    },
    {
        'name': 'Severe Malaria Single Symptom',
        'urgency_level': 'urgent',
        'requires_all': 'False',
        'priority': 75,
        'guidance_text': (
            'High fever in Nigeria should always be investigated '
            'for malaria. See a doctor or visit a pharmacy with '
            'a rapid diagnostic test today. Do not assume it is '
            'just a common cold. Stay hydrated and rest while '
            'seeking medical attention.'
        ),
        'symptoms': 'High Fever, Chills'
    },
    {
        'name': 'Asthma Attack',
        'urgency_level': 'urgent',
        'requires_all': 'True',
        'priority': 73,
        'guidance_text': (
            'These symptoms suggest an asthma episode. '
            'Use your reliever inhaler immediately if you have one. '
            'Sit upright and try to stay calm. If breathing does '
            'not improve within 15 minutes, go to hospital. '
            'Avoid triggers like dust, smoke, and cold air.'
        ),
        'symptoms': 'Shortness of Breath, Cough, Fatigue'
    },
    {
        'name': 'Hypertension Crisis',
        'urgency_level': 'urgent',
        'requires_all': 'True',
        'priority': 71,
        'guidance_text': (
            'Chest pain with headache and dizziness can indicate '
            'a hypertensive crisis which is common in Nigeria. '
            'See a doctor today to check your blood pressure. '
            'Sit and rest, avoid stress and exertion. '
            'If you are on blood pressure medication take it now. '
            'Do not ignore these symptoms.'
        ),
        'symptoms': 'Chest Pain, Headache, Dizziness'
    },
    {
        'name': 'Urinary Tract Infection',
        'urgency_level': 'urgent',
        'requires_all': 'True',
        'priority': 65,
        'guidance_text': (
            'Your symptoms suggest a urinary tract infection. '
            'See a doctor within 24 hours for urine tests and '
            'antibiotics. Drink plenty of clean water. '
            'Do not self-medicate with leftover antibiotics. '
            'UTIs can spread to kidneys if left untreated.'
        ),
        'symptoms': 'Burning Urination, Frequent Urination, Bladder Discomfort'
    },

    # ── MODERATE RULES (priority 30-59) ────────────────────────
    # Needs attention but not immediately
    {
        'name': 'Gastroenteritis',
        'urgency_level': 'moderate',
        'requires_all': 'True',
        'priority': 58,
        'guidance_text': (
            'Your symptoms suggest gastroenteritis or stomach flu. '
            'Rest and stay well hydrated with ORS or clean water. '
            'Eat light foods like rice, bread, or bananas. '
            'See a doctor if symptoms persist beyond 2 days, '
            'if there is blood in stool, or if you cannot keep '
            'fluids down at all.'
        ),
        'symptoms': 'Vomiting, Diarrhea, Nausea'
    },
    {
        'name': 'Peptic Ulcer',
        'urgency_level': 'moderate',
        'requires_all': 'True',
        'priority': 55,
        'guidance_text': (
            'Your symptoms suggest a possible peptic ulcer. '
            'Avoid spicy foods, alcohol, and pain relievers like '
            'aspirin or ibuprofen. Eat small frequent meals. '
            'See a doctor within 2-3 days. '
            'If you vomit blood or have very severe sudden '
            'abdominal pain, go to hospital immediately.'
        ),
        'symptoms': 'Abdominal Pain, Vomiting, Loss of Appetite, Indigestion'
    },
    {
        'name': 'Diabetes Symptoms',
        'urgency_level': 'moderate',
        'requires_all': 'True',
        'priority': 52,
        'guidance_text': (
            'Your symptoms may indicate diabetes or blood sugar '
            'problems which are increasingly common in Nigeria. '
            'See a doctor within 2-3 days for blood sugar testing. '
            'Reduce sugar and processed food intake. '
            'Exercise regularly and maintain a healthy weight.'
        ),
        'symptoms': 'Excessive Hunger, Fatigue, Blurred Vision, Weight Loss'
    },
    {
        'name': 'Chicken Pox',
        'urgency_level': 'moderate',
        'requires_all': 'True',
        'priority': 49,
        'guidance_text': (
            'Your symptoms suggest chicken pox. '
            'Stay at home and avoid contact with others, '
            'especially pregnant women and newborns. '
            'Do not scratch the rash - trim nails and use '
            'calamine lotion to relieve itching. '
            'See a doctor if fever is very high or rash '
            'becomes infected.'
        ),
        'symptoms': 'Skin Rash, High Fever, Itching, Fatigue'
    },
    {
        'name': 'Jaundice',
        'urgency_level': 'moderate',
        'requires_all': 'False',
        'priority': 46,
        'guidance_text': (
            'Yellowing of the skin or eyes needs medical '
            'evaluation within 2-3 days. This can have several '
            'causes including malaria, hepatitis, or other '
            'liver conditions. Avoid alcohol completely. '
            'Eat light low-fat meals and drink clean water.'
        ),
        'symptoms': 'Yellowing of Skin, Yellowing of Eyes, Dark Urine'
    },
    {
        'name': 'Hypertension Monitoring',
        'urgency_level': 'moderate',
        'requires_all': 'False',
        'priority': 43,
        'guidance_text': (
            'Your symptoms may be related to high blood pressure '
            'which is very common in Nigeria. Schedule a doctor '
            'appointment within 2-3 days to check your blood '
            'pressure. Reduce salt intake, avoid stress, exercise '
            'regularly, and get enough sleep.'
        ),
        'symptoms': 'Headache, Dizziness, Fatigue'
    },
    {
        'name': 'Fungal Infection',
        'urgency_level': 'moderate',
        'requires_all': 'True',
        'priority': 38,
        'guidance_text': (
            'Your symptoms suggest a fungal skin infection which '
            'is very common in Nigeria due to the hot humid climate. '
            'Keep the affected area clean and dry. '
            'Antifungal creams are available at pharmacies. '
            'See a doctor if it spreads or does not improve '
            'within a week.'
        ),
        'symptoms': 'Skin Rash, Itching'
    },

    # ── SELF CARE RULES (priority 1-29) ────────────────────────
    # Can be managed at home
    {
        'name': 'Common Cold',
        'urgency_level': 'self_care',
        'requires_all': 'True',
        'priority': 28,
        'guidance_text': (
            'Your symptoms are consistent with a common cold. '
            'Rest at home and drink plenty of warm fluids. '
            'You can take paracetamol for fever and body aches. '
            'Steam inhalation helps with congestion. '
            'Most colds resolve in 7-10 days. '
            'See a doctor if fever lasts more than 3 days or '
            'symptoms significantly worsen.'
        ),
        'symptoms': 'Cough, Runny Nose, Sneezing, Sore Throat'
    },
    {
        'name': 'Mild Fever and Fatigue',
        'urgency_level': 'self_care',
        'requires_all': 'True',
        'priority': 22,
        'guidance_text': (
            'Rest and drink plenty of fluids. '
            'Take paracetamol for fever if needed. '
            'Eat light nutritious meals. '
            'Monitor your temperature. '
            'See a doctor if fever rises above 38.5°C, '
            'lasts more than 2 days, or other symptoms develop. '
            'Note: In Nigeria any fever should be considered '
            'for malaria testing.'
        ),
        'symptoms': 'Mild Fever, Fatigue'
    },
    {
        'name': 'General Body Pain',
        'urgency_level': 'self_care',
        'requires_all': 'False',
        'priority': 18,
        'guidance_text': (
            'Rest and take paracetamol for pain relief. '
            'Apply warm compress to affected areas. '
            'Gentle stretching can help with muscle pain. '
            'Stay hydrated and avoid strenuous activity. '
            'See a doctor if pain is severe, worsening, '
            'or does not improve within 3 days.'
        ),
        'symptoms': 'Muscle Pain, Joint Pain, Back Pain'
    },
    {
        'name': 'Mild Digestive Issues',
        'urgency_level': 'self_care',
        'requires_all': 'False',
        'priority': 14,
        'guidance_text': (
            'Eat light easily digestible meals. '
            'Avoid spicy, oily, and heavy foods. '
            'Drink clean water and stay hydrated. '
            'Ginger tea can help with nausea. '
            'See a doctor if symptoms persist beyond 2 days '
            'or if you cannot keep food or water down.'
        ),
        'symptoms': 'Nausea, Indigestion, Loss of Appetite'
    },
    {
        'name': 'Mild Respiratory Symptoms',
        'urgency_level': 'self_care',
        'requires_all': 'False',
        'priority': 10,
        'guidance_text': (
            'Rest and drink warm fluids like tea with honey. '
            'Steam inhalation helps relieve congestion. '
            'Avoid cold drinks and dusty environments. '
            'Gargle with warm salt water for sore throat. '
            'See a doctor if symptoms worsen or you develop '
            'high fever or difficulty breathing.'
        ),
        'symptoms': 'Cough, Sore Throat, Sneezing, Runny Nose'
    },
]

os.makedirs(os.path.dirname(output_path), exist_ok=True)

with open(output_path, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=[
        'name', 'urgency_level', 'requires_all',
        'priority', 'guidance_text', 'symptoms'
    ])
    writer.writeheader()
    for rule in rules:
        writer.writerow(rule)

print(f'✅ Generated {len(rules)} urgency rules')
print(f'   Saved to: {output_path}')
print()

# Summary
from collections import Counter
levels = Counter(r['urgency_level'] for r in rules)
for level, count in sorted(levels.items()):
    print(f'   {level}: {count} rules')