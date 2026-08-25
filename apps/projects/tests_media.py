from importlib import reload
from pathlib import Path

from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import clear_url_caches


class MediaServingTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        # Only remove the test fixture — never wipe the whole MEDIA_ROOT
        # (that would delete media/.gitkeep and any real uploads).
        fixture = Path(settings.MEDIA_ROOT) / "test-fixture.bin"
        fixture.unlink(missing_ok=True)
        super().tearDownClass()

    def test_media_served_when_debug_true(self):
        media_dir = Path(settings.MEDIA_ROOT)
        media_dir.mkdir(parents=True, exist_ok=True)
        fixture = media_dir / "test-fixture.bin"
        fixture.write_bytes(b"hello-media")
        try:
            import config.urls as _urls

            with override_settings(DEBUG=True):
                # The test runner imports the URLconf with DEBUG=False, so the
                # dev-only media route is absent. Reload under DEBUG=True so the
                # `if settings.DEBUG:` gate behaves as it does in runserver.
                reload(_urls)
                clear_url_caches()
                resp = self.client.get(f"{settings.MEDIA_URL}test-fixture.bin")
                self.assertEqual(resp.status_code, 200)
                self.assertEqual(b"".join(resp.streaming_content), b"hello-media")
        finally:
            fixture.unlink(missing_ok=True)
            # Restore module state — reload with DEBUG=False to undo the
            # static() addition so no global state leaks into later tests.
            import config.urls as _urls

            with override_settings(DEBUG=False):
                reload(_urls)
            clear_url_caches()

    def test_media_not_served_when_debug_false(self):
        import config.urls as _urls

        with override_settings(DEBUG=False):
            reload(_urls)
            clear_url_caches()
            resp = self.client.get(f"{settings.MEDIA_URL}anything.png")
            self.assertEqual(resp.status_code, 404)
