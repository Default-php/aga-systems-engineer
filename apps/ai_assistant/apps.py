from django.apps import AppConfig


class AiAssistantConfig(AppConfig):
    name = "apps.ai_assistant"

    def ready(self):
        from . import signals  # noqa: F401
