from django.urls import include, path

urlpatterns = [
    path("", include("apps.rss_service.public_api_urls")),
    path("", include("apps.bookmark_service.public_api_urls")),
]
