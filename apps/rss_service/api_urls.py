from django.urls import path

from .views import (
    ArticleIngestView,
    ArticleUserStateView,
    DisplayModePreferenceView,
    FeedFetchStatusView,
    FeedListView,
    FeedReorderView,
)

app_name = "rss_service_api"

urlpatterns = [
    path("feeds/", FeedListView.as_view(), name="feed-list"),
    path(
        "feeds/<int:feed_id>/fetch-status/",
        FeedFetchStatusView.as_view(),
        name="feed-fetch-status",
    ),
    path("feeds/reorder/", FeedReorderView.as_view(), name="feed-reorder"),
    path("articles/ingest/", ArticleIngestView.as_view(), name="article-ingest"),
    path(
        "articles/<int:article_id>/state/",
        ArticleUserStateView.as_view(),
        name="article-user-state",
    ),
    path(
        "preferences/display-mode/",
        DisplayModePreferenceView.as_view(),
        name="display-mode-preference",
    ),
]
