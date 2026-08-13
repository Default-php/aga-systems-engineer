# Signal handlers for chat-context cache invalidation. Per-model registration
# happens in AppConfig.ready(); this module re-exports the handler so tests can
# import it directly.
from apps.ai_assistant.services import _invalidate_context_cache  # noqa: F401
