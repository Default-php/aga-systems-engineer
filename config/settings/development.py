"""Development settings — DEBUG on, console email, SQLite."""

from .base import *  # noqa: F401,F403

DEBUG = True
SECRET_KEY = env("SECRET_KEY", default="dev-insecure-secret-replace-me")
ALLOWED_HOSTS = ["*"]  # dev only

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@example.com")
CONTACT_RECIPIENT_EMAIL = env("CONTACT_RECIPIENT_EMAIL", default="alfonso.ga@proton.me")
