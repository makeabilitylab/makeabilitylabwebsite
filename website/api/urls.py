"""
URL routing for the public API (#1268), mounted at ``/api/`` by the root
URLconf. Versioned under ``v1/`` so the contract can evolve without breaking
consumers.

The DRF ``DefaultRouter`` also serves a self-documenting API root at
``/api/v1/`` listing every endpoint, and (in DEBUG) a browsable HTML UI.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    GrantViewSet,
    PersonViewSet,
    ProjectViewSet,
    PublicationViewSet,
)

app_name = "api"

router = DefaultRouter()
router.register(r"publications", PublicationViewSet, basename="publication")
router.register(r"people", PersonViewSet, basename="person")
router.register(r"projects", ProjectViewSet, basename="project")
router.register(r"grants", GrantViewSet, basename="grant")

urlpatterns = [
    path("v1/", include(router.urls)),
]
