"""Production settings — env-driven, security-hardened, Postgres, WhiteNoise."""

from .base import *  # noqa: F401,F403

SECRET_KEY = env("SECRET_KEY")  # required, no default
DEBUG = False
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["example.com"])

DATABASES = {
    "default": env.db("DATABASE_URL", default="postgres://postgres:postgres@db:5432/portfolio"),
}

# Static files via WhiteNoise (already in base.txt requirements).
# Django 6 uses STORAGES; STATICFILES_STORAGE is kept as a legacy alias.
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Append WhiteNoise middleware after SecurityMiddleware.
_MIDDLEWARE_BASE = list(MIDDLEWARE)
_MIDDLEWARE_BASE.insert(
    _MIDDLEWARE_BASE.index("django.middleware.security.SecurityMiddleware") + 1,
    "whitenoise.middleware.WhiteNoiseMiddleware",
)
MIDDLEWARE = _MIDDLEWARE_BASE

# Security
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30  # 30 days
SECURE_PROXY_SSL_HEADER = (
    ("HTTP_X_FORWARDED_PROTO", "https")
    if env.bool("SECURE_PROXY_SSL_HEADER_ENABLED", default=True)
    else None
)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# Email: SMTP if configured, else console.
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@example.com")
CONTACT_RECIPIENT_EMAIL = env("CONTACT_RECIPIENT_EMAIL", default="admin@example.com")
