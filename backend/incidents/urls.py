from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .auth_views import (
    AuthStatusAPIView,
    InitialSetupAPIView,
    LoginAPIView,
    LogoutAPIView,
    UserProfileAPIView,
    ChangeOwnPasswordAPIView,
    APITokenAPIView,
    AnalystDirectoryAPIView,
    UserViewSet,
)
from .views import (
    ProjectViewSet,
    EvidenceItemViewSet,
    RelatedIncidentViewSet,
    CustomerContactViewSet,
    ExternalResearchViewSet,
    EvidenceScreenshotViewSet,
    MitreCatalogAPIView,
    SOCIngestAPIView,
)

router = DefaultRouter()
router.register(r'projects', ProjectViewSet, basename='project')
router.register(r'evidence', EvidenceItemViewSet, basename='evidence')
router.register(r'related-incidents', RelatedIncidentViewSet, basename='related-incident')
router.register(r'customer-contacts', CustomerContactViewSet, basename='customer-contact')
router.register(r'external-research', ExternalResearchViewSet, basename='external-research')
router.register(r'screenshots', EvidenceScreenshotViewSet, basename='screenshot')
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    path('auth/status/', AuthStatusAPIView.as_view(), name='auth-status'),
    path('auth/setup/', InitialSetupAPIView.as_view(), name='auth-setup'),
    path('auth/login/', LoginAPIView.as_view(), name='auth-login'),
    path('auth/logout/', LogoutAPIView.as_view(), name='auth-logout'),
    path('auth/profile/', UserProfileAPIView.as_view(), name='auth-profile'),
    path('auth/change-password/', ChangeOwnPasswordAPIView.as_view(), name='auth-change-password'),
    path('auth/api-token/', APITokenAPIView.as_view(), name='auth-api-token'),
    path('analysts/', AnalystDirectoryAPIView.as_view(), name='analyst-directory'),
    path('mitre-catalog/', MitreCatalogAPIView.as_view(), name='mitre-catalog'),
    path('', include(router.urls)),
    path('soc/ingest/', SOCIngestAPIView.as_view(), name='soc-ingest'),
]
