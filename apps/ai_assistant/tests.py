from datetime import date
from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.ai_assistant import services
from apps.ai_assistant.models import ChatMessage
from apps.blog.models import Post
from apps.experience.models import Experience
from apps.projects.models import Project
from apps.skills.models import Category, Skill


@override_settings(OPENROUTER_API_KEY="")
class ChatApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.project = Project.objects.create(
            title="Sample Project",
            slug="sample-project",
            summary="A sample project about Django.",
            tags_csv="Python, Django",
        )
        cls.category = Category.objects.create(name="Backend", slug="backend")
        Skill.objects.create(name="Django", category=cls.category, level=Skill.ADVANCED)
        cls.post = Post.objects.create(
            title="Sample Post",
            slug="sample-post",
            body="Post body.",
            is_draft=False,
            published_at=timezone.now(),
        )

    def setUp(self):
        cache.clear()

    def test_chat_api_requires_post_or_get_method(self):
        response = self.client.get("/chat/")
        self.assertEqual(response.status_code, 405)

    def test_chat_api_validates_empty_message(self):
        response = self.client.post(
            "/chat/", data={"message": ""}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_chat_api_validates_max_length(self):
        response = self.client.post(
            "/chat/", data={"message": "x" * 1000}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    @override_settings(OPENROUTER_API_KEY="")
    def test_chat_api_demo_mode_without_api_key(self):
        response = self.client.post(
            "/chat/", data={"message": "Hello"}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("demo mode", response.json()["answer"].lower())

    @patch("apps.ai_assistant.views.call_openrouter")
    def test_chat_api_calls_openrouter_with_context(self, mock_call):
        mock_call.return_value = "Mocked answer."
        with override_settings(OPENROUTER_API_KEY="test-key"):
            response = self.client.post(
                "/chat/",
                data={"message": "What projects have you done?"},
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["answer"], "Mocked answer.")
        mock_call.assert_called_once()
        args, kwargs = mock_call.call_args
        messages = args[0]
        self.assertEqual(messages[-1]["content"], "What projects have you done?")
        system_content = messages[0]["content"]
        self.assertIn("Sample Project", system_content)
        self.assertIn("Django", system_content)
        self.assertEqual(kwargs, {"stream": False})

    @patch("apps.ai_assistant.views.call_openrouter")
    def test_chat_persists_chatmessage(self, mock_call):
        mock_call.return_value = "Saved answer."
        with override_settings(OPENROUTER_API_KEY="test-key"):
            self.client.post(
                "/chat/",
                data={"message": "Persist me"},
                content_type="application/json",
            )
        self.assertEqual(ChatMessage.objects.count(), 1)
        message = ChatMessage.objects.get()
        self.assertEqual(message.user_message, "Persist me")
        self.assertEqual(message.assistant_reply, "Saved answer.")

    def test_chat_rate_limit_per_ip(self):
        cache.clear()
        payload = {"message": "Question"}
        last = None
        for _ in range(11):
            last = self.client.post(
                "/chat/", data=payload, content_type="application/json"
            )
        self.assertEqual(last.status_code, 429)

    def test_widget_renders_on_every_page(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="chat-widget"')
        self.assertContains(response, "data-chat-url")

    @patch("apps.ai_assistant.services.requests.post")
    def test_openrouter_call_format(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"choices": [{"message": {"content": "ok"}}]}
        mock_post.return_value = mock_resp

        messages = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "hello"},
        ]
        with override_settings(OPENROUTER_API_KEY="test-key"):
            services.call_openrouter(messages, stream=False)

        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        self.assertIn("Authorization", kwargs["headers"])
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(kwargs["json"]["model"], "openrouter/auto:free")
        self.assertEqual(kwargs["json"]["stream"], False)
        self.assertEqual(
            [m["role"] for m in kwargs["json"]["messages"]], ["system", "user"]
        )

    @patch("apps.ai_assistant.services.build_context", wraps=services.build_context)
    def test_cache_invalidation_on_model_save(self, mock_build):
        services.get_context()  # warms cache — build_context call #1
        self.assertIsNotNone(cache.get(services.CONTEXT_CACHE_KEY))
        project = Project.objects.first()
        project.save()  # post_save signal invalidates the cache
        self.assertIsNone(cache.get(services.CONTEXT_CACHE_KEY))
        services.get_context()  # rebuilds — build_context call #2
        self.assertEqual(mock_build.call_count, 2)

    @patch("apps.ai_assistant.services.build_context", wraps=services.build_context)
    def test_cache_invalidation_on_model_delete(self, mock_build):
        services.get_context()  # warms cache — build_context call #1
        project = Project.objects.first()
        project.delete()  # post_delete signal invalidates the cache
        self.assertIsNone(cache.get(services.CONTEXT_CACHE_KEY))
        services.get_context()  # rebuilds — build_context call #2
        self.assertEqual(mock_build.call_count, 2)

    def test_context_truncation_bounds(self):
        long_desc = "D" * 2000
        Experience.objects.create(
            title="Truncated Role",
            organization="Some Co",
            start_date=date(2020, 1, 1),
            description=long_desc,
        )
        context = services.build_context()
        self.assertIn("…", context)
        self.assertNotIn(long_desc, context)
        # A 2000-char description is bounded to ~500 + ellipsis, so the whole
        # context stays small even with the other fixtures present.
        self.assertLess(len(context), 1000)

    def test_rate_limit_uses_remote_addr_not_xff(self):
        cache.clear()
        last = None
        # Different XFF values each time — if XFF were honored, each would be a
        # fresh bucket and the limit would never fire; it still fires after 10
        # because REMOTE_ADDR (127.0.0.1) drives the counter.
        for i in range(11):
            last = self.client.post(
                "/chat/",
                data={"message": "Q"},
                content_type="application/json",
                HTTP_X_FORWARDED_FOR=f"1.2.3.{i}",
            )
        self.assertEqual(last.status_code, 429)

    @patch("apps.ai_assistant.services.requests.post")
    def test_call_openrouter_raises_on_non_2xx(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.ok = False
        mock_resp.status_code = 429
        mock_resp.text = "rate limited"
        mock_post.return_value = mock_resp
        with override_settings(OPENROUTER_API_KEY="test-key"):
            with self.assertRaises(services.OpenRouterError) as ctx:
                services.call_openrouter(
                    [{"role": "user", "content": "hi"}], stream=False
                )
        self.assertIn("429", str(ctx.exception))

    @patch("apps.ai_assistant.services.requests.post")
    def test_call_openrouter_returns_message_content(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "Hello from the model."}}]
        }
        mock_post.return_value = mock_resp
        with override_settings(OPENROUTER_API_KEY="test-key"):
            result = services.call_openrouter(
                [{"role": "user", "content": "hi"}], stream=False
            )
        self.assertEqual(result, "Hello from the model.")
