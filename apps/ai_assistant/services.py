"""RAG-style context builder and OpenRouter client for the chat assistant.

All network access is confined to :func:`call_openrouter` so tests can patch it
(or rely on demo mode when ``OPENROUTER_API_KEY`` is empty). Nothing here calls
the API implicitly.
"""

import logging
import textwrap

import requests
from django.conf import settings
from django.core.cache import cache
from django.urls import reverse

logger = logging.getLogger(__name__)

CONTEXT_CACHE_KEY = "ai_assistant:context"
CONTEXT_CACHE_TTL = 300  # 5 minutes

# Circuit breaker: after an auth/payment rejection (401/402/403) we stop calling
# OpenRouter for a while instead of hammering a known-bad key.
CACHE_KEY_OPENROUTER_DISABLED = "openrouter:disabled_until"
DISABLE_DURATION_SECONDS = 3600  # 1 hour

# Per-field truncation limits applied when building the context string so
# unbounded TextFields cannot blow up the prompt.
FIELD_LIMITS = {"description": 500, "body": 500, "excerpt": 200}


class OpenRouterError(Exception):
    """Raised when the OpenRouter API returns a non-2xx response."""


class OpenRouterDisabled(OpenRouterError):
    """OpenRouter is temporarily disabled after a recent API rejection."""


def _shorten(value, field: str) -> str:
    limit = FIELD_LIMITS.get(field, 500)
    value = (value or "").strip()
    if len(value) <= limit:
        return value
    return textwrap.shorten(value, width=limit, placeholder="…")


def _invalidate_context_cache(sender, **kwargs):
    cache.delete(CONTEXT_CACHE_KEY)


def build_context() -> str:
    """Combine every live portfolio row into a single context string."""
    from apps.blog.models import Post
    from apps.certifications.models import Certification
    from apps.experience.models import Experience
    from apps.projects.models import Project
    from apps.skills.models import Category

    lines = []

    projects = list(Project.objects.all())
    if projects:
        lines.append("PROJECTS:")
        for p in projects:
            tags = ", ".join(p.tags_list) or "—"
            lines.append(
                f"- {p.title} ({p.get_absolute_url()}): {p.summary}. Tags: {tags}"
            )

    for cat in Category.objects.prefetch_related("skills").all():
        skills = list(cat.skills.all())
        if not skills:
            continue
        lines.append(f"SKILLS — {cat.name}:")
        lines.append(", ".join(f"{s.name} ({s.level_display})" for s in skills))

    experience = list(Experience.objects.all())
    if experience:
        lines.append("EXPERIENCE:")
        for e in experience:
            lines.append(
                f"- {e.title} at {e.organization} ({e.date_range}): "
                f"{_shorten(e.description, 'description')}"
            )

    certs = list(Certification.objects.all())
    if certs:
        lines.append("CERTIFICATIONS:")
        cert_list_url = reverse("certifications:list")
        for c in certs:
            lines.append(
                f"- {c.name} — {c.issuer} ({c.date_display}); list: {cert_list_url}"
            )

    posts = list(Post.published.all())
    if posts:
        lines.append("BLOG POSTS:")
        for post in posts:
            lines.append(
                f"- {post.title} ({post.get_absolute_url()}): "
                f"{_shorten(post.excerpt, 'excerpt')} {_shorten(post.body, 'body')}"
            )

    return "\n".join(lines)


def get_context() -> str:
    """Return the cached context, rebuilding after 5 minutes."""
    cached = cache.get(CONTEXT_CACHE_KEY)
    if cached is not None:
        return cached
    context = build_context()
    cache.set(CONTEXT_CACHE_KEY, context, CONTEXT_CACHE_TTL)
    return context


def source_links() -> list:
    """Structured list of URLs the visitor can jump to."""
    from apps.blog.models import Post
    from apps.projects.models import Project

    sources = []
    for p in Project.objects.all():
        sources.append({"title": p.title, "url": p.get_absolute_url()})
    for post in Post.published.all():
        sources.append({"title": post.title, "url": post.get_absolute_url()})
    if sources:
        sources.append(
            {"title": "Certifications", "url": reverse("certifications:list")}
        )
    return sources


def system_prompt() -> str:
    return (
        "You are Alfonso's portfolio AI assistant. Answer ONLY from the supplied "
        "context. If unknown, say so. Always cite sources by their URL when possible. "
        "Be concise."
    )


def demo_mode_answer_no_key() -> str:
    return (
        "The AI assistant is in demo mode because no OpenRouter API key "
        "is configured. Set OPENROUTER_API_KEY in the environment to "
        "enable real answers."
    )


def demo_mode_answer_rejected() -> str:
    return (
        "The AI assistant is in demo mode because the configured "
        "OPENROUTER_API_KEY is being rejected by the API (likely invalid "
        "or out of balance). Verify the key and its balance, then wait an "
        "hour or clear the openrouter:disabled_until cache key."
    )


def demo_mode_answer() -> str:
    # Backwards-compatible alias: "no key configured" demo-mode message.
    return demo_mode_answer_no_key()


def call_openrouter(messages, *, stream=False) -> str:
    """POST to the OpenRouter chat completions endpoint and return the answer text.

    Raises :class:`OpenRouterError` on any non-2xx response, or
    :class:`OpenRouterDisabled` if the circuit breaker is open (a recent
    401/402/403). Callers must either provide a key or use demo mode (see views).
    """
    if cache.get(CACHE_KEY_OPENROUTER_DISABLED):
        raise OpenRouterDisabled("OpenRouter disabled after a recent API rejection")

    api_key = getattr(settings, "OPENROUTER_API_KEY", "")
    if not api_key:
        raise OpenRouterError(
            "OPENROUTER_API_KEY is not set; refusing to call the API."
        )

    response = requests.post(
        f"{settings.OPENROUTER_BASE_URL}/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": settings.OPENROUTER_MODEL,
            "messages": messages,
            "stream": stream,
        },
        timeout=30,
    )
    if not response.ok:  # covers all 4xx and 5xx
        if response.status_code in (401, 402, 403):
            cache.set(
                CACHE_KEY_OPENROUTER_DISABLED,
                "1",
                DISABLE_DURATION_SECONDS,
            )
        raise OpenRouterError(
            f"openrouter {response.status_code}: {response.text[:300]}"
        )
    data = response.json()
    return data["choices"][0]["message"]["content"]
