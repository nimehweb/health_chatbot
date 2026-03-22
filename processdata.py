import csv
import os

# ── Nigeria-relevant diseases we want to keep ──────────────────
# Selected based on burden of disease in Nigeria
NIGERIA_DISEASES = {
    'Malaria',
    'Typhoid',
    'Tuberculosis',
    'Pneumonia',
    'Common Cold',
    'Bronchial Asthma',
    'Diabetes',
    'Hypertension',
    'Peptic ulcer diseae',   # we will fix the typo
    'Urinary tract infection',
    'Hepatitis A',
    'Hepatitis B',
    'Gastroenteritis',
    'Chicken pox',
    'Dengue',
    'Jaundice',
    'Fungal infection',
    'Arthritis',
    'Migraine',
    'Heart attack',
    'Anaemia',               # we will add this manually
    'Sickle cell crisis',    # we will add this manually
}

# ── Symptom name cleanup ────────────────────────────────────────
def clean_symptom(name):
    """Convert symptom_name to Symptom Name"""
    name = name.strip().replace('_', ' ')
    # Fix specific known issues
    replacements = {
        'high fever': 'High Fever',
        'mild fever': 'Mild Fever',
        'skin rash': 'Skin Rash',
        'abdominal pain': 'Abdominal Pain',
        'chest pain': 'Chest Pain',
        'joint pain': 'Joint Pain',
        'muscle pain': 'Muscle Pain',
        'back pain': 'Back Pain',
        'neck pain': 'Neck Pain',
        'blurred and distorted vision': 'Blurred Vision',
        'breathlessness': 'Shortness of Breath',
        'diarrhoea': 'Diarrhea',
        'continuous sneezing': 'Sneezing',
        'runny nose': 'Runny Nose',
        'loss of appetite': 'Loss of Appetite',
        'dark urine': 'Dark Urine',
        'yellowish skin': 'Yellowing of Skin',
        'yellowing of eyes': 'Yellowing of Eyes',
        'swelled lymph nodes': 'Swollen Lymph Nodes',
        'fast heart rate': 'Rapid Heartbeat',
        'burning micturition': 'Burning Urination',
        'foul smell of urine': 'Foul-smelling Urine',
        'continuous feel of urine': 'Frequent Urination',
        'bladder discomfort': 'Bladder Discomfort',
        'weight loss': 'Weight Loss',
        'weight gain': 'Weight Gain',
        'mood swings': 'Mood Swings',
        'cold hands and feets': 'Cold Hands and Feet',
        'loss of balance': 'Loss of Balance',
        'stiff neck': 'Stiff Neck',
        'spinning movements': 'Dizziness',
        'sunken eyes': 'Sunken Eyes',
        'red spots over body': 'Red Spots on Body',
        'pain behind the eyes': 'Pain Behind Eyes',
        'toxic look  typhos': 'Toxic Appearance',
        'throat irritation': 'Sore Throat',
        'phlegm': 'Phlegm',
        'blood in sputum': 'Blood in Cough',
        'mucoid sputum': 'Mucus in Cough',
        'rusty sputum': 'Rusty Coloured Sputum',
        'irregular sugar level': 'Irregular Blood Sugar',
        'polyuria': 'Excessive Urination',
        'excessive hunger': 'Excessive Hunger',
        'increased appetite': 'Increased Appetite',
        'passage of gases': 'Excessive Gas',
        'stomach pain': 'Stomach Pain',
        'indigestion': 'Indigestion',
        'acidity': 'Acidity',
        'ulcers on tongue': 'Mouth Ulcers',
        'internal itching': 'Internal Itching',
        'dehydration': 'Dehydration',
        'acute liver failure': 'Liver Failure',
        'altered sensorium': 'Altered Consciousness',
        'muscle wasting': 'Muscle Wasting',
        'muscle weakness': 'Muscle Weakness',
        'weakness in limbs': 'Weakness in Limbs',
        'weakness of one body side': 'One-sided Weakness',
        'lethargy': 'Lethargy',
        'malaise': 'General Malaise',
        'restlessness': 'Restlessness',
        'palpitations': 'Heart Palpitations',
        'lack of concentration': 'Difficulty Concentrating',
        'loss of smell': 'Loss of Smell',
        'redness of eyes': 'Red Eyes',
        'sinus pressure': 'Sinus Pressure',
        'congestion': 'Nasal Congestion',
        'watering from eyes': 'Watery Eyes',
        'shivering': 'Shivering',
        'depression': 'Depression',
        'irritability': 'Irritability',
        'anxiety': 'Anxiety',
    }
    lower = name.lower()
    return replacements.get(lower, name.title())

