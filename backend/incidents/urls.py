from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProjectViewSet,
    EvidenceItemViewSet,
    ExternalResearchViewSet,
    EvidenceScreenshotViewSet,
    SOCIngestAPIView,
)

router = DefaultRouter()
router.register(r'projects', ProjectViewSet, basename='project')
router.register(r'evidence', EvidenceItemViewSet, basename='evidence')
router.register(r'external-research', ExternalResearchViewSet, basename='external-research')
router.register(r'screenshots', EvidenceScreenshotViewSet, basename='screenshot')

urlpatterns = [
    path('', include(router.urls)),
    path('soc/ingest/', SOCIngestAPIView.as_view(), name='soc-ingest'),
]
