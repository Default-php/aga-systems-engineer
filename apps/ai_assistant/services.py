"""RAG-style context builder and OpenRouter client for the chat assistant.

All network access is confined to :func:`call_openrouter` so tests can patch it
(or rely on demo mode when ``OPENROUTER_API_KEY`` is empty). Nothing here calls
the API implicitly.
"""

import logging
import re
import textwrap

import requests
from django.conf import settings
from django.core.cache import cache
from django.urls import reverse

from apps.ai_assistant.constants import (
    MAX_BLOG_ROWS,
    MAX_CERTIFICATION_ROWS,
    MAX_EXPERIENCE_ROWS,
    MAX_HISTORY_CHARS,
    MAX_HISTORY_TURNS,
    MAX_PROJECT_ROWS,
)

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

    projects = list(
        Project.objects.order_by("-featured", "display_order", "-created_at")[
            :MAX_PROJECT_ROWS
        ]
    )
    if projects:
        lines.append("PROJECTS:")
        for p in projects:
            tags = ", ".join(p.tags_list) or "—"
            summary = p.summary or ""
            period = "" if summary.rstrip().endswith((".", "!", "?")) else "."
            lines.append(
                f"- {p.title} ({p.get_absolute_url()}): {summary}{period} Tags: {tags}"
            )

    for cat in Category.objects.prefetch_related("skills").all():
        skills = list(cat.skills.all())
        if not skills:
            continue
        lines.append(f"SKILLS — {cat.name}:")
        lines.append(", ".join(f"{s.name} ({s.level_display})" for s in skills))

    experience = list(Experience.objects.all()[:MAX_EXPERIENCE_ROWS])
    if experience:
        lines.append("EXPERIENCE:")
        for e in experience:
            lines.append(
                f"- {e.title} at {e.organization} ({e.date_range}): "
                f"{_shorten(e.description, 'description')}"
            )

    certs = list(Certification.objects.all()[:MAX_CERTIFICATION_ROWS])
    if certs:
        lines.append("CERTIFICATIONS:")
        cert_list_url = reverse("certifications:list")
        for c in certs:
            lines.append(
                f"- {c.name} — {c.issuer} ({c.date_display}); list: {cert_list_url}"
            )

    posts = list(Post.published.all()[:MAX_BLOG_ROWS])
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


def history_messages(session_key: str) -> list[dict]:
    """Return the recent conversation history for `session_key` as a list of
    OpenAI-style message dicts (alternating user/assistant). Returns [] for
    anonymous sessions (defense against cross-user leakage via the shared
    "anonymous" bucket).
    """
    if not session_key or session_key == "anonymous":
        return []
    from apps.ai_assistant.models import ChatMessage

    # Pull the most recent N turns (each turn = 1 user + 1 assistant).
    # Fetch extra rows so we can assemble turns properly.
    rows = list(
        ChatMessage.objects.filter(session_key=session_key).order_by(
            "-created_at", "-pk"
        )[: MAX_HISTORY_TURNS * 2]
    )
    rows.reverse()  # oldest → newest
    # Keep only the most recent MAX_HISTORY_TURNS turns (each row is one turn).
    rows = rows[-MAX_HISTORY_TURNS:]
    out = []
    total = 0
    for row in rows:
        user = {"role": "user", "content": row.user_message}
        assistant = {"role": "assistant", "content": row.assistant_reply}
        projected = total + len(user["content"]) + len(assistant["content"])
        if projected > MAX_HISTORY_CHARS:
            # Skip turns larger than the cap rather than truncate
            # mid-message. `continue` (not `break`) preserves later
            # shorter turns that may still fit.
            continue
        out.append(user)
        out.append(assistant)
        total = projected
    return out


def source_links() -> list:
    """Structured list of URLs the visitor can jump to."""
    from apps.blog.models import Post
    from apps.certifications.models import Certification
    from apps.projects.models import Project

    sources = []
    for p in Project.objects.all():
        sources.append({"title": p.title, "url": p.get_absolute_url()})
    for post in Post.published.all():
        sources.append({"title": post.title, "url": post.get_absolute_url()})
    for c in Certification.objects.all():
        if c.credential_url:
            sources.append({"title": c.name, "url": c.credential_url})
        else:
            sources.append({"title": c.name, "url": reverse("certifications:list")})
    return sources


_CITE_RE = re.compile(
    # Markdown link: [text](url) where url is absolute or root-relative
    r"\[([^\]]*)\]\((https?://[^)\s]+|/[^\s)]+)\)"
    # or
    r"|"
    # Bare URL (with negative lookbehind to avoid eating parens/slashes around it)
    r"(?<![\(\w/])(https?://[^\s)\]]+|/[a-zA-Z][^\s)\]]*)"
)


def extract_cited_sources(answer: str) -> list[dict]:
    """Parse citations from the answer in document order, returning a
    deduplicated list of {"title": ..., "url": ...} for each citation that
    matches a known source URL.

    The canonical URL list is `source_links()`. Citations to URLs outside that
    list are silently dropped (don't expose external/internal URLs to the
    visitor).
    """
    known = {entry["url"]: entry["title"] for entry in source_links()}
    seen: set[str] = set()
    out: list[dict] = []
    for match in _CITE_RE.finditer(answer):
        if match.group(1) is not None:
            # Markdown link form
            url = match.group(2)
            title = match.group(1).strip() or known.get(url, "")
        else:
            # Bare URL form
            url = match.group(3)
            title = ""
        url = url.rstrip(".,;:!?)}\"'`")
        if url in known and url not in seen:
            seen.add(url)
            out.append({"title": title or known[url], "url": url})
    return out


def system_prompt() -> str:
    return (
        "You are Alfonso's portfolio AI assistant. Answer ONLY from the supplied "
        "CONTEXT. If the answer is not in the CONTEXT, say so explicitly. "
        "When you reference a project, post, certification, or section of the "
        "portfolio, cite its URL inline as a markdown link [Title](url) — use "
        "EXACTLY the URLs that appear in the CONTEXT (do not invent URLs). "
        "Keep the response concise. Match the user's language."
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
