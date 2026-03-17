import csv
import os
from django.core.management.base import BaseCommand
from chatbot.models import Symptom, UrgencyRule

class Command(BaseCommand):
    help = 'Load symptoms and urgency rules from CSV files'

    def handle(self, *args, **kwargs):
        self.load_symptoms()
        self.load_urgency_rules()
        self.stdout.write(self.style.SUCCESS('All data loaded successfully!'))

    def load_symptoms(self):
        csv_path = os.path.join('chatbot', 'data', 'symptoms.csv')
        
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
        
        self.stdout.write(self.style.SUCCESS(f'Loaded {count} new symptoms'))

    def load_urgency_rules(self):
        csv_path = os.path.join('chatbot', 'data', 'urgency_rules.csv')
        
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            count = 0
            for row in reader:
                # Convert string values to proper types
                requires_all = row['requires_all'].strip().lower() == 'true'
                priority = int(row['priority'])
                
                # Create rule
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
                    # Add symptoms to rule
                    symptom_names = [s.strip() for s in row['symptoms'].split(',')]
                    for symptom_name in symptom_names:
                        try:
                            symptom = Symptom.objects.get(name=symptom_name)
                            rule.symptoms.add(symptom)
                        except Symptom.DoesNotExist:
                            self.stdout.write(
                                self.style.WARNING(f'  Warning: Symptom "{symptom_name}" not found for rule "{rule.name}"')
                            )
                    count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Loaded {count} new urgency rules'))