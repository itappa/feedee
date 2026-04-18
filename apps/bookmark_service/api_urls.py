from django.urls import path

from .views import BookmarkletCreateView, FetchMetadataView

app_name = "bookmark_service_api"

urlpatterns = [
    path(
        "bookmarks/fetch-metadata/",
        FetchMetadataView.as_view(),
        name="fetch-metadata",
    ),
    path(
        "bookmarklet/create/",
        BookmarkletCreateView.as_view(),
        name="bookmarklet-create",
    ),
]
