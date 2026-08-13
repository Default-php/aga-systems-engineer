from django.apps import AppConfig


class AiAssistantConfig(AppConfig):
    name = "apps.ai_assistant"

    def ready(self):
        from django.db.models.signals import post_delete, post_save

        from apps.ai_assistant import signals  # noqa: F401
        from apps.ai_assistant.constants import TRACKED_MODELS
        from apps.ai_assistant.services import _invalidate_context_cache

        for model in TRACKED_MODELS:
            post_save.connect(_invalidate_context_cache, sender=model)
            post_delete.connect(_invalidate_context_cache, sender=model)
