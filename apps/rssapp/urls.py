from django.urls import path
from django.urls import include
from django.views.generic import RedirectView

from .views import (
    export_opml_view,
    favorites_view,
    feed_update_view,
    import_opml_view,
    main_dashboard_view,
    read_later_view,
    settings_view,
)

urlpatterns = [
    path("", main_dashboard_view, name="homepage"),
    path("", include("apps.rss_service.public_urls")),
    path("", include("apps.bookmark_service.public_urls")),
    # Main pages
    path("overview/", main_dashboard_view, name="overview"),
    path(
        "dashboard/",
        RedirectView.as_view(pattern_name="overview", permanent=True),
        name="main-dashboard",
    ),
    path("read-later/", read_later_view, name="read-later"),
    path("favorites/", favorites_view, name="favorites"),
    # Unified settings
    path("settings/", settings_view, name="settings-feeds", kwargs={"tab": "feeds"}),
    path("settings/tags/", settings_view, name="settings-tags", kwargs={"tab": "tags"}),
    path(
        "settings/account/",
        settings_view,
        name="settings-account",
        kwargs={"tab": "account"},
    ),
    # Legacy redirects
    path(
        "feeds/settings/",
        RedirectView.as_view(pattern_name="settings-feeds", permanent=True),
        name="feed-settings",
    ),
    path(
        "tags/",
        RedirectView.as_view(pattern_name="settings-tags", permanent=True),
        name="tag-list",
    ),
    # Feeds (detail views)
    path("feeds/opml/export/", export_opml_view, name="feeds-opml-export"),
    path("feeds/opml/import/", import_opml_view, name="feeds-opml-import"),
    path("feeds/<int:feed_id>/update/", feed_update_view, name="feed-update"),
]
