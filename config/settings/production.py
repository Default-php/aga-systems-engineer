"""Production settings — env-driven, security-hardened, Postgres, WhiteNoise."""

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401,F403
from .base import MIDDLEWARE, env

SECRET_KEY = env("SECRET_KEY")  # required, no default
DEBUG = False
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["example.com"])

db_url = env("DATABASE_URL", default=None)
if not db_url:
    raise ImproperlyConfigured(
        "DATABASE_URL is required in production. Set it in the environment."
    )
# env.db_url_config parses a URL string directly; env.db() expects a var name.
DATABASES = {"default": env.db_url_config(db_url)}

# Static files via WhiteNoise (already in base.txt requirements).
# Include the default storage alias so default_storage (ImageField/FileField)
# keeps working. STATICFILES_STORAGE is intentionally unset — removed in Django 6.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

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
EMAIL_BACKEND = env(
    "EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@example.com")
CONTACT_RECIPIENT_EMAIL = env("CONTACT_RECIPIENT_EMAIL", default="admin@example.com")
