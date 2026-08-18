import json
import logging

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from apps.ai_assistant import services
from apps.ai_assistant.constants import (
    MAX_MESSAGE_LENGTH,
    RATE_LIMIT_KEY,
    RATE_LIMIT_MAX,
    RATE_LIMIT_TTL,
)
from apps.ai_assistant.models import ChatMessage
from apps.ai_assistant.services import (
    OpenRouterDisabled,
    OpenRouterError,
    call_openrouter,
)

logger = logging.getLogger(__name__)


def _client_ip(request) -> str:
    # Behind a trusted TLS-terminating proxy (SECURE_PROXY_SSL_HEADER_ENABLED)
    # take the leftmost XFF value; otherwise trust the connection peer, which
    # is not spoofable by the client.
    if getattr(settings, "SECURE_PROXY_SSL_HEADER_ENABLED", False):
        xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
        return xff.split(",")[0].strip() or request.META.get("REMOTE_ADDR", "")
    return request.META.get("REMOTE_ADDR", "")


def _rate_limited(ip: str) -> bool:
    key = RATE_LIMIT_KEY.format(ip)
    count = services.cache.get(key, 0)
    if count >= RATE_LIMIT_MAX:
        return True
    services.cache.set(key, count + 1, RATE_LIMIT_TTL)
    return False


@require_POST
def chat_api(request):
    try:
        payload = json.loads(request.body or b"{}")
    except (ValueError, TypeError):
        return JsonResponse({"error": "Invalid JSON body."}, status=400)

    message = payload.get("message")
    if not isinstance(message, str) or not message.strip():
        return JsonResponse(
            {"error": "Message is required and cannot be empty."}, status=400
        )
    message = message.strip()
    if len(message) > MAX_MESSAGE_LENGTH:
        return JsonResponse(
            {"error": (f"Message must be {MAX_MESSAGE_LENGTH} characters or fewer.")},
            status=400,
        )

    ip = _client_ip(request)
    if _rate_limited(ip):
        return JsonResponse(
            {"error": "Rate limit exceeded. Please try again later."}, status=429
        )

    context = services.get_context()
    messages = [
        {
            "role": "system",
            "content": services.system_prompt() + "\n\nCONTEXT:\n" + context,
        },
        {"role": "user", "content": message},
    ]

    api_key = getattr(settings, "OPENROUTER_API_KEY", "")
    if not api_key:
        answer = services.demo_mode_answer()
    else:
        try:
            answer = call_openrouter(messages, stream=False)
        except OpenRouterDisabled:
            # Known-bad key (recent 401/402/403) — don't call the API again;
            # explain transparently instead of a generic error.
            logger.warning("OpenRouter disabled; serving demo-mode answer")
            answer = services.demo_mode_answer_rejected()
        except OpenRouterError:
            logger.exception("OpenRouter call failed")
            answer = (
                "Sorry, the assistant is temporarily unavailable. "
                "Please try again later."
            )
        except Exception:
            logger.exception("Unexpected error in chat")
            answer = (
                "Sorry, the assistant is temporarily unavailable. "
                "Please try again later."
            )

    sources = services.extract_cited_sources(answer)

    session_key = request.session.session_key or "anonymous"
    ChatMessage.objects.create(
        session_key=session_key,
        user_message=message,
        assistant_reply=answer,
    )

    return JsonResponse({"answer": answer, "sources": sources})
