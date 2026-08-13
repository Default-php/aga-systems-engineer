from django.contrib import admin

from apps.ai_assistant.models import ChatMessage


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("session_key", "user_message", "created_at")
    search_fields = ("session_key", "user_message")
    readonly_fields = ("session_key", "user_message", "assistant_reply", "created_at")
