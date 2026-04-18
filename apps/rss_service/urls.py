from django.urls import path

from .views import (
    article_state_toggle_view,
    feed_articles_view,
    feeds_page_view,
    mark_all_read_view,
    reader_view,
)

app_name = "rss_service"

urlpatterns = [
    path("today/", feeds_page_view, name="dashboard"),
    path("feeds/", feeds_page_view, name="feeds-page"),
    path("feeds/<int:feed_id>/", feed_articles_view, name="feed-articles"),
    path("articles/<int:article_id>/reader/", reader_view, name="article-reader"),
    path(
        "articles/<int:article_id>/state/<str:state_field>/toggle/",
        article_state_toggle_view,
        name="article-state-toggle",
    ),
    path("mark-all-read/", mark_all_read_view, name="mark-all-read"),
]
