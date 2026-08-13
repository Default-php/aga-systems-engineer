import importlib
import os

_default = "config.settings.development"
__all__ = list({"development", "production"})

if os.environ.get("DJANGO_SETTINGS_MODULE") in (None, "config.settings"):
    # setdefault would NOT override an explicit "config.settings" value, which
    # would then re-import this partially-initialized package (empty re-export).
    os.environ["DJANGO_SETTINGS_MODULE"] = _default
else:
    # Honor explicit override (CI / production / etc.)
    pass

# Re-export the chosen module's attributes so django.conf can import it.
_settings_module = os.environ["DJANGO_SETTINGS_MODULE"]
_module = importlib.import_module(_settings_module)
globals().update({k: v for k, v in vars(_module).items() if not k.startswith("_")})
