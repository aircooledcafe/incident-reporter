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
    Customer,
    CustomerContact,
    Investigation,
    Project,
    RelatedIncident,
    ExternalResearch,
    EvidenceItem,
    EvidenceScreenshot,
    EvidencePcap,
    get_user_display_name,
)
from .permissions import (
    CustomerAccessPermission,
    InvestigationAccessPermission,
    ProjectAccessPermission,
    InvestigationItemPermission,
    assert_project_unlocked,
    assert_can_delete_evidence_item,
    assert_can_delete_screenshot,
    assert_can_delete_pcap,
)
from .serializers import (
    CustomerSerializer,
    CustomerContactSerializer,
    InvestigationSerializer,
    ProjectSerializer,
    RelatedIncidentSerializer,
    ExternalResearchSerializer,
    EvidenceItemSerializer,
    EvidenceScreenshotSerializer,
    EvidencePcapSerializer,
)
from .reports import (
    build_investigation_report_filename,
    generate_timeline_csv,
    generate_key_evidence_odt,
    generate_key_evidence_markdown,
)


class CustomerViewSet(viewsets.ModelViewSet):
    """
    CRUD API for Customer entities and directory management.
    """
    queryset = (
        Customer.objects.prefetch_related('contacts', 'investigations')
        .all()
    )
    serializer_class = CustomerSerializer
    permission_classes = [CustomerAccessPermission]

    def perform_destroy(self, instance):
        if instance.investigations.exists():
            raise PermissionDenied(
                f"Cannot delete customer '{instance.name}' because it has {instance.investigations.count()} associated investigation(s). "
                f"Reassign or delete the investigations first."
            )
        instance.delete()

    @action(detail=True, methods=['get'])
    def investigations(self, request, pk=None):
        customer = self.get_object()
        invs = customer.investigations.all()
        serializer = InvestigationSerializer(invs, many=True, context={'request': request})
        return Response(serializer.data)


class CustomerContactViewSet(viewsets.ModelViewSet):
    """
    CRUD API for Customer Contacts with Primary, Secondary, and Tertiary escalation tiers.
    """
    queryset = CustomerContact.objects.select_related('customer').all()
    serializer_class = CustomerContactSerializer
    permission_classes = [CustomerAccessPermission]

    def get_queryset(self):
        qs = super().get_queryset()
        customer_id = self.request.query_params.get('customer') or self.request.query_params.get('customer_id')
        if customer_id:
            qs = qs.filter(customer_id=customer_id)
        return qs

    def perform_create(self, serializer):
        contact = serializer.save()
        # Sync manifest for any investigations under this customer
        for inv in contact.customer.investigations.all():
            inv.sync_archive_manifest()

    def perform_update(self, serializer):
        contact = serializer.save()
        for inv in contact.customer.investigations.all():
            inv.sync_archive_manifest()

    def perform_destroy(self, instance):
        customer = instance.customer
        instance.delete()
        for inv in customer.investigations.all():
            inv.sync_archive_manifest()


