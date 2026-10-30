from django.http import HttpResponse
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .demo_scenarios import DEMO_SCENARIO_CATALOG, create_demo_scenario
from .mitre_catalog import MITRE_TACTICS_WITH_TECHNIQUES
from .models import (
    Project,
    RelatedIncident,
    CustomerContact,
    ExternalResearch,
    EvidenceItem,
    EvidenceScreenshot,
    get_user_display_name,
)
from .permissions import (
    ProjectAccessPermission,
    InvestigationItemPermission,
    assert_project_unlocked,
)
from .serializers import (
    ProjectSerializer,
    RelatedIncidentSerializer,
    CustomerContactSerializer,
    ExternalResearchSerializer,
    EvidenceItemSerializer,
    EvidenceScreenshotSerializer,
)
from .reports import (
    generate_timeline_csv,
    generate_key_evidence_odt,
    generate_key_evidence_markdown,
)


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = (
        Project.objects.select_related('locked_by')
        .prefetch_related('related_incidents', 'customer_contacts', 'external_research_items')
        .all()
    )
    serializer_class = ProjectSerializer
    permission_classes = [ProjectAccessPermission]

    def perform_create(self, serializer):
        lead = (serializer.validated_data.get('lead_analyst') or '').strip()
        if not lead:
            lead = get_user_display_name(self.request.user)
        instance = serializer.save(lead_analyst=lead)
        instance.sync_archive_manifest()

    def perform_update(self, serializer):
        assert_project_unlocked(serializer.instance)
        instance = serializer.save()
        instance.sync_archive_manifest()

    def perform_destroy(self, instance):
        if instance.is_locked:
            raise PermissionDenied(
                "Cannot delete a locked project. Unlock the project first if you intend to delete it."
            )
        instance.delete()

    @action(detail=True, methods=['post'])
    def lock(self, request, pk=None):
        project = self.get_object()
        if not project.is_locked:
            project.is_locked = True
            project.locked_by = request.user
            project.locked_at = timezone.now()
            project.save(update_fields=['is_locked', 'locked_by', 'locked_at', 'updated_at'])
        return Response(self.get_serializer(project).data)

    @action(detail=True, methods=['post'])
    def unlock(self, request, pk=None):
        project = self.get_object()
        if project.is_locked:
            project.is_locked = False
            project.locked_by = None
            project.locked_at = None
            project.save(update_fields=['is_locked', 'locked_by', 'locked_at', 'updated_at'])
        return Response(self.get_serializer(project).data)

    @action(detail=True, methods=['get'])
    def timeline(self, request, pk=None):
        project = self.get_object()
        items = project.get_timeline_evidence()
        serializer = EvidenceItemSerializer(items, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def report_csv(self, request, pk=None):
        """
        Report One: Generates and downloads a time-ordered CSV report of ALL evidence.
        """
        project = self.get_object()
        csv_content, _ = generate_timeline_csv(project)
        project.sync_archive_manifest()
        filename = f"incident_{project.pk}_evidence_timeline.csv"
        response = HttpResponse(csv_content, content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    @action(detail=True, methods=['get'])
    def report_odt(self, request, pk=None):
        """
        Report Two (ODT): Generates and downloads a concise OpenDocument Text (.odt) report
        of ONLY Key Evidence items, time-ordered, with embedded screenshots, links, and summary tables.
        """
        project = self.get_object()
        odt_bytes, _ = generate_key_evidence_odt(project)
        project.sync_archive_manifest()
        filename = f"incident_{project.pk}_key_evidence_report.odt"
        response = HttpResponse(
            odt_bytes,
            content_type="application/vnd.oasis.opendocument.text",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    @action(detail=True, methods=['get'])
    def report_md(self, request, pk=None):
        """
        Report Two (Markdown): Creates the dedicated screenshot folder alongside the Markdown report
        and downloads either the .md file or a .zip bundle (containing the .md + screenshot folder)
        when ?bundle=zip is passed.
        """
        project = self.get_object()
        md_content, _, zip_bytes = generate_key_evidence_markdown(project)
        project.sync_archive_manifest()
        if request.query_params.get("bundle") == "zip":
            filename = f"incident_{project.pk}_key_evidence_markdown_with_screenshots.zip"
            response = HttpResponse(zip_bytes, content_type="application/zip")
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            return response

        filename = f"incident_{project.pk}_key_evidence_report.md"
        response = HttpResponse(md_content, content_type="text/markdown; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    @action(detail=False, methods=['get'])
    def demo_scenarios(self, request):
        """Returns the catalog of Super Admin-only sample incident scenarios."""
        return Response(DEMO_SCENARIO_CATALOG)

    @action(detail=False, methods=['post'])
    def seed_demo(self, request):
        """
        Super Admin-only endpoint to create one of the 4 themed sample SOC Incident Response
        investigations (`expanse`, `star_trek`, `matrix`, `star_wars`) or all 4 (`all`).
        """
        scenario_key = (
            request.data.get('scenario')
            or request.query_params.get('scenario')
            or 'expanse'
        )
        try:
            created_projects = create_demo_scenario(scenario_key)
        except ValueError as exc:
            return Response(
                {"scenario": [str(exc)]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(created_projects) == 1:
            serializer = self.get_serializer(created_projects[0])
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        serialized = self.get_serializer(created_projects, many=True).data
        return Response(
            {
                "count": len(serialized),
                "projects": serialized,
                "primary": serialized[0],
            },
            status=status.HTTP_201_CREATED,
        )


class EvidenceItemViewSet(viewsets.ModelViewSet):
    queryset = EvidenceItem.objects.select_related('project').prefetch_related('screenshots').all()
    serializer_class = EvidenceItemSerializer
    permission_classes = [InvestigationItemPermission]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        qs = super().get_queryset()
        project_id = self.request.query_params.get('project')
        if project_id:
            qs = qs.filter(project_id=project_id)
        return qs

    def perform_create(self, serializer):
        project = serializer.validated_data.get('project')
        assert_project_unlocked(project)
        analyst = (serializer.validated_data.get('analyst_name') or '').strip()
        if not analyst:
            analyst = get_user_display_name(self.request.user)
        instance = serializer.save(analyst_name=analyst)
        files = self.request.FILES.getlist('screenshots_upload')
        captions = self.request.data.getlist('screenshot_captions') if hasattr(self.request.data, 'getlist') else []
        for idx, img_file in enumerate(files):
            caption = captions[idx] if idx < len(captions) else ""
            EvidenceScreenshot.objects.create(
                evidence=instance,
                image=img_file,
                caption=caption,
                analyst_name=instance.analyst_name,
            )
        instance.project.sync_archive_manifest()

    def perform_update(self, serializer):
        assert_project_unlocked(serializer.instance.project)
        if 'project' in serializer.validated_data:
            assert_project_unlocked(serializer.validated_data['project'])
        instance = serializer.save()
        files = self.request.FILES.getlist('screenshots_upload')
        captions = self.request.data.getlist('screenshot_captions') if hasattr(self.request.data, 'getlist') else []
        for idx, img_file in enumerate(files):
            caption = captions[idx] if idx < len(captions) else ""
            EvidenceScreenshot.objects.create(
                evidence=instance,
                image=img_file,
                caption=caption,
                analyst_name=instance.analyst_name,
            )
        instance.project.sync_archive_manifest()

    def perform_destroy(self, instance):
        project = instance.project
        assert_project_unlocked(project)
        instance.delete()
        project.sync_archive_manifest()

    @action(detail=True, methods=['post'])
    def toggle_key(self, request, pk=None):
        item = self.get_object()
        assert_project_unlocked(item.project)
        item.is_key_evidence = not item.is_key_evidence
        item.save(update_fields=['is_key_evidence', 'updated_at'])
        item.project.sync_archive_manifest()
        return Response(self.get_serializer(item).data)


class RelatedIncidentViewSet(viewsets.ModelViewSet):
    queryset = RelatedIncident.objects.select_related('project').all()
    serializer_class = RelatedIncidentSerializer
    permission_classes = [InvestigationItemPermission]

    def get_queryset(self):
        qs = super().get_queryset()
        project_id = self.request.query_params.get('project')
        if project_id:
            qs = qs.filter(project_id=project_id)
        return qs

    def perform_create(self, serializer):
        project = serializer.validated_data.get('project')
        assert_project_unlocked(project)
        analyst = (serializer.validated_data.get('analyst_name') or '').strip()
        if not analyst:
            analyst = get_user_display_name(self.request.user)
        instance = serializer.save(analyst_name=analyst)
        instance.project.sync_archive_manifest()

    def perform_update(self, serializer):
        assert_project_unlocked(serializer.instance.project)
        if 'project' in serializer.validated_data:
            assert_project_unlocked(serializer.validated_data['project'])
        instance = serializer.save()
        instance.project.sync_archive_manifest()

    def perform_destroy(self, instance):
        project = instance.project
        assert_project_unlocked(project)
        instance.delete()
        project.sync_archive_manifest()


class CustomerContactViewSet(viewsets.ModelViewSet):
    queryset = CustomerContact.objects.select_related('project').all()
    serializer_class = CustomerContactSerializer
    permission_classes = [InvestigationItemPermission]

    def get_queryset(self):
        qs = super().get_queryset()
        project_id = self.request.query_params.get('project')
        if project_id:
            qs = qs.filter(project_id=project_id)
        return qs

    def perform_create(self, serializer):
        project = serializer.validated_data.get('project')
        assert_project_unlocked(project)
        instance = serializer.save()
        instance.project.sync_archive_manifest()

    def perform_update(self, serializer):
        assert_project_unlocked(serializer.instance.project)
        if 'project' in serializer.validated_data:
            assert_project_unlocked(serializer.validated_data['project'])
        instance = serializer.save()
        instance.project.sync_archive_manifest()

    def perform_destroy(self, instance):
        project = instance.project
        assert_project_unlocked(project)
        instance.delete()
        project.sync_archive_manifest()


class ExternalResearchViewSet(viewsets.ModelViewSet):
    queryset = ExternalResearch.objects.select_related('project').all()
    serializer_class = ExternalResearchSerializer
    permission_classes = [InvestigationItemPermission]

    def get_queryset(self):
        qs = super().get_queryset()
        project_id = self.request.query_params.get('project')
        if project_id:
            qs = qs.filter(project_id=project_id)
        return qs

    def perform_create(self, serializer):
        project = serializer.validated_data.get('project')
        assert_project_unlocked(project)
        analyst = (serializer.validated_data.get('analyst_name') or '').strip()
        if not analyst:
            analyst = get_user_display_name(self.request.user)
        instance = serializer.save(analyst_name=analyst)
        instance.project.sync_archive_manifest()

    def perform_update(self, serializer):
        assert_project_unlocked(serializer.instance.project)
        if 'project' in serializer.validated_data:
            assert_project_unlocked(serializer.validated_data['project'])
        instance = serializer.save()
        instance.project.sync_archive_manifest()

    def perform_destroy(self, instance):
        project = instance.project
        assert_project_unlocked(project)
        instance.delete()
        project.sync_archive_manifest()


class EvidenceScreenshotViewSet(viewsets.ModelViewSet):
    queryset = EvidenceScreenshot.objects.select_related('evidence__project').all()
    serializer_class = EvidenceScreenshotSerializer
    permission_classes = [InvestigationItemPermission]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def perform_create(self, serializer):
        evidence = serializer.validated_data.get('evidence')
        assert_project_unlocked(evidence.project)
        analyst = (serializer.validated_data.get('analyst_name') or '').strip()
        if not analyst:
            analyst = get_user_display_name(self.request.user)
        instance = serializer.save(analyst_name=analyst)
        instance.evidence.project.sync_archive_manifest()

    def perform_update(self, serializer):
        assert_project_unlocked(serializer.instance.evidence.project)
        if 'evidence' in serializer.validated_data:
            assert_project_unlocked(serializer.validated_data['evidence'].project)
        instance = serializer.save()
        instance.evidence.project.sync_archive_manifest()

    def perform_destroy(self, instance):
        project = instance.evidence.project
        assert_project_unlocked(project)
        instance.delete()
        project.sync_archive_manifest()


class MitreCatalogAPIView(APIView):
    """Returns the structured MITRE ATT&CK Tactics and Techniques catalog for UI multi-selects."""
    permission_classes = [InvestigationItemPermission]

    def get(self, request):
        return Response(MITRE_TACTICS_WITH_TECHNIQUES)


class SOCIngestAPIView(APIView):
    """
    Integration endpoint for existing Python/Django SOC tools (SIEM, SOAR, IDS)
    to programmatically push Atomic or Search Result evidence into an incident project.
    Requires Analyst, Admin, or Super Admin credentials (e.g. `Authorization: Token <token>`).
    """
    permission_classes = [InvestigationItemPermission]

    def post(self, request):
        project_id = request.data.get('project_id') or request.data.get('project')
        ticket_id = request.data.get('ticket_id')

        project = None
        if project_id:
            project = Project.objects.filter(pk=project_id).first()
        elif ticket_id:
            project = Project.objects.filter(ticket_id=ticket_id).first()

        if not project:
            return Response(
                {"error": "Specify a valid 'project_id' or 'ticket_id' to ingest evidence."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        assert_project_unlocked(project)

        payload = request.data.copy()
        payload['project'] = project.pk
        if not (payload.get('analyst_name') or '').strip():
            payload['analyst_name'] = get_user_display_name(request.user)
        serializer = EvidenceItemSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        item = serializer.save()
        project.sync_archive_manifest()
        return Response(EvidenceItemSerializer(item).data, status=status.HTTP_201_CREATED)
