from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from apps.rssapp.forms import EmailLoginForm
from apps.rssapp.views import register_view

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="auth/login.html",
            authentication_form=EmailLoginForm,
        ),
        name="login",
    ),
    path("register/", register_view, name="register"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path(
        "rss/",
        include(("apps.rss_service.urls", "rss_service"), namespace="rss_service"),
    ),
    path(
        "bookmark-service/",
        include(
            ("apps.bookmark_service.urls", "bookmark_service"),
            namespace="bookmark_service",
        ),
    ),
    path(
        "api/rss/",
        include(
            ("apps.rss_service.api_urls", "rss_service_api"),
            namespace="rss_service_api",
        ),
    ),
    path(
        "api/bookmarks/",
        include(
            ("apps.bookmark_service.api_urls", "bookmark_service_api"),
            namespace="bookmark_service_api",
        ),
    ),
    path("", include("apps.rssapp.urls")),
    path("api/", include("apps.rssapp.api_urls")),
]