class InvestigationViewSet(viewsets.ModelViewSet):
    queryset = (
        Investigation.objects.select_related('locked_by', 'customer', 'lead_analyst_user')
        .prefetch_related('customer__contacts', 'related_incidents', 'external_research_items')
        .all()
    )
    serializer_class = InvestigationSerializer
    permission_classes = [InvestigationAccessPermission]

    def perform_create(self, serializer):
        lead = (serializer.validated_data.get('lead_analyst') or '').strip()
        lead_user = serializer.validated_data.get('lead_analyst_user')
        if lead_user and not lead:
            lead = get_user_display_name(lead_user)
        elif not lead:
            lead = get_user_display_name(self.request.user)
        instance = serializer.save(lead_analyst=lead)
        instance.sync_timeline_events()

    def perform_update(self, serializer):
        assert_project_unlocked(serializer.instance)
        lead = (serializer.validated_data.get('lead_analyst') or '').strip()
        lead_user = serializer.validated_data.get('lead_analyst_user')
        if lead_user and not lead:
            lead = get_user_display_name(lead_user)
        instance = serializer.save(lead_analyst=lead) if lead else serializer.save()
        instance.sync_timeline_events()

    def perform_destroy(self, instance):
        if instance.is_locked:
            raise PermissionDenied(
                "Cannot delete a locked investigation. Unlock the investigation first if you intend to delete it."
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
        serializer = EvidenceItemSerializer(items, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def report_csv(self, request, pk=None):
        project = self.get_object()
        csv_bytes, file_path = generate_timeline_csv(project)
        filename = build_investigation_report_filename(project, "csv")
        response = HttpResponse(csv_bytes, content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    @action(detail=True, methods=['get'])
    def report_odt(self, request, pk=None):
        project = self.get_object()
        odt_bytes, file_path = generate_key_evidence_odt(project)
        filename = build_investigation_report_filename(project, "odt")
        response = HttpResponse(
            odt_bytes,
            content_type='application/vnd.oasis.opendocument.text',
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    @action(detail=True, methods=['get'])
    def report_md(self, request, pk=None):
        project = self.get_object()
        bundle = request.query_params.get('bundle', '').lower() in ('1', 'true', 'zip')
        md_bytes, file_path, zip_bytes, zip_path = generate_key_evidence_markdown(project)
        if bundle:
            filename = build_investigation_report_filename(project, "zip")
            response = HttpResponse(zip_bytes, content_type='application/zip')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        filename = build_investigation_report_filename(project, "md")
        response = HttpResponse(md_bytes, content_type='text/markdown; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    @action(detail=False, methods=['get'])
    def demo_scenarios(self, request):
        """Returns the catalog of Super Admin-only sample investigation scenarios."""
        return Response(DEMO_SCENARIO_CATALOG)

    @action(detail=False, methods=['post'])
    def seed_demo(self, request):
        """
        Super Admin-only endpoint to create one of the 4 themed sample SOC Investigation Response
        scenarios ('expanse', 'star_trek', 'matrix', 'star_wars', or 'all').
        """
        scenario_key = request.data.get('scenario') or 'expanse'
        try:
            created = create_demo_scenario(scenario_key)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        if scenario_key == 'all':
            serializer = self.get_serializer(created, many=True)
            return Response(
                {
                    'status': 'success',
                    'scenario': scenario_key,
                    'count': len(created),
                    'investigations': serializer.data,
                    'projects': serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )
        serializer = self.get_serializer(created[0])
        return Response(serializer.data, status=status.HTTP_201_CREATED)


ProjectViewSet = InvestigationViewSet


class EvidenceItemViewSet(viewsets.ModelViewSet):
    queryset = (
        EvidenceItem.objects.select_related('investigation', 'created_by')
        .prefetch_related('screenshots__created_by', 'pcaps__created_by')
        .all()
    )
    serializer_class = EvidenceItemSerializer
    permission_classes = [InvestigationItemPermission]

    def _save_uploaded_attachments(self, instance):
        files = self.request.FILES.getlist('screenshots_upload')
        captions = self.request.data.getlist('screenshot_captions') if hasattr(self.request.data, 'getlist') else []
        for idx, img_file in enumerate(files):
            caption = captions[idx] if idx < len(captions) else ""
            EvidenceScreenshot.objects.create(
                evidence=instance,
                image=img_file,
                caption=caption,
                analyst_name=instance.analyst_name,
                created_by=self.request.user,
            )

        pcap_files = self.request.FILES.getlist('pcaps_upload')
        pcap_descriptions = self.request.data.getlist('pcap_descriptions') if hasattr(self.request.data, 'getlist') else []
        for idx, pcap_file in enumerate(pcap_files):
            desc = pcap_descriptions[idx] if idx < len(pcap_descriptions) else ""
            EvidencePcap.objects.create(
                evidence=instance,
                file=pcap_file,
                description=desc,
                analyst_name=instance.analyst_name,
                created_by=self.request.user,
            )

    def get_queryset(self):
        qs = super().get_queryset()
        investigation_id = (
            self.request.query_params.get('investigation')
            or self.request.query_params.get('investigation_id')
            or self.request.query_params.get('project')
        )
        if investigation_id:
            qs = qs.filter(investigation_id=investigation_id)

        key_only = self.request.query_params.get('is_key_evidence')
        if key_only is not None:
            qs = qs.filter(is_key_evidence=key_only.lower() in ('1', 'true'))
        return qs

    def perform_create(self, serializer):
        inv = serializer.validated_data.get('investigation')
        assert_project_unlocked(inv)
        analyst = (serializer.validated_data.get('analyst_name') or '').strip()
        if not analyst:
            analyst = get_user_display_name(self.request.user)
        instance = serializer.save(analyst_name=analyst, created_by=self.request.user)
        self._save_uploaded_attachments(instance)
        instance.investigation.sync_timeline_events()

    def perform_update(self, serializer):
        assert_project_unlocked(serializer.instance.investigation)
        if 'investigation' in serializer.validated_data:
            assert_project_unlocked(serializer.validated_data['investigation'])
        instance = serializer.save()
        self._save_uploaded_attachments(instance)
        instance.investigation.sync_timeline_events()

    def perform_destroy(self, instance):
        inv = instance.investigation
        assert_project_unlocked(inv)
        assert_can_delete_evidence_item(self.request.user, instance)
        instance.delete()
        inv.sync_timeline_events()

    @action(detail=True, methods=['post'])
    def toggle_key(self, request, pk=None):
        item = self.get_object()
        assert_project_unlocked(item.investigation)
        item.is_key_evidence = not item.is_key_evidence
        item.save(update_fields=['is_key_evidence', 'updated_at'])
        item.investigation.sync_timeline_events()
        return Response(self.get_serializer(item).data)


class RelatedIncidentViewSet(viewsets.ModelViewSet):
    queryset = RelatedIncident.objects.select_related('investigation').all()
    serializer_class = RelatedIncidentSerializer
    permission_classes = [InvestigationItemPermission]

    def get_queryset(self):
        qs = super().get_queryset()
        inv_id = (
            self.request.query_params.get('investigation')
            or self.request.query_params.get('investigation_id')
            or self.request.query_params.get('project')
        )
        if inv_id:
            qs = qs.filter(investigation_id=inv_id)
        return qs

    def perform_create(self, serializer):
        inv = serializer.validated_data.get('investigation')
        assert_project_unlocked(inv)
        analyst = (serializer.validated_data.get('analyst_name') or '').strip()
        if not analyst:
            analyst = get_user_display_name(self.request.user)
        instance = serializer.save(analyst_name=analyst)
        instance.investigation.sync_archive_manifest()

    def perform_update(self, serializer):
        assert_project_unlocked(serializer.instance.investigation)
        if 'investigation' in serializer.validated_data:
            assert_project_unlocked(serializer.validated_data['investigation'])
        instance = serializer.save()
        instance.investigation.sync_archive_manifest()

    def perform_destroy(self, instance):
        inv = instance.investigation
        assert_project_unlocked(inv)
        instance.delete()
        inv.sync_archive_manifest()


class ExternalResearchViewSet(viewsets.ModelViewSet):
    queryset = ExternalResearch.objects.select_related('investigation').all()
    serializer_class = ExternalResearchSerializer
    permission_classes = [InvestigationItemPermission]

    def get_queryset(self):
        qs = super().get_queryset()
        inv_id = (
            self.request.query_params.get('investigation')
            or self.request.query_params.get('investigation_id')
            or self.request.query_params.get('project')
        )
        if inv_id:
            qs = qs.filter(investigation_id=inv_id)
        return qs

    def perform_create(self, serializer):
        inv = serializer.validated_data.get('investigation')
        assert_project_unlocked(inv)
        analyst = (serializer.validated_data.get('analyst_name') or '').strip()
        if not analyst:
            analyst = get_user_display_name(self.request.user)
        instance = serializer.save(analyst_name=analyst)
        instance.investigation.sync_archive_manifest()

    def perform_update(self, serializer):
        assert_project_unlocked(serializer.instance.investigation)
        if 'investigation' in serializer.validated_data:
            assert_project_unlocked(serializer.validated_data['investigation'])
        instance = serializer.save()
        instance.investigation.sync_archive_manifest()

    def perform_destroy(self, instance):
        inv = instance.investigation
        assert_project_unlocked(inv)
        instance.delete()
        inv.sync_archive_manifest()


class EvidenceScreenshotViewSet(viewsets.ModelViewSet):
    queryset = (
        EvidenceScreenshot.objects.select_related('evidence__investigation', 'created_by')
        .all()
    )
    serializer_class = EvidenceScreenshotSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    permission_classes = [InvestigationItemPermission]

    def perform_create(self, serializer):
        evidence = serializer.validated_data['evidence']
        assert_project_unlocked(evidence.investigation)
        analyst = (serializer.validated_data.get('analyst_name') or '').strip()
        if not analyst:
            analyst = get_user_display_name(self.request.user)
        instance = serializer.save(analyst_name=analyst, created_by=self.request.user)
        instance.evidence.investigation.sync_timeline_events()

    def perform_update(self, serializer):
        assert_project_unlocked(serializer.instance.evidence.investigation)
        if 'evidence' in serializer.validated_data:
            assert_project_unlocked(serializer.validated_data['evidence'].investigation)
        instance = serializer.save()
        instance.evidence.investigation.sync_timeline_events()

    def perform_destroy(self, instance):
        inv = instance.evidence.investigation
        assert_project_unlocked(inv)
        assert_can_delete_screenshot(self.request.user, instance)
        instance.delete()
        inv.sync_timeline_events()


class EvidencePcapViewSet(viewsets.ModelViewSet):
    queryset = (
        EvidencePcap.objects.select_related('evidence__investigation', 'created_by')
        .all()
    )
    serializer_class = EvidencePcapSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    permission_classes = [InvestigationItemPermission]

    def perform_create(self, serializer):
        evidence = serializer.validated_data['evidence']
        assert_project_unlocked(evidence.investigation)
        analyst = (serializer.validated_data.get('analyst_name') or '').strip()
        if not analyst:
            analyst = get_user_display_name(self.request.user)
        instance = serializer.save(analyst_name=analyst, created_by=self.request.user)
        instance.evidence.investigation.sync_timeline_events()

    def perform_update(self, serializer):
        assert_project_unlocked(serializer.instance.evidence.investigation)
        if 'evidence' in serializer.validated_data:
            assert_project_unlocked(serializer.validated_data['evidence'].investigation)
        instance = serializer.save()
        instance.evidence.investigation.sync_timeline_events()

    def perform_destroy(self, instance):
        inv = instance.evidence.investigation
        assert_project_unlocked(inv)
        assert_can_delete_pcap(self.request.user, instance)
        instance.delete()
        inv.sync_timeline_events()

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if request.query_params.get('download') in ('1', 'true'):
            if not instance.file:
                return Response({'error': 'No file available'}, status=status.HTTP_404_NOT_FOUND)
            response = HttpResponse(instance.file.read(), content_type='application/vnd.tcpdump.pcap')
            filename = instance.file.name.split('/')[-1]
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class MitreCatalogAPIView(APIView):
    """
    Returns the built-in enterprise MITRE ATT&CK Matrix tactics and techniques catalog.
    """
    permission_classes = [InvestigationItemPermission]

    def get(self, request):
        return Response(MITRE_TACTICS_WITH_TECHNIQUES)


class SOCIngestAPIView(APIView):
    """
    Integration endpoint for existing Python/Django SOC tools (SIEM, SOAR, IDS)
    to programmatically push Atomic or Search Result evidence into an investigation.
    Requires Analyst, Admin, or Super Admin credentials (e.g. `Authorization: Token <token>`).
    """
    permission_classes = [InvestigationItemPermission]

    def post(self, request):
        inv_id = (
            request.data.get('investigation_id')
            or request.data.get('investigation')
            or request.data.get('project_id')
            or request.data.get('project')
        )
        ticket_id = request.data.get('ticket_id')

        inv = None
        if inv_id:
            inv = Investigation.objects.filter(pk=inv_id).first()
        elif ticket_id:
            inv = Investigation.objects.filter(ticket_id=ticket_id).first()

        if not inv:
            return Response(
                {"error": "Specify a valid 'investigation_id' or 'ticket_id' to ingest evidence."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        assert_project_unlocked(inv)

        payload = request.data.copy()
        payload['investigation'] = inv.pk
        if not (payload.get('analyst_name') or '').strip():
            payload['analyst_name'] = get_user_display_name(request.user)
        serializer = EvidenceItemSerializer(data=payload, context={'request': request})
        serializer.is_valid(raise_exception=True)
        item = serializer.save(created_by=request.user)
        inv.sync_timeline_events()
        return Response(
            EvidenceItemSerializer(item, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )
