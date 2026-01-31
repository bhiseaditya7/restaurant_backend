from django.contrib import admin
from django.urls import path, re_path, include

from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.conf.urls.static import static
from django.conf import settings
from rest_framework import permissions

schema_view = get_schema_view(
    openapi.Info(
        title="restaurant API",
        default_version="v1",
        description="siper Service API.",
        terms_of_service="https://abc/privacy",
        contact=openapi.Contact(email="bhiseaditya7@gmail.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
    # authentication_classes=[],
)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/users/', include('billing.urls')),

    # Swagger URLs
    re_path(
        r"^swagger(?P<format>\.json|\.yaml)$",
        schema_view.without_ui(cache_timeout=0),
        name="schema-json",
    ),
    re_path(
        r"^api/docs/swagger/$",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    re_path(
        r"^api/docs/redoc/$",
        schema_view.with_ui("redoc", cache_timeout=0),
        name="schema-redoc",
    ),
]