# ── Symptoms we want to keep (relevant, not too obscure) ────────
EXCLUDED_SYMPTOMS = {
    'extra_marital_contacts',
    'family_history',
    'receiving_blood_transfusion',
    'receiving_unsterile_injections',
    'history_of_alcohol_consumption',
    'dischromic _patches',
    'nodal_skin_eruptions',
    'toxic_look_(typhos)',
    'small_dents_in_nails',
    'silver_like_dusting',
    'prominent_veins_on_calf',
    'scurring',
    'pus_filled_pimples',
    'blackheads',
    'puffy_face_and_eyes',
    'enlarged_thyroid',
    'brittle_nails',
    'swollen_extremeties',
    'swollen_blood_vessels',
    'swollen_legs',
    'fluid_overload',
    'distention_of_abdomen',
    'swelling_of_stomach',
    'yellow_crust_ooze',
    'red_sore_around_nose',
    'blister',
    'skin_peeling',
    'inflammatory_nails',
    'movement_stiffness',
    'painful_walking',
    'hip_joint_pain',
    'knee_pain',
    'pain_during_bowel_movements',
    'pain_in_anal_region',
    'irritation_in_anus',
    'bloody_stool',
    'patches_in_throat',
    'obesity',
    'bruising',
    'cramps',
    'spotting_ urination',
    'drying_and_tingling_lips',
    'slurred_speech',
    'visual_disturbances',
    'unsteadiness',
    'coma',
    'stomach_bleeding',
}

# ── Disease descriptions (Nigerian context) ─────────────────────
DISEASE_DESCRIPTIONS = {
    'Malaria': 'A mosquito-borne infectious disease common in Nigeria, caused by Plasmodium parasites.',
    'Typhoid': 'A bacterial infection caused by Salmonella typhi, spread through contaminated food and water.',
    'Tuberculosis': 'A serious bacterial infection primarily affecting the lungs, spread through the air.',
    'Pneumonia': 'An infection that inflames the air sacs in the lungs, very common in Nigeria.',
    'Common Cold': 'A viral infection of the upper respiratory tract, usually mild and self-limiting.',
    'Bronchial Asthma': 'A chronic condition causing airway inflammation and breathing difficulty.',
    'Diabetes': 'A metabolic disease causing high blood sugar levels, increasingly common in Nigeria.',
    'Hypertension': 'High blood pressure, a leading cause of stroke and heart disease in Nigeria.',
    'Peptic Ulcer Disease': 'Sores that develop on the lining of the stomach or small intestine.',
    'Urinary Tract Infection': 'A bacterial infection in any part of the urinary system, more common in women.',
    'Hepatitis A': 'A viral liver infection spread through contaminated food and water.',
    'Hepatitis B': 'A serious viral liver infection, endemic in Nigeria with high prevalence.',
    'Gastroenteritis': 'Inflammation of the stomach and intestines, commonly called stomach flu.',
    'Chicken Pox': 'A highly contagious viral infection causing an itchy blister-like rash.',
    'Dengue': 'A mosquito-borne viral infection causing severe flu-like illness.',
    'Jaundice': 'A condition causing yellowing of skin and eyes, often a sign of liver problems.',
    'Fungal Infection': 'Infections caused by fungi, very common in the Nigerian tropical climate.',
    'Arthritis': 'Inflammation of joints causing pain and stiffness.',
    'Migraine': 'A neurological condition causing severe recurring headaches.',
    'Heart Attack': 'A medical emergency where blood supply to the heart is suddenly blocked.',
}

