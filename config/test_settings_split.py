"""Regression tests for the settings-module split (task 4.1).

Each test runs a fresh interpreter in a hermetic temp copy of the repo
(without the local ``.env``) so the auto-default and fail-closed behavior
is independent of the developer's environment.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class TestSettingsSplit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._tmp = tempfile.mkdtemp(prefix="portfolio-settings-")
        tmp = Path(cls._tmp)
        for name in ("config", "apps"):
            shutil.copytree(
                ROOT / name,
                tmp / name,
                ignore=shutil.ignore_patterns("__pycache__"),
            )

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._tmp, ignore_errors=True)
        super().tearDownClass()

    def _run(self, env_updates, code):
        env = dict(os.environ)
        env["PYTHONPATH"] = str(Path(self._tmp))
        for key in ("DJANGO_SETTINGS_MODULE", "SECRET_KEY", "DATABASE_URL"):
            env.pop(key, None)
        env.update(env_updates)
        return subprocess.run(
            [sys.executable, "-c", code],
            env=env,
            capture_output=True,
            text=True,
            cwd=Path(self._tmp),
            timeout=60,
        )

    def test_default_settings_module_picks_development_when_unset_or_legacy(self):
        result = self._run(
            {},
            "import config.settings, django; django.setup(); "
            "from django.conf import settings; "
            "print(settings.DEBUG, settings.DATABASES['default']['ENGINE'])",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("True django.db.backends.sqlite3", result.stdout)

    def test_explicit_development_module_loads(self):
        result = self._run(
            {"DJANGO_SETTINGS_MODULE": "config.settings.development"},
            "import django; django.setup(); "
            "from django.conf import settings; "
            "print(settings.DEBUG, settings.DATABASES['default']['ENGINE'])",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("True django.db.backends.sqlite3", result.stdout)

    def test_explicit_production_loads_with_env_required_vars(self):
        result = self._run(
            {
                "DJANGO_SETTINGS_MODULE": "config.settings.production",
                "SECRET_KEY": "x",
                "DATABASE_URL": "postgres://u:p@h:5432/db",
            },
            "import django; django.setup(); "
            "from django.conf import settings; "
            "from django.core.files.storage import default_storage; "
            "default_storage.base_location; "
            "print(settings.DEBUG, settings.DATABASES['default']['ENGINE'], "
            "sorted(settings.STORAGES), default_storage._wrapped.__class__.__name__)",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            "False django.db.backends.postgresql "
            "['default', 'staticfiles'] FileSystemStorage",
            result.stdout,
        )

    def test_production_fails_closed_without_database_url(self):
        result = self._run(
            {
                "DJANGO_SETTINGS_MODULE": "config.settings.production",
                "SECRET_KEY": "x",
            },
            "import django; django.setup()",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DATABASE_URL", result.stderr)

    def test_production_fails_closed_without_secret_key(self):
        result = self._run(
            {
                "DJANGO_SETTINGS_MODULE": "config.settings.production",
                "DATABASE_URL": "postgres://u:p@h:5432/db",
            },
            "import django; django.setup()",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SECRET_KEY", result.stderr)
