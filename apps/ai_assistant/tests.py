from datetime import date
from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.ai_assistant import services
from apps.ai_assistant.models import ChatMessage
from apps.ai_assistant.services import extract_cited_sources
from apps.blog.models import Post
from apps.certifications.models import Certification
from apps.experience.models import Experience
from apps.projects.models import Project
from apps.skills.models import Category, Skill


class AnswerCitationExtractionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # One project with a known URL; one cert with an absolute credential_url.
        cls.project = Project.objects.create(
            title="My Project",
            slug="my-project",
            summary="A project",
        )
        cls.cert = Certification.objects.create(
            name="My Cert",
            issuer="ACME",
            date_obtained="2024-01-01",
            credential_url="https://acme.test/verify/xyz",
        )

    def test_markdown_link_is_extracted(self):
        url = self.project.get_absolute_url()
        answer = f"This is described in [My Project]({url})."
        sources = extract_cited_sources(answer)
        self.assertEqual(sources, [{"title": "My Project", "url": url}])

    def test_bare_path_is_extracted(self):
        url = self.project.get_absolute_url()
        answer = f"See {url} for details."
        sources = extract_cited_sources(answer)
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0]["url"], url)

    def test_bare_absolute_url_is_extracted(self):
        url = self.cert.credential_url
        answer = f"Verify at {url}."
        sources = extract_cited_sources(answer)
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0]["url"], url)

    def test_unknown_url_is_dropped(self):
        # URL not in the source_links list.
        answer = "External link: [spammy](https://spammy.example/path)."
        sources = extract_cited_sources(answer)
        self.assertEqual(sources, [])

    def test_deduplication_across_markdown_and_bare(self):
        url = self.project.get_absolute_url()
        answer = f"Both [link]({url}) and bare {url} appear."
        sources = extract_cited_sources(answer)
        self.assertEqual(len(sources), 1, "duplicate citations must be deduped")

    def test_multiple_distinct_citations(self):
        url_a = self.project.get_absolute_url()
        url_b = self.cert.credential_url
        answer = f"See [project]({url_a}) and verify at {url_b}."
        sources = extract_cited_sources(answer)
        self.assertEqual(len(sources), 2)
        # Order is preserved (markdown first, then bare URL).
        self.assertEqual(sources[0]["url"], url_a)
        self.assertEqual(sources[1]["url"], url_b)

    def test_citations_in_appearance_order(self):
        """Markdown link after bare URL — citations returned in document order."""
        url = self.project.get_absolute_url()
        cert_url = self.cert.credential_url
        answer = f"First bare {url} then [Cert]({cert_url})."
        sources = extract_cited_sources(answer)
        self.assertEqual(len(sources), 2)
        self.assertEqual(
            sources[0]["url"], url, "bare URL first in answer must come first"
        )
        self.assertEqual(sources[1]["url"], cert_url)

    def test_trailing_delimiters_stripped(self):
        """Each trailing-delimiter variant is asserted independently."""
        url = self.project.get_absolute_url()
        cases = [
            ("period", f"See {url}."),
            ("comma", f"Or {url},"),
            ("single-quotes", f"'{url}'"),
            ("backticks", f"`{url}`"),
            ("semicolon", f"{url};"),
            ("colon", f"{url}:"),
            ("exclamation", f"{url}!"),
            ("question", f"{url}?"),
            (
                "closing-brace",
                f"end {url}}}",
            ),  # URL immediately followed by }; rstrip must remove it
        ]
        for label, text in cases:
            with self.subTest(case=label):
                sources = extract_cited_sources(text)
                self.assertEqual(
                    len(sources),
                    1,
                    f"case {label!r}: expected 1 source, got {sources!r}",
                )
                self.assertEqual(
                    sources[0]["url"],
                    url,
                    f"case {label!r}: trailing delimiter not stripped",
                )


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

    @override_settings(OPENROUTER_MODEL="openrouter/auto:free")
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
        long_desc = "word " * 400  # ~2000 chars, whitespace-separated
        fixture_exp = Experience.objects.create(
            title="Truncated Role",
            organization="Some Co",
            start_date=date(2020, 1, 1),
            description=long_desc,
        )
        ctx = services.build_context()
        # Locate the fixture's experience line in the context.
        marker = f"- {fixture_exp.title} at {fixture_exp.organization}"
        i = ctx.find(marker)
        self.assertNotEqual(i, -1, "context missing the fixture experience")
        seg = ctx[i:]
        desc_start = seg.find(": ")
        desc_text = (
            seg[desc_start + 2 :].split("\n")[0]  # noqa: E203 (black slice style)
            if desc_start != -1
            else ""
        )
        # Pinned to the FIELD_LIMITS bound (+ ellipsis + small slack), so a
        # degenerate "…"-only truncation would NOT pass.
        self.assertLessEqual(
            len(desc_text),
            services.FIELD_LIMITS["description"] + len("…") + 1,
            f"description not truncated to <= 500 chars: {len(desc_text)}",
        )
        # Truncation actually happened — the ellipsis is present.
        self.assertIn("…", desc_text)
        # The full 2000-char fixture string must not appear verbatim.
        self.assertNotIn(long_desc, ctx)

    def test_rate_limit_uses_remote_addr_not_xff(self):
        cache.clear()
        last = None
        # REMOTE_ADDR is pinned to 9.9.9.9 while the spoofable XFF value varies
        # each request — if the limiter keyed on XFF, each request would be a
        # fresh bucket and the limit would never fire. It fires after 10, which
        # proves the counter is keyed on REMOTE_ADDR.
        for i in range(11):
            last = self.client.post(
                "/chat/",
                data={"message": "Q"},
                content_type="application/json",
                REMOTE_ADDR="9.9.9.9",
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


class ChatApiFallbackTests(TestCase):
    @override_settings(OPENROUTER_API_KEY="sk-fake-but-set")
    @patch("apps.ai_assistant.views.call_openrouter")
    def test_view_returns_200_with_friendly_message_on_openrouter_error(
        self, mock_call
    ):
        mock_call.side_effect = services.OpenRouterError("openrouter 401: anything")
        resp = self.client.post(
            reverse("ai_assistant:chat_api"),
            data='{"message": "Hello"}',
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("answer", body)
        # Friendly fallback, not the raw exception text.
        self.assertNotIn("openrouter", body["answer"].lower())
        self.assertNotIn("401", body["answer"])
        self.assertTrue(
            "unavailable" in body["answer"].lower()
            or "try again" in body["answer"].lower(),
            f"answer was: {body['answer']!r}",
        )


class CircuitBreakerTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_circuit_breaker_locks_out_after_401(self):
        with (
            override_settings(OPENROUTER_API_KEY="sk-fake"),
            patch("apps.ai_assistant.services.requests.post") as mock_post,
        ):
            mock_post.return_value = MagicMock(
                ok=False, status_code=401, text='{"error":"User not found.","code":401}'
            )
            # First call: raises OpenRouterError, breaker activates.
            with self.assertRaises(services.OpenRouterError):
                services.call_openrouter([{"role": "user", "content": "hi"}])
            # Second call: should NOT call requests.post — short-circuits.
            mock_post.reset_mock()
            with self.assertRaises(services.OpenRouterDisabled):
                services.call_openrouter([{"role": "user", "content": "hi"}])
            mock_post.assert_not_called()
        cache.clear()

    def test_circuit_breaker_does_not_trigger_on_500(self):
        with (
            override_settings(OPENROUTER_API_KEY="sk-fake"),
            patch("apps.ai_assistant.services.requests.post") as mock_post,
        ):
            mock_post.return_value = MagicMock(
                ok=False, status_code=500, text="server error"
            )
            with self.assertRaises(services.OpenRouterError):
                services.call_openrouter([{"role": "user", "content": "hi"}])
            # 500 does not open the breaker — a second call still hits the API.
            mock_post.reset_mock()
            with self.assertRaises(services.OpenRouterError):
                services.call_openrouter([{"role": "user", "content": "hi"}])
            mock_post.assert_called_once()
        cache.clear()


class ChatApiDemoModeTests(TestCase):
    @override_settings(OPENROUTER_API_KEY="sk-fake-but-set")
    @patch("apps.ai_assistant.views.call_openrouter")
    def test_view_returns_demo_mode_rejected_when_openrouter_disabled(
        self,
        mock_call,
    ):
        mock_call.side_effect = services.OpenRouterDisabled(
            "OpenRouter disabled after a recent API rejection"
        )
        resp = self.client.post(
            reverse("ai_assistant:chat_api"),
            data='{"message": "Hello"}',
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("answer", body)
        # Specific demo-mode-rejected phrase (NOT the generic "unavailable" text).
        self.assertIn("rejected", body["answer"].lower())
        self.assertNotIn("openrouter 401", body["answer"].lower())


class ContextBuilderTests(TestCase):
    """Direct unit tests for build_context()/source_links() assembly."""

    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name="Backend", slug="backend")
        cls.project = Project.objects.create(
            title="Period Project",
            slug="period-project",
            summary="Built with Django and Postgres.",
            tags_csv="",
        )
        cls.cert_with_url = Certification.objects.create(
            name="AWS Certified",
            issuer="Amazon",
            date_obtained=date(2023, 5, 1),
            credential_url="https://example.com/verify/abc",
        )
        cls.cert_without_url = Certification.objects.create(
            name="No URL Cert",
            issuer="Some Org",
            date_obtained=date(2022, 5, 1),
            credential_url="",
        )

    def test_build_context_no_double_period_after_summary_ending_in_period(self):
        ctx = services.build_context()
        line = next(
            line
            for line in ctx.splitlines()
            if line.startswith(f"- {self.project.title} (")
        )
        self.assertNotIn("..", line)
        self.assertIn("Built with Django and Postgres. Tags:", line)

    def test_source_links_includes_per_cert_credential_url(self):
        sources = services.source_links()
        by_title = {s["title"]: s["url"] for s in sources}
        self.assertEqual(by_title["AWS Certified"], "https://example.com/verify/abc")
        self.assertEqual(by_title["No URL Cert"], reverse("certifications:list"))

    def test_source_links_empty_when_no_projects_posts_or_certifications(self):
        # Empty-DB scenario: delete all projects/posts/certs. Skills/experience
        # remain but are never source entries.
        Project.objects.all().delete()
        Post.objects.all().delete()
        Certification.objects.all().delete()
        self.assertEqual(services.source_links(), [])


class ContextRowCapTests(TestCase):
    """build_context() must cap each section's row count (A4)."""

    @classmethod
    def setUpTestData(cls):
        Project.objects.bulk_create(
            Project(
                title=f"Cap Project {i}",
                slug=f"cap-project-{i}",
                summary="short",
            )
            for i in range(7)
        )
        Post.objects.bulk_create(
            Post(
                title=f"Cap Post {i}",
                slug=f"cap-post-{i}",
                body="body",
                is_draft=False,
                published_at=timezone.now(),
            )
            for i in range(7)
        )
        Experience.objects.bulk_create(
            Experience(
                title=f"Cap Role {i}",
                organization="Org",
                start_date=date(2020 + i, 1, 1),
            )
            for i in range(11)
        )
        Certification.objects.bulk_create(
            Certification(
                name=f"Cap Cert {i}",
                issuer="Issuer",
                date_obtained=date(2020 + i, 1, 1),
            )
            for i in range(21)
        )

    @staticmethod
    def _section_lines(ctx: str, header: str) -> list:
        """Lines starting with '- ' that belong to the named context section."""
        lines = ctx.splitlines()
        try:
            start = lines.index(header)
        except ValueError:
            return []
        section = []
        for line in lines[start + 1 :]:  # noqa: E203 (black slice style)
            if line.startswith("- "):
                section.append(line)
            elif line:
                break  # next section header
        return section

    def test_build_context_caps_projects(self):
        ctx = services.build_context()
        self.assertEqual(
            len(self._section_lines(ctx, "PROJECTS:")),
            services.MAX_PROJECT_ROWS,
        )

    def test_build_context_caps_posts(self):
        ctx = services.build_context()
        self.assertEqual(
            len(self._section_lines(ctx, "BLOG POSTS:")),
            services.MAX_BLOG_ROWS,
        )

    def test_build_context_caps_experience(self):
        ctx = services.build_context()
        self.assertEqual(
            len(self._section_lines(ctx, "EXPERIENCE:")),
            services.MAX_EXPERIENCE_ROWS,
        )

    def test_build_context_caps_certifications(self):
        ctx = services.build_context()
        self.assertEqual(
            len(self._section_lines(ctx, "CERTIFICATIONS:")),
            services.MAX_CERTIFICATION_ROWS,
        )

    def test_projects_ordered_featured_first(self):
        # Create 6 projects: 3 featured, 3 not; varied display_orders so the
        # natural insertion order differs from the desired order.
        Project.objects.all().delete()
        Project.objects.create(
            title="Featured-A",
            slug="f-a",
            summary="A",
            featured=True,
            display_order=10,
        )
        Project.objects.create(
            title="NotFeatured-A",
            slug="nf-a",
            summary="A",
            featured=False,
            display_order=0,
        )
        Project.objects.create(
            title="Featured-B",
            slug="f-b",
            summary="B",
            featured=True,
            display_order=5,
        )
        Project.objects.create(
            title="NotFeatured-B",
            slug="nf-b",
            summary="B",
            featured=False,
            display_order=1,
        )
        Project.objects.create(
            title="Featured-C",
            slug="f-c",
            summary="C",
            featured=True,
            display_order=1,
        )
        Project.objects.create(
            title="NotFeatured-C",
            slug="nf-c",
            summary="C",
            featured=False,
            display_order=2,
        )
        # Cap = 5 → top 5 from ("-featured", "display_order", "-created_at"):
        # featured rows first (all featured=true), then display_order asc.
        # Within featured: (F-C,1),(F-B,5),(F-A,10). The top-5 cap covers all 3
        # featured + 2 of 3 non-featured.
        ctx = services.build_context()
        section = self._section_lines(ctx, "PROJECTS:")
        # 5 lines (cap).
        self.assertEqual(len(section), 5)
        # First three lines are featured, ordered by display_order asc.
        first_three = [line.split(" (")[0] for line in section[:3]]
        self.assertEqual(first_three, ["- Featured-C", "- Featured-B", "- Featured-A"])
        # Last two are non-featured (display_order asc: NF-A(0), NF-B(1)).
        last_two_titles = [line.split(" (")[0] for line in section[3:]]
        self.assertEqual(last_two_titles, ["- NotFeatured-A", "- NotFeatured-B"])


class CategoryCacheInvalidationTests(TestCase):
    """A3 — Category saves/deletes must invalidate the context cache."""

    @classmethod
    def setUpTestData(cls):
        cls.cat = Category.objects.create(
            name="Backend", slug="backend", display_order=0
        )
        Skill.objects.create(name="Django", category=cls.cat, level="advanced")
        cls.cat.refresh_from_db()

    def test_category_save_invalidates_context_cache(self):
        cache.set(services.CONTEXT_CACHE_KEY, "warm", 300)
        self.cat.name = "Backend & Platform"
        self.cat.save()
        self.assertIsNone(cache.get(services.CONTEXT_CACHE_KEY))

    def test_category_delete_invalidates_context_cache(self):
        cat = self.cat.__class__.objects.create(
            name="Frontend", slug="frontend", display_order=1
        )
        cache.set(services.CONTEXT_CACHE_KEY, "warm", 300)
        cat.delete()
        self.assertIsNone(cache.get(services.CONTEXT_CACHE_KEY))