# ── Urgency levels per disease ──────────────────────────────────
DISEASE_URGENCY = {
    'Malaria': 'urgent',
    'Typhoid': 'urgent',
    'Tuberculosis': 'urgent',
    'Pneumonia': 'urgent',
    'Common Cold': 'self_care',
    'Bronchial Asthma': 'urgent',
    'Diabetes': 'moderate',
    'Hypertension': 'moderate',
    'Peptic Ulcer Disease': 'moderate',
    'Urinary Tract Infection': 'moderate',
    'Hepatitis A': 'urgent',
    'Hepatitis B': 'urgent',
    'Gastroenteritis': 'moderate',
    'Chicken Pox': 'moderate',
    'Dengue': 'urgent',
    'Jaundice': 'urgent',
    'Fungal Infection': 'self_care',
    'Arthritis': 'self_care',
    'Migraine': 'moderate',
    'Heart Attack': 'emergency',
}


def process_data():
    input_path = 'chatbot/data'
    os.makedirs(input_path, exist_ok=True)

    all_symptoms = set()
    disease_symptom_map = {}

    # ── Step 1: Read disease_symptoms.csv ──────────────────────
    with open('C:/Users/Admin/Downloads/archive/disease_symptoms.csv',
              encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            disease = row['Disease'].strip()

            # Fix known typos
            if disease == 'Peptic ulcer diseae':
                disease = 'Peptic Ulcer Disease'
            if disease == 'hepatitis A':
                disease = 'Hepatitis A'
            disease = disease.strip()

            # Only keep Nigeria-relevant diseases
            if disease not in NIGERIA_DISEASES and \
               disease.lower() not in [d.lower() for d in NIGERIA_DISEASES]:
                continue

            symptoms = []
            for i in range(1, 18):
                key = f'Symptom_{i}'
                val = row.get(key, '').strip()
                if val and val not in EXCLUDED_SYMPTOMS:
                    cleaned = clean_symptom(val)
                    if cleaned:
                        symptoms.append(cleaned)
                        all_symptoms.add(cleaned)

            if symptoms:
                disease_symptom_map[disease] = symptoms

    # ── Step 2: Write nigeria_symptoms.csv ─────────────────────
    body_system_map = {
        'Fever': 'general', 'High Fever': 'general', 'Mild Fever': 'general',
        'Chills': 'general', 'Sweating': 'general', 'Fatigue': 'general',
        'Weight Loss': 'general', 'Weight gain': 'general',
        'Loss of Appetite': 'general', 'Dehydration': 'general',
        'Malaise': 'general', 'General Malaise': 'general',
        'Lethargy': 'general', 'Restlessness': 'general',
        'Cough': 'respiratory', 'Shortness of Breath': 'respiratory',
        'Phlegm': 'respiratory', 'Sneezing': 'respiratory',
        'Runny Nose': 'respiratory', 'Sore Throat': 'respiratory',
        'Nasal Congestion': 'respiratory', 'Sinus Pressure': 'respiratory',
        'Blood in Cough': 'respiratory', 'Mucus in Cough': 'respiratory',
        'Chest Pain': 'cardiovascular', 'Rapid Heartbeat': 'cardiovascular',
        'Heart Palpitations': 'cardiovascular',
        'Headache': 'neurological', 'Dizziness': 'neurological',
        'Blurred Vision': 'neurological', 'Stiff Neck': 'neurological',
        'Loss of Balance': 'neurological', 'Altered Consciousness': 'neurological',
        'One-sided Weakness': 'neurological', 'Difficulty Concentrating': 'neurological',
        'Nausea': 'digestive', 'Vomiting': 'digestive', 'Diarrhea': 'digestive',
        'Abdominal Pain': 'digestive', 'Stomach Pain': 'digestive',
        'Indigestion': 'digestive', 'Acidity': 'digestive',
        'Loss of Smell': 'digestive', 'Excessive Gas': 'digestive',
        'Dark Urine': 'digestive', 'Yellowing of Skin': 'digestive',
        'Yellowing of Eyes': 'digestive', 'Mouth Ulcers': 'digestive',
        'Joint Pain': 'musculoskeletal', 'Muscle Pain': 'musculoskeletal',
        'Back Pain': 'musculoskeletal', 'Neck Pain': 'musculoskeletal',
        'Muscle Weakness': 'musculoskeletal', 'Weakness in Limbs': 'musculoskeletal',
        'Muscle Wasting': 'musculoskeletal',
        'Skin Rash': 'general', 'Itching': 'general',
        'Red Spots on Body': 'general', 'Swollen Lymph Nodes': 'general',
        'Burning Urination': 'general', 'Frequent Urination': 'general',
        'Foul-smelling Urine': 'general', 'Bladder Discomfort': 'general',
        'Irregular Blood Sugar': 'general', 'Excessive Urination': 'general',
        'Excessive Hunger': 'general', 'Increased Appetite': 'general',
        'Depression': 'neurological', 'Irritability': 'neurological',
        'Anxiety': 'neurological', 'Mood Swings': 'neurological',
    }

    symptoms_written = set()
    with open(f'{input_path}/nigeria_symptoms.csv', 'w',
              newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['name', 'description', 'body_system'])
        for symptom in sorted(all_symptoms):
            if symptom in symptoms_written:
                continue
            symptoms_written.add(symptom)
            body_system = body_system_map.get(symptom, 'general')
            description = f'Patient reports {symptom.lower()}'
            writer.writerow([symptom, description, body_system])

    print(f'✅ nigeria_symptoms.csv — {len(symptoms_written)} symptoms')

    # ── Step 3: Write nigeria_diseases.csv ─────────────────────
    with open(f'{input_path}/nigeria_diseases.csv', 'w',
              newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'name', 'description', 'urgency_level', 'symptoms'
        ])
        for disease, symptoms in disease_symptom_map.items():
            clean_name = disease.strip()
            description = DISEASE_DESCRIPTIONS.get(
                clean_name,
                f'A medical condition presenting with {symptoms[0].lower()} and other symptoms.'
            )
            urgency = DISEASE_URGENCY.get(clean_name, 'moderate')
            symptoms_str = ', '.join(symptoms)
            writer.writerow([clean_name, description, urgency, symptoms_str])

    print(f'✅ nigeria_diseases.csv — {len(disease_symptom_map)} diseases')

    # ── Step 4: Write nigeria_precautions.csv ──────────────────
    precautions_map = {}
    with open('C:/Users/Admin/Downloads/archive/disease_precaution.csv',
              encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            disease = row['Disease'].strip()
            precautions = [
                row.get('Precaution_1', '').strip(),
                row.get('Precaution_2', '').strip(),
                row.get('Precaution_3', '').strip(),
                row.get('Precaution_4', '').strip(),
            ]
            precautions = [p for p in precautions if p]
            if precautions:
                precautions_map[disease] = precautions

    with open(f'{input_path}/nigeria_precautions.csv', 'w',
              newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['disease', 'precaution_1', 'precaution_2',
                         'precaution_3', 'precaution_4'])
        for disease, precs in precautions_map.items():
            while len(precs) < 4:
                precs.append('')
            writer.writerow([disease] + precs[:4])

    print(f'✅ nigeria_precautions.csv — {len(precautions_map)} entries')
    print('\n🎉 All files written to chatbot/data/')


if __name__ == '__main__':
    process_data()