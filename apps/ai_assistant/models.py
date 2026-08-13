from django.db import models


class ChatMessage(models.Model):
    session_key = models.CharField(max_length=100)
    user_message = models.TextField()
    assistant_reply = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.session_key}: {self.user_message[:50]}"
