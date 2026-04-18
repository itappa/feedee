from django.test import SimpleTestCase
from django.urls import reverse


class ServiceNamespaceRoutingTests(SimpleTestCase):
    def test_rss_service_html_routes_are_namespaced(self):
        self.assertEqual(reverse("rss_service:feeds-page"), "/rss/feeds/")
        self.assertEqual(
            reverse("rss_service:feed-articles", args=[1]), "/rss/feeds/1/"
        )
        self.assertEqual(
            reverse("rss_service:article-reader", args=[1]),
            "/rss/articles/1/reader/",
        )

    def test_bookmark_service_html_routes_are_namespaced(self):
        self.assertEqual(
            reverse("bookmark_service:bookmarks-page"),
            "/bookmark-service/bookmarks/",
        )
        self.assertEqual(
            reverse("bookmark_service:bookmark-add"),
            "/bookmark-service/bookmarks/add/",
        )

    def test_rss_service_api_routes_are_namespaced(self):
        self.assertEqual(reverse("rss_service_api:feed-list"), "/api/rss/feeds/")
        self.assertEqual(
            reverse("rss_service_api:article-user-state", args=[1]),
            "/api/rss/articles/1/state/",
        )

    def test_bookmark_service_api_routes_are_namespaced(self):
        self.assertEqual(
            reverse("bookmark_service_api:fetch-metadata"),
            "/api/bookmarks/bookmarks/fetch-metadata/",
        )
        self.assertEqual(
            reverse("bookmark_service_api:bookmarklet-create"),
            "/api/bookmarks/bookmarklet/create/",
        )

    def test_legacy_html_route_names_are_still_supported(self):
        self.assertEqual(reverse("rss-dashboard"), "/today/")
        self.assertEqual(reverse("feeds-page"), "/feeds/")
        self.assertEqual(reverse("bookmarks-page"), "/bookmarks/")

    def test_legacy_api_route_names_are_still_supported(self):
        self.assertEqual(reverse("feed-list"), "/api/feeds/")
        self.assertEqual(reverse("article-ingest"), "/api/articles/ingest/")
        self.assertEqual(reverse("fetch-metadata"), "/api/bookmarks/fetch-metadata/")
