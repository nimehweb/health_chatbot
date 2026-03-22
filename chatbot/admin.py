from django.contrib import admin

# Register your models here.
from .models import Symptom, UrgencyRule, ChatSession, ChatMessage, Disease

@admin.register(Symptom)
class SymptomAdmin(admin.ModelAdmin):
    list_display = ['name', 'body_system']
    list_filter = ['body_system']
    search_fields = ['name', 'description']

@admin.register(UrgencyRule)
class UrgencyRuleAdmin(admin.ModelAdmin):
    list_display = ['name', 'urgency_level', 'priority', 'requires_all']
    list_filter = ['urgency_level']
    filter_horizontal = ['symptoms']  # Nice widget for selecting symptoms

@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ['session_id', 'current_urgency', 'is_complete', 'created_at']
    list_filter = ['is_complete', 'current_urgency']

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['session', 'message_type', 'content_preview', 'timestamp']
    list_filter = ['message_type']
    
    def content_preview(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content

@admin.register(Disease)
class DiseaseAdmin(admin.ModelAdmin):
    list_display = ['name', 'urgency_level']
    list_filter = ['urgency_level']
    filter_horizontal = ['symptoms']
    search_fields = ['name', 'description']