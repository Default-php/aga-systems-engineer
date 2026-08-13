"""RAG-style context builder and OpenRouter client for the chat assistant.

All network access is confined to :func:`call_openrouter` so tests can patch it
(or rely on demo mode when ``OPENROUTER_API_KEY`` is empty). Nothing here calls
the API implicitly.
"""

import logging

import requests
from django.conf import settings
from django.core.cache import cache
from django.urls import reverse

logger = logging.getLogger(__name__)

CONTEXT_CACHE_KEY = "ai_assistant:context"
CONTEXT_CACHE_TTL = 300  # 5 minutes


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
                f"- {e.title} at {e.organization} ({e.date_range}): {e.description}"
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
                f"{post.excerpt or ''} {post.body[:500]}"
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


def demo_mode_answer() -> str:
    return (
        "Demo mode: the chat assistant is wired up, but OPENROUTER_API_KEY is not "
        "set. Add it to your environment to enable real answers."
    )


def call_openrouter(messages, *, stream=False):
    """POST to the OpenRouter chat completions endpoint.

    Raises RuntimeError on non-2xx with a meaningful message. Callers must
    either provide a key or use demo mode (see views).
    """
    api_key = getattr(settings, "OPENROUTER_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set; refusing to call the API.")

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
    if response.status_code >= 400:
        raise RuntimeError(
            f"OpenRouter request failed: {response.status_code} {response.text[:200]}"
        )
    return response.json()
