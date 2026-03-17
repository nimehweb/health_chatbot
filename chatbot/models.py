from django.db import models

# Create your models here.
class Symptom(models.Model):
    # "Stores known symptoms that users can report."
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, help_text="A brief description of the symptom.")
    body_system = models.CharField(max_length=50, choices=[
        ('general', 'General'),
        ('respiratory', 'Respiratory'),
        ('cardiovascular', 'Cardiovascular'),
        ('neurological', 'Neurological'),
        ('musculoskeletal', 'Musculoskeletal'),
    ],default='general')
    def __str__(self):        
        return self.name

class UrgencyRule(models.Model):
    # "Defines rules for determining the urgency of symptoms."
    URGENCY_LEVELS = [('emergency', 'Emergency - seek immediate medical attention'),
        ('urgent', 'Urgent - see a doctor within 24 hours'),
        ('moderate', 'Moderate - Monitor or Schedule appoinment'),
        ('self_care', 'Self-care - Home treatment sufficient]')
        ]
    name = models.CharField(max_length= 100, help_text="Name of this rule")
    urgency_level = models.CharField(max_length = 20,  choices = URGENCY_LEVELS)
    # Symptoms that trigger this rule (many-to-many relationship)
    symptoms = models.ManyToManyField(Symptom, related_name='urgency_rules')
    
    # Logic: Does this require ALL symptoms or ANY symptom?
    requires_all = models.BooleanField(default=True, help_text="If True, ALL listed symptoms must be present. If False, ANY one symptom triggers this.")
    
    # Priority: Higher number = checked first (for conflicting rules)
    priority = models.IntegerField(default=0, help_text="Higher priority rules are checked first")
    
    guidance_text = models.TextField(help_text="What to tell the user when this rule matches")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-priority']  # Highest priority first
    
    def __str__(self):
        return f"{self.name} ({self.urgency_level})"

class ChatSession(models.Model):
    """
    Tracks a single conversation with a user.
    Like a 'case file' that stores the whole interaction.
    """
    session_id = models.CharField(max_length=100, unique=True, help_text="Unique identifier for this chat session")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Store the collected symptoms during this conversation
    reported_symptoms = models.ManyToManyField(Symptom, blank=True, related_name='chat_sessions')
    
    # Store free-text symptoms that don't match our database
    free_text_symptoms = models.TextField(blank=True, help_text="Raw symptoms user described that we couldn't match")
    
    # Current state of the conversation
    current_urgency = models.CharField(
        max_length=20, 
        choices=UrgencyRule.URGENCY_LEVELS,
        blank=True,
        null=True
    )
    
    # Is the assessment complete?
    is_complete = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Session {self.session_id} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"

class ChatMessage(models.Model):
    """
    Individual messages within a chat session.
    Keeps the full conversation history.
    """
    MESSAGE_TYPES = [
        ('user', 'User'),
        ('bot', 'Bot'),
    ]
    
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Optional: Store what the system understood from this message
    extracted_symptoms = models.JSONField(default=list, blank=True, help_text="Symptoms extracted from this message")
    
    class Meta:
        ordering = ['timestamp']  # Oldest first
    
    def __str__(self):
        return f"{self.message_type}: {self.content[:50]}..."
    