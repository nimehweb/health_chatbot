import csv
import os
from django.core.management.base import BaseCommand
from chatbot.models import Symptom, UrgencyRule, Disease

class Command(BaseCommand):
    help = 'Load Nigerian health data from CSV files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete all existing urgency rules before reloading from CSV'
        )

    def handle(self, *args, **kwargs):
        reset = kwargs.get('reset', False)
        
        if reset:
            deleted_count, _ = UrgencyRule.objects.all().delete()
            self.stdout.write(self.style.WARNING(
                f'Deleted {deleted_count} existing urgency rules'
            ))
        
        self.load_symptoms()
        self.load_diseases()
        self.load_urgency_rules()
        self.stdout.write(self.style.SUCCESS('All data loaded successfully!'))

    def load_symptoms(self):
        csv_path = os.path.join('chatbot', 'data', 'nigeria_symptoms.csv')

        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(
                f'File not found: {csv_path}'
            ))
            return

        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            count = 0
            for row in reader:
                symptom, created = Symptom.objects.get_or_create(
                    name=row['name'].strip(),
                    defaults={
                        'description': row['description'].strip(),
                        'body_system': row['body_system'].strip()
                    }
                )
                if created:
                    count += 1

        self.stdout.write(self.style.SUCCESS(
            f'Loaded {count} new symptoms'
        ))

    def load_diseases(self):
        csv_path = os.path.join('chatbot', 'data', 'nigeria_diseases.csv')
        precautions_path = os.path.join(
            'chatbot', 'data', 'nigeria_precautions.csv'
        )

        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(
                f'File not found: {csv_path}'
            ))
            return

        # Build precautions lookup first
        precautions_map = {}
        if os.path.exists(precautions_path):
            with open(precautions_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    disease_name = row['disease'].strip()
                    precs = [
                        row.get('precaution_1', '').strip(),
                        row.get('precaution_2', '').strip(),
                        row.get('precaution_3', '').strip(),
                        row.get('precaution_4', '').strip(),
                    ]
                    # Filter out empty strings
                    precs = [p for p in precs if p]
                    if precs:
                        precautions_map[disease_name] = ', '.join(precs)

        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            count = 0
            for row in reader:
                disease_name = row['name'].strip()

                # Get precautions for this disease
                precautions = precautions_map.get(disease_name, '')

                # Create or get the disease
                disease, created = Disease.objects.get_or_create(
                    name=disease_name,
                    defaults={
                        'description': row['description'].strip(),
                        'urgency_level': row['urgency_level'].strip(),
                        'precautions': precautions,
                    }
                )

                if created:
                    # Add symptoms to this disease
                    symptom_names = [
                        s.strip()
                        for s in row['symptoms'].split(',')
                        if s.strip()
                    ]

                    for symptom_name in symptom_names:
                        try:
                            symptom = Symptom.objects.get(
                                name=symptom_name
                            )
                            disease.symptoms.add(symptom)
                        except Symptom.DoesNotExist:
                            self.stdout.write(self.style.WARNING(
                                f'  Symptom not found: "{symptom_name}" '
                                f'for disease "{disease_name}"'
                            ))
                    count += 1

        self.stdout.write(self.style.SUCCESS(
            f'Loaded {count} new diseases'
        ))
    
    def load_urgency_rules(self):
        csv_path = os.path.join(
            'chatbot', 'data', 'nigeria_urgency_rules.csv'
        )

        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(
                f'File not found: {csv_path}'
            ))
            return

        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            count = 0
            for row in reader:
                requires_all = row['requires_all'].strip().lower() == 'true'
                priority = int(row['priority'])

                rule, created = UrgencyRule.objects.get_or_create(
                    name=row['name'].strip(),
                    defaults={
                        'urgency_level': row['urgency_level'].strip(),
                        'requires_all': requires_all,
                        'priority': priority,
                        'guidance_text': row['guidance_text'].strip()
                    }
                )

                if created:
                    symptom_names = [
                        s.strip()
                        for s in row['symptoms'].split(',')
                        if s.strip()
                    ]
                    for symptom_name in symptom_names:
                        try:
                            symptom = Symptom.objects.get(name=symptom_name)
                            rule.symptoms.add(symptom)
                        except Symptom.DoesNotExist:
                            self.stdout.write(self.style.WARNING(
                                f'  Symptom not found: "{symptom_name}" '
                                f'for rule "{rule.name}"'
                            ))
                    count += 1

        self.stdout.write(self.style.SUCCESS(
            f'Loaded {count} new urgency rules'
        ))