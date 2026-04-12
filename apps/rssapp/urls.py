from django.urls import path
from django.views.generic import RedirectView

from .views import (
    article_state_toggle_view,
    bookmark_add_view,
    bookmark_category_list_view,
    bookmark_category_reorder_view,
    bookmark_category_update_view,
    bookmark_delete_view,
    bookmark_edit_view,
    bookmark_from_article_view,
    bookmark_list_view,
    bookmarks_page_view,
    dashboard_view,
    export_opml_view,
    favorites_view,
    feed_articles_view,
    feed_update_view,
    feeds_page_view,
    import_opml_view,
    main_dashboard_view,
    mark_all_read_view,
    read_later_view,
    reader_view,
    settings_view,
    tag_update_view,
)

urlpatterns = [
    path("", dashboard_view, name="rss-dashboard"),
    # Main pages
    path("dashboard/", main_dashboard_view, name="main-dashboard"),
    path("feeds/", feeds_page_view, name="feeds-page"),
    path("bookmarks/", bookmarks_page_view, name="bookmarks-page"),
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
    path("feeds/<int:feed_id>/", feed_articles_view, name="feed-articles"),
    path("feeds/<int:feed_id>/update/", feed_update_view, name="feed-update"),
    # Articles
    path("articles/<int:article_id>/reader/", reader_view, name="article-reader"),
    path(
        "articles/<int:article_id>/state/<str:state_field>/toggle/",
        article_state_toggle_view,
        name="article-state-toggle",
    ),
    path("mark-all-read/", mark_all_read_view, name="mark-all-read"),
    # Bookmarks (legacy routes kept for compatibility)
    path("old-bookmarks/", bookmark_list_view, name="bookmark-list"),
    path("bookmarks/add/", bookmark_add_view, name="bookmark-add"),
    path("bookmarks/<int:bookmark_id>/edit/", bookmark_edit_view, name="bookmark-edit"),
    path(
        "bookmarks/<int:bookmark_id>/delete/",
        bookmark_delete_view,
        name="bookmark-delete",
    ),
    path(
        "bookmarks/from-article/<int:article_id>/",
        bookmark_from_article_view,
        name="bookmark-from-article",
    ),
    # Tags
    path("tags/<int:tag_id>/update/", tag_update_view, name="tag-update"),
    # Bookmark Categories
    path(
        "bookmarks/categories/",
        bookmark_category_list_view,
        name="bookmark-category-list",
    ),
    path(
        "bookmarks/categories/<int:category_id>/update/",
        bookmark_category_update_view,
        name="bookmark-category-update",
    ),
    path(
        "bookmarks/categories/reorder/",
        bookmark_category_reorder_view,
        name="bookmark-category-reorder",
    ),
]
