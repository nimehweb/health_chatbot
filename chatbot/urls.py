from django.urls import path
from .views import start_chat, send_message, get_chat_history, list_symptoms

urlpatterns = [
    path('start/', start_chat),
    path('message/', send_message),
    path('history/<str:session_id>/', get_chat_history),
    path('symptoms/', list_symptoms),
]