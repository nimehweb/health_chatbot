from rest_framework import serializers
from .models import Symptom, UrgencyRule, ChatSession, ChatMessage

class SymptomSerializer(serializers.ModelSerializer):
    """Converts Symptom model to/from JSON"""
    class Meta:
        model = Symptom
        fields = ['id', 'name', 'description', 'body_system']

class ChatMessageSerializer(serializers.ModelSerializer):
    """Converts ChatMessage to JSON"""
    class Meta:
        model = ChatMessage
        fields = ['id', 'message_type', 'content', 'timestamp', 'extracted_symptoms']

class ChatSessionSerializer(serializers.ModelSerializer):
    """Converts ChatSession to JSON, including related messages"""
    messages = ChatMessageSerializer(many=True, read_only=True)
    reported_symptoms = SymptomSerializer(many=True, read_only=True)
    
    class Meta:
        model = ChatSession
        fields = ['id', 'session_id', 'created_at', 'updated_at', 
                  'reported_symptoms', 'free_text_symptoms', 
                  'current_urgency', 'is_complete', 'messages']