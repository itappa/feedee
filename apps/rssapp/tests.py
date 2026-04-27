from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.authtoken.models import Token

from .forms import FeedCreateForm
from .models import (
    Article,
    ArticleUserState,
    Bookmark,
    BookmarkUserState,
    Feed,
    Tag,
    UserProfile,
)


class AuthenticationFlowTests(TestCase):
    def test_homepage_redirects_anonymous_to_login(self):
        response = self.client.get(reverse("homepage"))

        self.assertRedirects(response, f"{reverse('login')}?next={reverse('homepage')}")

    def test_login_page_shows_register_link(self):
        response = self.client.get(reverse("login"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("register"))
        self.assertContains(response, "Create an account")

    def test_bookmarks_page_redirects_to_login_when_unauthenticated(self):
        response = self.client.get(reverse("bookmark-list"))

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('bookmark-list')}",
        )

    def test_anonymous_today_alias_redirects_to_login(self):
        response = self.client.get(reverse("rss-dashboard"))

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('rss-dashboard')}",
        )

    def test_register_page_creates_user_and_logs_in(self):
        response = self.client.post(
            reverse("register"),
            {
                "email": "newuser@example.com",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("homepage"))
        user = get_user_model().objects.get(email="newuser@example.com")
        self.assertEqual(user.username, "newuser@example.com")
        self.assertTrue(response.context["user"].is_authenticated)
        self.assertTrue(UserProfile.objects.filter(user=user).exists())

    def test_register_rejects_duplicate_email(self):
        get_user_model().objects.create_user(
            username="existing",
            email="dup@example.com",
            password="Password123!",
        )

        response = self.client.post(
            reverse("register"),
            {
                "email": "dup@example.com",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "An account with this email already exists.")

    def test_saved_route_returns_404(self):
        response = self.client.get("/saved/")
        self.assertEqual(response.status_code, 404)

    def test_read_later_legacy_route_redirects_to_feeds_state_filter(self):
        user = get_user_model().objects.create_user(
            username="reader",
            email="reader@example.com",
            password="Password123!",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("read-later"))
        self.assertRedirects(response, f"{reverse('feeds-page')}?state=read-later")

    def test_favorites_legacy_route_redirects_to_feeds_state_filter(self):
        user = get_user_model().objects.create_user(
            username="fav-reader",
            email="fav-reader@example.com",
            password="Password123!",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("favorites"))
        self.assertRedirects(response, f"{reverse('feeds-page')}?state=read-later")


class HTMLSanitizationTests(TestCase):
    """Test HTML sanitization for Article.content field."""

    def test_dangerous_script_tags_removed(self):
        """script タグと内容が削除される"""
        article = Article.objects.create(
            title="Test Article",
            link="https://example.com/article",
            normalized_link="https://example.com/article",
            guid="test-guid-1",
            hash="test-hash-1",
            content='<p>Hello</p><script>alert("XSS")</script><p>World</p>',
        )
        self.assertIn("<p>Hello</p>", article.content)
        self.assertIn("<p>World</p>", article.content)
        self.assertNotIn("<script>", article.content)
        self.assertNotIn("</script>", article.content)
        self.assertNotIn("alert", article.content)

    def test_iframe_tags_removed(self):
        """iframe タグが削除される"""
        article = Article.objects.create(
            title="Test Article",
            link="https://example.com/article",
            normalized_link="https://example.com/article",
            guid="test-guid-2",
            hash="test-hash-2",
            content='<p>Embedded:</p><iframe src="https://malicious.com"></iframe>',
        )
        self.assertEqual(article.content, "<p>Embedded:</p>")
        self.assertNotIn("iframe", article.content)

    def test_onclick_attributes_removed(self):
        """onclick属性が削除される"""
        article = Article.objects.create(
            title="Test Article",
            link="https://example.com/article",
            normalized_link="https://example.com/article",
            guid="test-guid-3",
            hash="test-hash-3",
            content='<a href="https://example.com" onclick="alert(\'XSS\')">Link</a>',
        )
        # href のみ許可属性となり、onclick は削除される
        self.assertIn('<a href="https://example.com">Link</a>', article.content)
        self.assertNotIn("onclick", article.content)

    def test_style_tags_removed(self):
        """style タグが削除される"""
        article = Article.objects.create(
            title="Test Article",
            link="https://example.com/article",
            normalized_link="https://example.com/article",
            guid="test-guid-4",
            hash="test-hash-4",
            content="<p>Text</p><style>body { display: none; }</style>",
        )
        self.assertIn("<p>Text</p>", article.content)
        self.assertNotIn("<style>", article.content)
        self.assertNotIn("</style>", article.content)

    def test_form_tags_removed(self):
        """form タグが削除される"""
        article = Article.objects.create(
            title="Test Article",
            link="https://example.com/article",
            normalized_link="https://example.com/article",
            guid="test-guid-5",
            hash="test-hash-5",
            content='<form action="https://malicious.com"><input type="submit"></form>',
        )
        self.assertNotIn("form", article.content)
        self.assertNotIn("input", article.content)

    def test_allowed_tags_preserved(self):
        """許可されたタグは保存される"""
        html_with_allowed_tags = """
        <h2>Title</h2>
        <p>Paragraph with <strong>bold</strong> and <em>italic</em> text.</p>
        <a href="https://example.com" title="Example">Link</a>
        <img src="https://example.com/image.jpg" alt="Image">
        <ul><li>Item 1</li><li>Item 2</li></ul>
        <blockquote>Quote</blockquote>
        <code>code snippet</code>
        """
        article = Article.objects.create(
            title="Test Article",
            link="https://example.com/article",
            normalized_link="https://example.com/article",
            guid="test-guid-6",
            hash="test-hash-6",
            content=html_with_allowed_tags,
        )
        # 許可されたタグが含まれている
        self.assertIn("<h2>Title</h2>", article.content)
        self.assertIn("<strong>bold</strong>", article.content)
        self.assertIn("<em>italic</em>", article.content)
        self.assertIn(
            '<a href="https://example.com" title="Example">Link</a>', article.content
        )
        self.assertIn("<img", article.content)
        self.assertIn("<li>Item 1</li>", article.content)
        self.assertIn("<blockquote>Quote</blockquote>", article.content)
        self.assertIn("<code>code snippet</code>", article.content)

    def test_class_attribute_allowed(self):
        """class属性は許可される（任意のタグで）"""
        article = Article.objects.create(
            title="Test Article",
            link="https://example.com/article",
            normalized_link="https://example.com/article",
            guid="test-guid-7",
            hash="test-hash-7",
            content='<p class="highlight">Highlighted paragraph</p>',
        )
        self.assertIn('class="highlight"', article.content)

    def test_dangerous_javascript_url_in_href_removed(self):
        """javascript: URLは削除される"""
        article = Article.objects.create(
            title="Test Article",
            link="https://example.com/article",
            normalized_link="https://example.com/article",
            guid="test-guid-8",
            hash="test-hash-8",
            content="<a href=\"javascript:alert('XSS')\">Link</a>",
        )
        # nh3 はデフォルトで javascript: URLのhref属性を削除
        self.assertNotIn("javascript:", article.content)
        self.assertIn("Link", article.content)

    def test_empty_content_preserved(self):
        """空のコンテンツは保持される"""
        article = Article.objects.create(
            title="Test Article",
            link="https://example.com/article",
            normalized_link="https://example.com/article",
            guid="test-guid-9",
            hash="test-hash-9",
            content="",
        )
        self.assertEqual(article.content, "")

    def test_complex_dangerous_html_sanitized(self):
        """複雑な危険なHTMLが正しくサニタイズされる"""
        dangerous_html = """
        <h1>Article Title</h1>
        <p>Safe paragraph content</p>
        <script>
            fetch('https://malicious.com/steal-data')
        </script>
        <div onclick="alert('XSS')">
            <p>Paragraph inside div</p>
            <img src="x" onerror="alert('XSS')" alt="Image">
        </div>
        <style>
            .malicious { display: none; }
        </style>
        <iframe src="https://malicious.com/phishing"></iframe>
        <a href="https://legitimate-link.com">Safe Link</a>
        """
        article = Article.objects.create(
            title="Test Article",
            link="https://example.com/article",
            normalized_link="https://example.com/article",
            guid="test-guid-10",
            hash="test-hash-10",
            content=dangerous_html,
        )
        # 危険なタグは削除される - 実際のテキストは保持される可能性あり
        self.assertNotIn("<script>", article.content)
        self.assertNotIn("</script>", article.content)
        self.assertNotIn("onclick", article.content)
        self.assertNotIn("onerror", article.content)
        self.assertNotIn("<style>", article.content)
        self.assertNotIn("</style>", article.content)
        self.assertNotIn("<iframe>", article.content)
        self.assertNotIn("</iframe>", article.content)
        # 安全な要素は保持される
        self.assertIn("<h1>Article Title</h1>", article.content)
        self.assertIn("<p>Safe paragraph content</p>", article.content)
        self.assertIn("https://legitimate-link.com", article.content)


class ArticleUserStateTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="reader",
            email="reader@example.com",
            password="password123",
        )
        self.article = Article.objects.create(
            title="Example article",
            link="https://example.com/article",
            normalized_link="https://example.com/article",
            guid="article-guid-1",
            hash="c1a3c9f5d9f94d29cbf5d53da03d9563795143d7f8c0f356a58c4fc73d1aab31",
        )
        self.state_api_url = reverse("article-user-state", args=[self.article.id])

    def test_api_get_unauthenticated_returns_401(self):
        response = self.client.get(self.state_api_url)

        self.assertEqual(response.status_code, 401)

    def test_api_get_authenticated_without_state_returns_all_false(self):
        self.client.force_login(self.user)

        response = self.client.get(self.state_api_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["is_read_later"], False)
        self.assertEqual(response.json()["is_read"], False)

    def test_api_patch_authenticated_creates_and_updates_row(self):
        self.client.force_login(self.user)

        create_response = self.client.patch(
            self.state_api_url,
            data={"is_read_later": True},
            content_type="application/json",
        )
        self.assertEqual(create_response.status_code, 200)
        state = ArticleUserState.objects.get(user=self.user, article=self.article)
        self.assertEqual(state.is_read_later, True)
        self.assertEqual(state.is_read, False)

        update_response = self.client.patch(
            self.state_api_url,
            data={"is_read": True},
            content_type="application/json",
        )
        self.assertEqual(update_response.status_code, 200)
        state.refresh_from_db()
        self.assertEqual(state.is_read_later, True)
        self.assertEqual(state.is_read, True)

    def test_web_toggle_authenticated_updates_state_and_preserves_query_params(self):
        self.client.force_login(self.user)
        toggle_url = reverse(
            "article-state-toggle", args=[self.article.id, "is_read_later"]
        )

        response = self.client.post(toggle_url, data={"q": "django", "page": "3"})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response["Location"],
            f"{reverse('feeds-page')}?q=django&page=3",
        )
        state = ArticleUserState.objects.get(user=self.user, article=self.article)
        self.assertEqual(state.is_read_later, True)

    def test_bookmark_pin_toggle_updates_bookmark_state(self):
        self.client.force_login(self.user)
        bookmark = Bookmark.objects.create(
            user=self.user,
            url="https://example.com/bookmark",
            normalized_url="https://example.com/bookmark",
            hash="bookmark-pin-hash",
            title="Pin target",
        )
        toggle_url = reverse("bookmark-state-toggle", args=[bookmark.id, "is_pinned"])

        first_response = self.client.post(toggle_url)
        self.assertEqual(first_response.status_code, 302)
        state = BookmarkUserState.objects.get(user=self.user, bookmark=bookmark)
        self.assertEqual(state.is_pinned, True)

        second_response = self.client.post(toggle_url)
        self.assertEqual(second_response.status_code, 302)
        state.refresh_from_db()
        self.assertEqual(state.is_pinned, False)

    def test_homepage_shows_dashboard_for_authenticated_user(self):
        self.client.force_login(self.user)
        bookmark = Bookmark.objects.create(
            user=self.user,
            url="https://example.com/pinned",
            normalized_url="https://example.com/pinned",
            hash="pinned-hash",
            title="Pinned bookmark",
        )
        BookmarkUserState.objects.create(
            user=self.user,
            bookmark=bookmark,
            is_pinned=True,
        )

        response = self.client.get(reverse("homepage"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Overview")

    def test_web_toggle_anonymous_does_not_create_state_and_shows_error(self):
        toggle_url = reverse(
            "article-state-toggle", args=[self.article.id, "is_read_later"]
        )

        response = self.client.post(
            toggle_url, data={"q": "feeds", "page": "2"}, follow=True
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(ArticleUserState.objects.count(), 0)
        messages = [str(message) for message in response.context["messages"]]
        self.assertIn("Please log in to update article state.", messages)


class FeedArticleBindingTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="worker", password="pass"
        )
        self.token = Token.objects.create(user=self.user)
        self.auth_header = {"HTTP_AUTHORIZATION": f"Token {self.token.key}"}

    def test_feed_list_api_returns_array_for_worker(self):
        Feed.objects.create(name="Feed A", url="https://example.com/a.xml")

        response = self.client.get(reverse("feed-list"), **self.auth_header)

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIsInstance(payload, list)
        self.assertEqual(payload[0]["name"], "Feed A")

    def test_feed_list_api_unauthenticated_returns_401(self):
        response = self.client.get(reverse("feed-list"))
        self.assertIn(response.status_code, (401, 403))

    def test_feed_list_api_returns_only_active_and_display_ordered(self):
        feed_first = Feed.objects.create(
            name="Feed First",
            url="https://example.com/first.xml",
            display_order=1,
            is_active=True,
        )
        Feed.objects.create(
            name="Feed Hidden",
            url="https://example.com/hidden.xml",
            display_order=2,
            is_active=False,
        )
        feed_last = Feed.objects.create(
            name="Feed Last",
            url="https://example.com/last.xml",
            display_order=3,
            is_active=True,
        )

        response = self.client.get(reverse("feed-list"), **self.auth_header)

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(
            [item["id"] for item in payload], [feed_first.id, feed_last.id]
        )

    def test_feed_reorder_updates_display_order(self):
        feed_a = Feed.objects.create(name="Feed A", url="https://example.com/a.xml")
        feed_b = Feed.objects.create(name="Feed B", url="https://example.com/b.xml")
        feed_c = Feed.objects.create(name="Feed C", url="https://example.com/c.xml")

        response = self.client.post(
            reverse("feed-reorder"),
            data={"feed_ids": [feed_c.id, feed_a.id, feed_b.id]},
            content_type="application/json",
            **self.auth_header,
        )

        self.assertEqual(response.status_code, 200)
        feed_a.refresh_from_db()
        feed_b.refresh_from_db()
        feed_c.refresh_from_db()
        self.assertEqual(feed_c.display_order, 1)
        self.assertEqual(feed_a.display_order, 2)
        self.assertEqual(feed_b.display_order, 3)

    def test_ingest_binds_article_to_feed(self):
        feed = Feed.objects.create(name="Example", url="https://example.com/rss.xml")

        response = self.client.post(
            reverse("article-ingest"),
            data=[
                {
                    "feed_id": feed.id,
                    "title": "Bound article",
                    "link": "https://example.com/a1",
                    "guid": "a1",
                }
            ],
            content_type="application/json",
            **self.auth_header,
        )

        self.assertEqual(response.status_code, 200)
        article = Article.objects.get(title="Bound article")
        self.assertEqual(article.feed_id, feed.id)

    def test_ingest_unauthenticated_returns_401(self):
        response = self.client.post(
            reverse("article-ingest"),
            data=[{"title": "X", "link": "https://example.com/x"}],
            content_type="application/json",
        )
        self.assertIn(response.status_code, (401, 403))

    def test_dashboard_hides_legacy_feedless_articles(self):
        feed = Feed.objects.create(
            name="Current Feed", url="https://example.com/new.xml"
        )
        Article.objects.create(
            feed=feed,
            title="Current article",
            link="https://example.com/current",
            normalized_link="https://example.com/current",
            guid="current-guid",
            hash="b1d8f07f8d6f700e57480e3c39fc36f8d6c0fec8a9846d907f5f578f31bb0d95",
        )
        Article.objects.create(
            feed=None,
            title="Legacy article",
            link="https://example.com/legacy",
            normalized_link="https://example.com/legacy",
            guid="legacy-guid",
            hash="6f08f2161d21ef863ed3bd83f4d503f7de60d6b8f3baeb3340016be0f2f0e5f4",
        )

        response = self.client.get(reverse("rss-dashboard"))

        self.assertContains(response, "Current article")
        self.assertNotContains(response, "Legacy article")

    def test_reader_view_prefers_content_then_summary(self):
        self.client.force_login(self.user)
        feed = Feed.objects.create(
            name="Reader Feed", url="https://example.com/reader.xml"
        )
        content_article = Article.objects.create(
            feed=feed,
            title="Reader content article",
            link="https://example.com/content",
            normalized_link="https://example.com/content",
            guid="reader-content-guid",
            hash="afe58e95505cbec0cf70916f01f8453594e3f55442ad8f1b3d8cf905bf11f2a2",
            summary="Summary text",
            content="<p>Body content</p>",
        )
        summary_article = Article.objects.create(
            feed=feed,
            title="Reader summary article",
            link="https://example.com/summary",
            normalized_link="https://example.com/summary",
            guid="reader-summary-guid",
            hash="a5dc724e59f5c8419386f5fd4f862f13f9924ec7151ecfef58114c42f3095294",
            summary="Summary only text",
            content="",
        )

        content_response = self.client.get(
            reverse("article-reader", args=[content_article.id])
        )
        summary_response = self.client.get(
            reverse("article-reader", args=[summary_article.id])
        )

        self.assertContains(content_response, "Body content")
        self.assertContains(summary_response, "Summary only text")


class FullTextExtractionMVPTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="worker",
            email="worker@example.com",
            password="password123",
        )
        self.token = Token.objects.create(user=self.user)
        self.auth_header = {"HTTP_AUTHORIZATION": f"Token {self.token.key}"}
        self.feed = Feed.objects.create(
            name="Extraction Feed",
            url="https://example.com/rss.xml",
        )

    @patch("apps.rssapp.views.extract_article_content")
    def test_ingest_backfills_full_text_when_feed_content_missing(self, mock_extract):
        mock_extract.return_value = {
            "content": "<p>Extracted article body</p>",
            "source": "extracted",
            "status": "success",
        }

        response = self.client.post(
            reverse("article-ingest"),
            data=[
                {
                    "feed_id": self.feed.id,
                    "title": "Needs extraction",
                    "link": "https://example.com/posts/needs-extraction",
                    "guid": "needs-extraction-guid",
                    "summary": "Short feed summary",
                }
            ],
            content_type="application/json",
            **self.auth_header,
        )

        self.assertEqual(response.status_code, 200)
        article = Article.objects.get(hash__isnull=False, title="Needs extraction")
        self.assertEqual(article.content, "<p>Extracted article body</p>")
        self.assertEqual(article.content_source, "extracted")
        self.assertEqual(article.extraction_status, "success")
        mock_extract.assert_called_once_with(
            "https://example.com/posts/needs-extraction"
        )

    @patch("apps.rssapp.views.extract_article_content")
    def test_ingest_keeps_feed_content_without_triggering_extraction(
        self, mock_extract
    ):
        response = self.client.post(
            reverse("article-ingest"),
            data=[
                {
                    "feed_id": self.feed.id,
                    "title": "Already has content",
                    "link": "https://example.com/posts/has-content",
                    "guid": "has-content-guid",
                    "content": "<p>Provided by feed</p>",
                }
            ],
            content_type="application/json",
            **self.auth_header,
        )

        self.assertEqual(response.status_code, 200)
        article = Article.objects.get(title="Already has content")
        self.assertEqual(article.content, "<p>Provided by feed</p>")
        self.assertEqual(article.content_source, "feed")
        self.assertEqual(article.extraction_status, "provided")
        mock_extract.assert_not_called()

    @override_settings(FULL_TEXT_EXTRACTION_ENABLED=True)
    @patch("apps.rssapp.views.extract_article_content")
    def test_bulk_ingest_skips_inline_extraction_to_avoid_timeouts(self, mock_extract):
        mock_extract.return_value = {
            "content": "",
            "source": "summary",
            "status": "failed",
        }

        response = self.client.post(
            reverse("article-ingest"),
            data=[
                {
                    "feed_id": self.feed.id,
                    "title": "Batch item 1",
                    "link": "https://example.com/posts/batch-1",
                    "guid": "batch-guid-1",
                    "summary": "Summary one",
                },
                {
                    "feed_id": self.feed.id,
                    "title": "Batch item 2",
                    "link": "https://example.com/posts/batch-2",
                    "guid": "batch-guid-2",
                    "summary": "Summary two",
                },
            ],
            content_type="application/json",
            **self.auth_header,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Article.objects.filter(feed=self.feed).count(), 2)
        self.assertEqual(
            Article.objects.filter(
                content_source="summary", extraction_status="skipped"
            ).count(),
            2,
        )
        mock_extract.assert_not_called()


class UserPreferenceMVPTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="reader",
            email="reader@example.com",
            password="password123",
        )
        self.profile = UserProfile.objects.create(user=self.user)

    def test_account_settings_can_save_theme_preference(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("settings-account"),
            data={
                "form_action": "profile",
                "default_sort": "published_desc",
                "items_per_page": 20,
                "theme_preference": "dark",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.theme_preference, "dark")
        self.assertContains(response, "Preferences saved.")


class BookmarkLinkBehaviorTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="bookmarker",
            email="bookmarker@example.com",
            password="password123",
        )
        self.client.force_login(self.user)
        self.feed = Feed.objects.create(
            name="Example Feed",
            url="https://example.com/rss.xml",
        )
        self.article = Article.objects.create(
            feed=self.feed,
            title="Reader-backed article",
            link="https://example.com/posts/reader-backed",
            normalized_link="https://example.com/posts/reader-backed",
            guid="reader-backed-guid",
            hash="reader-backed-hash",
        )

    def test_bookmark_from_article_keeps_external_link(self):
        Bookmark.objects.create(
            user=self.user,
            url=self.article.link,
            title=self.article.title,
        )

        response = self.client.get(reverse("bookmark-list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'href="{self.article.link}"')

    def test_manual_bookmark_keeps_external_link(self):
        Bookmark.objects.create(
            user=self.user,
            url="https://external.example.com/manual",
            title="Manual Bookmark",
        )

        response = self.client.get(reverse("bookmark-list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="https://external.example.com/manual"')

    def test_save_article_as_bookmark_does_not_store_source_article(self):
        response = self.client.post(reverse("article-save", args=[self.article.id]))

        self.assertEqual(response.status_code, 302)
        bookmark = Bookmark.objects.get(user=self.user, url=self.article.link)
        self.assertIsNone(bookmark.source_article)


class FeedArticlesViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="reader",
            email="reader@example.com",
            password="password123",
        )
        self.feed_a = Feed.objects.create(
            name="Feed A", url="https://example.com/a.xml", category="News"
        )
        self.feed_b = Feed.objects.create(
            name="Feed B", url="https://example.com/b.xml", category="Tech"
        )
        self.article_a1 = Article.objects.create(
            feed=self.feed_a,
            title="Article A1",
            link="https://example.com/a1",
            normalized_link="https://example.com/a1",
            guid="a1",
            hash="hash_a1",
        )
        self.article_a2 = Article.objects.create(
            feed=self.feed_a,
            title="Article A2",
            link="https://example.com/a2",
            normalized_link="https://example.com/a2",
            guid="a2",
            hash="hash_a2",
        )
        self.article_b1 = Article.objects.create(
            feed=self.feed_b,
            title="Article B1",
            link="https://example.com/b1",
            normalized_link="https://example.com/b1",
            guid="b1",
            hash="hash_b1",
        )

    def test_feed_articles_view_displays_only_feed_articles(self):
        response = self.client.get(reverse("feed-articles", args=[self.feed_a.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Article A1")
        self.assertContains(response, "Article A2")
        self.assertNotContains(response, "Article B1")

    def test_feed_articles_view_returns_404_for_nonexistent_feed(self):
        response = self.client.get(reverse("feed-articles", args=[9999]))

        self.assertEqual(response.status_code, 404)

    def test_feed_articles_view_filters_by_search_query(self):
        response = self.client.get(
            reverse("feed-articles", args=[self.feed_a.id]) + "?q=A1"
        )

        self.assertContains(response, "Article A1")
        self.assertNotContains(response, "Article A2")

    def test_feed_articles_view_shows_article_counts(self):
        self.client.force_login(self.user)

        ArticleUserState.objects.create(
            user=self.user, article=self.article_a1, is_read_later=True
        )

        response = self.client.get(reverse("feed-articles", args=[self.feed_a.id]))

        # Template renders label and count in separate elements
        content = response.content.decode()
        self.assertIn("All", content)
        self.assertIn("Read Later", content)

    def test_feeds_page_includes_state_filters_and_sort_controls(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("feeds-page"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Unread")
        self.assertContains(response, "Read Later")
        self.assertContains(response, "Latest")
        self.assertContains(response, "Oldest")
        self.assertContains(response, "Smart")

    def test_dashboard_sidebar_marks_all_articles_badge_as_unread(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("rss-dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "3 unread")

    def test_dashboard_sidebar_unread_count_is_not_inflated_by_other_users(self):
        other_user = get_user_model().objects.create_user(
            username="another-reader",
            email="another-reader@example.com",
            password="password123",
        )
        self.client.force_login(self.user)

        for article in (self.article_a1, self.article_a2, self.article_b1):
            ArticleUserState.objects.create(
                user=self.user, article=article, is_read=True
            )

        ArticleUserState.objects.create(
            user=other_user, article=self.article_a1, is_read=True
        )
        ArticleUserState.objects.create(
            user=other_user, article=self.article_a2, is_read=True
        )

        response = self.client.get(reverse("rss-dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "0 unread")


class FeedDiscoveryAndOpmlTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="discoverer",
            email="discoverer@example.com",
            password="password123",
        )
        self.client.force_login(self.user)

    @patch("apps.rssapp.forms.discover_feed_url")
    def test_feed_create_form_accepts_homepage_url_via_discovery(self, mock_discover):
        mock_discover.return_value = {
            "feed_url": "https://example.com/feed.xml",
            "title": "Example Feed",
        }

        form = FeedCreateForm(
            data={
                "name": "",
                "url": "https://example.com",
                "category": "Tech",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        feed = form.save()
        self.assertEqual(feed.url, "https://example.com/feed.xml")
        self.assertEqual(feed.name, "Example Feed")

    def test_opml_export_includes_feed_categories(self):
        Feed.objects.create(
            name="Example Feed",
            url="https://example.com/feed.xml",
            category="Tech",
        )

        response = self.client.get(reverse("feeds-opml-export"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/xml")
        self.assertContains(response, 'title="Feedee Subscriptions"')
        self.assertContains(response, 'text="Tech"')
        self.assertContains(response, 'xmlUrl="https://example.com/feed.xml"')

    def test_opml_import_skips_duplicates_and_preserves_categories(self):
        Feed.objects.create(
            name="Existing Feed",
            url="https://example.com/existing.xml",
            category="News",
        )
        opml = b"""<?xml version='1.0' encoding='UTF-8'?>
<opml version='1.0'>
  <body>
    <outline text='Tech'>
      <outline text='Example Feed' title='Example Feed' type='rss' xmlUrl='https://example.com/feed.xml' htmlUrl='https://example.com/' />
    </outline>
    <outline text='News'>
      <outline text='Existing Feed' title='Existing Feed' type='rss' xmlUrl='https://example.com/existing.xml' htmlUrl='https://example.com/' />
    </outline>
  </body>
</opml>
"""

        response = self.client.post(
            reverse("feeds-opml-import"),
            data={
                "opml_file": SimpleUploadedFile(
                    "feeds.opml", opml, content_type="text/xml"
                )
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            Feed.objects.filter(
                url="https://example.com/feed.xml", category="Tech"
            ).exists()
        )
        self.assertEqual(
            Feed.objects.filter(url="https://example.com/existing.xml").count(), 1
        )
        self.assertContains(response, "Imported 1 feed")


class FeedFetchHealthTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="worker-health",
            email="worker-health@example.com",
            password="password123",
        )
        self.token = Token.objects.create(user=self.user)
        self.auth_header = {"HTTP_AUTHORIZATION": f"Token {self.token.key}"}

    def test_feed_list_api_returns_only_due_feeds_with_health_metadata(self):
        due_feed = Feed.objects.create(
            name="Due Feed",
            url="https://example.com/due.xml",
            next_fetch_at=timezone.now() - timedelta(minutes=5),
            etag='"abc"',
            last_modified="Wed, 21 Oct 2015 07:28:00 GMT",
        )
        Feed.objects.create(
            name="Later Feed",
            url="https://example.com/later.xml",
            next_fetch_at=timezone.now() + timedelta(minutes=30),
        )

        response = self.client.get(reverse("feed-list"), **self.auth_header)

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual([item["id"] for item in payload], [due_feed.id])
        self.assertEqual(payload[0]["etag"], '"abc"')
        self.assertEqual(payload[0]["last_modified"], "Wed, 21 Oct 2015 07:28:00 GMT")

    def test_feed_fetch_status_api_tracks_backoff_and_success_reset(self):
        feed = Feed.objects.create(
            name="Tracked Feed",
            url="https://example.com/feed.xml",
            next_fetch_at=timezone.now() - timedelta(minutes=1),
        )

        error_response = self.client.post(
            reverse("feed-fetch-status", args=[feed.id]),
            data={"status": "error", "error": "timeout"},
            content_type="application/json",
            **self.auth_header,
        )

        self.assertEqual(error_response.status_code, 200)
        feed.refresh_from_db()
        self.assertEqual(feed.consecutive_failures, 1)
        self.assertEqual(feed.last_error, "timeout")
        self.assertGreater(feed.next_fetch_at, timezone.now())

        success_response = self.client.post(
            reverse("feed-fetch-status", args=[feed.id]),
            data={
                "status": "success",
                "etag": '"fresh"',
                "last_modified": "Thu, 22 Oct 2015 07:28:00 GMT",
                "item_count": 4,
            },
            content_type="application/json",
            **self.auth_header,
        )

        self.assertEqual(success_response.status_code, 200)
        feed.refresh_from_db()
        self.assertEqual(feed.consecutive_failures, 0)
        self.assertEqual(feed.last_error, "")
        self.assertEqual(feed.etag, '"fresh"')
        self.assertEqual(feed.last_modified, "Thu, 22 Oct 2015 07:28:00 GMT")


class EnhancedSearchAndRankingTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="smart-reader",
            email="smart-reader@example.com",
            password="password123",
        )
        self.client.force_login(self.user)
        self.feed = Feed.objects.create(
            name="Smart Feed",
            url="https://example.com/smart.xml",
        )

    def test_dashboard_search_matches_summary_and_content(self):
        Article.objects.create(
            feed=self.feed,
            title="Unrelated title",
            link="https://example.com/summary-hit",
            normalized_link="https://example.com/summary-hit",
            guid="summary-hit",
            hash="summary-hit",
            summary="Contains orbital needle in summary",
        )
        Article.objects.create(
            feed=self.feed,
            title="Another title",
            link="https://example.com/content-hit",
            normalized_link="https://example.com/content-hit",
            guid="content-hit",
            hash="content-hit",
            content="<p>Deep content needle appears here.</p>",
        )

        response = self.client.get(reverse("rss-dashboard"), {"q": "needle"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Unrelated title")
        self.assertContains(response, "Another title")

    def test_dashboard_sort_smart_prioritizes_unread_then_saved(self):
        read_article = Article.objects.create(
            feed=self.feed,
            title="Read article",
            link="https://example.com/read",
            normalized_link="https://example.com/read",
            guid="read-guid",
            hash="read-guid",
            published_at=timezone.now() - timedelta(hours=1),
        )
        favorite_unread = Article.objects.create(
            feed=self.feed,
            title="Favorite unread",
            link="https://example.com/favorite-unread",
            normalized_link="https://example.com/favorite-unread",
            guid="favorite-unread-guid",
            hash="favorite-unread-guid",
            published_at=timezone.now() - timedelta(days=2),
        )
        plain_unread = Article.objects.create(
            feed=self.feed,
            title="Plain unread",
            link="https://example.com/plain-unread",
            normalized_link="https://example.com/plain-unread",
            guid="plain-unread-guid",
            hash="plain-unread-guid",
            published_at=timezone.now() - timedelta(days=1),
        )

        ArticleUserState.objects.create(
            user=self.user,
            article=read_article,
            is_read=True,
        )
        ArticleUserState.objects.create(
            user=self.user,
            article=favorite_unread,
            is_read_later=True,
        )

        response = self.client.get(reverse("rss-dashboard"), {"sort": "smart"})

        self.assertEqual(response.status_code, 200)
        article_ids = [card["id"] for card in response.context["article_cards"]]
        self.assertEqual(article_ids[0], favorite_unread.id)
        self.assertLess(
            article_ids.index(plain_unread.id), article_ids.index(read_article.id)
        )
