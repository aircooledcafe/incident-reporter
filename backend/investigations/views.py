from pathlib import Path
from django.db import transaction
from django.db.models import Count, Q
from django.http import FileResponse, Http404, HttpResponse
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
    is_valid_pk_int,
    suppress_timeline_sync,
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
    can_write_investigations,
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


def _clean_query_str(value) -> str:
    if value is None:
        return ""
    return str(value).replace("\x00", "").strip()


def _filter_by_customer_param(qs, cust_param, fk_field: str = "customer_id", code_lookup: str = "customer__customer_id__iexact"):
    cust_str = _clean_query_str(cust_param)
    if not cust_str:
        return qs
    if is_valid_pk_int(cust_str):
        return qs.filter(Q(**{fk_field: int(cust_str)}) | Q(**{code_lookup: cust_str}))
    return qs.filter(**{code_lookup: cust_str})


def _filter_by_investigation_param(qs, inv_param):
    inv_str = _clean_query_str(inv_param)
    if not inv_str:
        return qs
    if is_valid_pk_int(inv_str):
        return qs.filter(
            Q(investigation_id=int(inv_str)) |
            Q(investigation__investigation_id__iexact=inv_str)
        )
    return qs.filter(investigation__investigation_id__iexact=inv_str)


def _safe_header_filename(raw_name: str, fallback: str = "download.bin") -> str:
    name = Path(raw_name or "").name
    cleaned = "".join(ch for ch in name if ch >= " " and ch not in ('"', "\\", "\x7f")).strip()
    return cleaned or fallback


class CustomerViewSet(viewsets.ModelViewSet):
    """
    CRUD API for Customer entities and directory management.
    """
    queryset = (
        Customer.objects.annotate(investigations_count_val=Count('investigations', distinct=True))
        .prefetch_related('contacts')
        .all()
    )
    serializer_class = CustomerSerializer
    permission_classes = [CustomerAccessPermission]

    def get_object(self):
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup_value = _clean_query_str(self.kwargs.get(lookup_url_kwarg, ''))
        if not lookup_value:
            raise Http404("No Customer specified.")
        queryset = self.filter_queryset(self.get_queryset())
        obj = queryset.filter(customer_id__iexact=lookup_value).first()
        if not obj and is_valid_pk_int(lookup_value):
            obj = queryset.filter(pk=int(lookup_value)).first()
        if not obj:
            raise Http404(f"No Customer found matching '{lookup_value}'.")
        self.check_object_permissions(self.request, obj)
        return obj

    def perform_destroy(self, instance):
        inv_count = instance.investigations.count()
        if inv_count > 0:
            raise PermissionDenied(
                f"Cannot delete customer '{instance.name}' because it has {inv_count} associated investigation(s). "
                f"Reassign or delete the investigations first."
            )
        instance.delete()

    @action(detail=True, methods=['get'])
    def investigations(self, request, pk=None):
        customer = self.get_object()
        invs = InvestigationViewSet.queryset.filter(customer=customer)
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
            qs = _filter_by_customer_param(qs, customer_id)
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
        .prefetch_related(
            'customer__contacts',
            'related_incidents',
            'external_research_items',
            'evidence_items__created_by',
            'evidence_items__screenshots__created_by',
            'evidence_items__pcaps__created_by',
        )
        .all()
    )
    serializer_class = InvestigationSerializer
    permission_classes = [InvestigationAccessPermission]

    def get_object(self):
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup_value = _clean_query_str(self.kwargs.get(lookup_url_kwarg, ''))
        if not lookup_value:
            raise Http404("No Investigation specified.")
        queryset = self.filter_queryset(self.get_queryset())
        obj = queryset.filter(investigation_id__iexact=lookup_value).first()
        if not obj and is_valid_pk_int(lookup_value):
            obj = queryset.filter(pk=int(lookup_value)).first()
        if not obj:
            raise Http404(f"No Investigation found matching '{lookup_value}'.")
        self.check_object_permissions(self.request, obj)
        return obj

    def get_queryset(self):
        qs = super().get_queryset()
        cust_param = self.request.query_params.get('customer') or self.request.query_params.get('customer_id')
        if cust_param:
            qs = _filter_by_customer_param(qs, cust_param)
        status_param = _clean_query_str(self.request.query_params.get('status'))
        if status_param:
            qs = qs.filter(status=status_param.upper())
        inv_code = self.request.query_params.get('investigation_id') or self.request.query_params.get('code')
        if inv_code:
            cleaned_code = _clean_query_str(inv_code)
            if cleaned_code:
                qs = qs.filter(investigation_id__iexact=cleaned_code)
        return qs

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
        save_kwargs = {}
        has_lead_str = 'lead_analyst' in serializer.validated_data
        has_lead_user = 'lead_analyst_user' in serializer.validated_data
        lead = (serializer.validated_data.get('lead_analyst') or '').strip()
        lead_user = (
            serializer.validated_data['lead_analyst_user']
            if has_lead_user
            else serializer.instance.lead_analyst_user
        )
        if lead_user and ((has_lead_str and not lead) or (has_lead_user and not lead) or not (lead or serializer.instance.lead_analyst)):
            save_kwargs['lead_analyst'] = get_user_display_name(lead_user)
        elif has_lead_str:
            save_kwargs['lead_analyst'] = lead
        instance = serializer.save(**save_kwargs)
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
        Super Admin-only endpoint to create one of the 5 themed sample SOC Investigation Response
        scenarios ('expanse', 'star_trek', 'matrix', 'star_wars', 'god_of_war', or 'all').
        """
        scenario_key = _clean_query_str(request.data.get('scenario')) or 'expanse'
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

    @action(detail=True, methods=['post'], url_path='bulk-evidence')
    def bulk_evidence(self, request, pk=None):
        """Allows bulk ingestion of evidence items directly tied to this investigation."""
        investigation = self.get_object()
        return EvidenceItemViewSet().handle_bulk_create_payload(request, target_investigation=investigation)

    @action(detail=True, methods=['post'], url_path='bulk_evidence')
    def bulk_evidence_underscore(self, request, pk=None):
        investigation = self.get_object()
        return EvidenceItemViewSet().handle_bulk_create_payload(request, target_investigation=investigation)


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
            caption = (captions[idx] if idx < len(captions) else "").replace("\x00", "")
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
            desc = (pcap_descriptions[idx] if idx < len(pcap_descriptions) else "").replace("\x00", "")
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
            qs = _filter_by_investigation_param(qs, investigation_id)

        key_only = self.request.query_params.get('is_key_evidence')
        if key_only is not None:
            qs = qs.filter(is_key_evidence=_clean_query_str(key_only).lower() in ('1', 'true'))
        return qs

    def perform_create(self, serializer):
        inv = serializer.validated_data.get('investigation')
        assert_project_unlocked(inv)
        analyst = (serializer.validated_data.get('analyst_name') or '').strip()
        if not analyst:
            analyst = get_user_display_name(self.request.user)
        with suppress_timeline_sync():
            instance = serializer.save(analyst_name=analyst, created_by=self.request.user)
            self._save_uploaded_attachments(instance)
        instance.investigation.sync_timeline_events()

    def perform_update(self, serializer):
        old_inv = serializer.instance.investigation
        assert_project_unlocked(old_inv)
        if 'investigation' in serializer.validated_data:
            assert_project_unlocked(serializer.validated_data['investigation'])
        with suppress_timeline_sync():
            instance = serializer.save()
            self._save_uploaded_attachments(instance)
        if old_inv.pk != instance.investigation_id:
            old_inv.sync_timeline_events()
        instance.investigation.sync_timeline_events()

    def perform_destroy(self, instance):
        inv = instance.investigation
        assert_project_unlocked(inv)
        assert_can_delete_evidence_item(self.request.user, instance)
        instance.delete()

    @action(detail=True, methods=['post'])
    def toggle_key(self, request, pk=None):
        item = self.get_object()
        assert_project_unlocked(item.investigation)
        item.is_key_evidence = not item.is_key_evidence
        item.save(update_fields=['is_key_evidence', 'updated_at'])
        return Response(self.get_serializer(item).data)

    @action(detail=False, methods=['post'], url_path='bulk_create')
    def bulk_create(self, request):
        return self.handle_bulk_create_payload(request)

    @action(detail=False, methods=['post'], url_path='bulk')
    def bulk(self, request):
        return self.handle_bulk_create_payload(request)

    @action(detail=False, methods=['post'], url_path='bulk-create')
    def bulk_dash(self, request):
        return self.handle_bulk_create_payload(request)

    def handle_bulk_create_payload(self, request, target_investigation=None):
        if not can_write_investigations(request.user):
            raise PermissionDenied(
                "Executive accounts are read-only and cannot create investigation items."
            )

        data = request.data
        if isinstance(data, list):
            raw_items = data
            default_investigation_id = target_investigation.id if target_investigation else None
        elif isinstance(data, dict):
            raw_items = data.get('items') if 'items' in data else data.get('evidence_items')
            if raw_items is None:
                return Response(
                    {'error': "Expected a JSON payload with an 'items' array or a JSON array of items."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            default_investigation_id = (
                target_investigation.id
                if target_investigation
                else (data.get('investigation') or data.get('project'))
            )
        else:
            return Response(
                {'error': "Expected a JSON object with 'items' array or a JSON array of items."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not isinstance(raw_items, list) or len(raw_items) == 0:
            return Response(
                {'error': "'items' must be a non-empty array of evidence items."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        validated_serializers = []
        investigations_cache = {}
        if target_investigation:
            investigations_cache[target_investigation.id] = target_investigation

        errors = []
        for idx, item in enumerate(raw_items):
            if not isinstance(item, dict):
                errors.append({'index': idx, 'error': 'Item must be a JSON object.'})
                continue

            item_data = item.copy()
            inv_id = item_data.get('investigation') or item_data.get('project') or default_investigation_id
            if not inv_id:
                errors.append({
                    'index': idx,
                    'error': "Missing 'investigation'. Specify at top level or per item.",
                })
                continue
            item_data['investigation'] = inv_id

            if inv_id not in investigations_cache:
                inv_str = _clean_query_str(inv_id)
                inv_obj = Investigation.objects.filter(investigation_id__iexact=inv_str).first() if inv_str else None
                if not inv_obj and is_valid_pk_int(inv_str):
                    inv_obj = Investigation.objects.filter(pk=int(inv_str)).first()
                if not inv_obj:
                    errors.append({
                        'index': idx,
                        'error': f"Investigation '{inv_id}' does not exist.",
                    })
                    continue
                investigations_cache[inv_id] = inv_obj
                investigations_cache[inv_obj.id] = inv_obj
                investigations_cache[inv_obj.investigation_id] = inv_obj

            inv_obj = investigations_cache[inv_id]
            item_data['investigation'] = inv_obj.pk
            try:
                assert_project_unlocked(inv_obj)
            except Exception as lock_err:
                errors.append({'index': idx, 'error': str(lock_err)})
                continue

            serializer = EvidenceItemSerializer(data=item_data, context={'request': request})
            if not serializer.is_valid():
                errors.append({'index': idx, 'errors': serializer.errors})
            else:
                validated_serializers.append((serializer, inv_obj))

        if errors:
            return Response(
                {
                    'error': 'Validation failed for one or more evidence items. No items were saved.',
                    'details': errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        default_analyst = get_user_display_name(request.user)
        created_instances = []
        investigations_to_sync = set()

        with transaction.atomic():
            with suppress_timeline_sync():
                for serializer, inv_obj in validated_serializers:
                    analyst = (serializer.validated_data.get('analyst_name') or '').strip()
                    if not analyst:
                        analyst = default_analyst
                    instance = serializer.save(analyst_name=analyst, created_by=request.user)
                    created_instances.append(instance)
                    investigations_to_sync.add(inv_obj)

            for inv in investigations_to_sync:
                inv.sync_timeline_events()

        resp_serializer = EvidenceItemSerializer(
            created_instances,
            many=True,
            context={'request': request},
        )
        return Response(
            {
                'status': 'success',
                'count': len(created_instances),
                'items': resp_serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )


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
            qs = _filter_by_investigation_param(qs, inv_id)
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
            qs = _filter_by_investigation_param(qs, inv_id)
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
        serializer.save(analyst_name=analyst, created_by=self.request.user)

    def perform_update(self, serializer):
        old_inv = serializer.instance.evidence.investigation
        assert_project_unlocked(old_inv)
        if 'evidence' in serializer.validated_data:
            assert_project_unlocked(serializer.validated_data['evidence'].investigation)
        instance = serializer.save()
        if old_inv.pk != instance.evidence.investigation_id:
            old_inv.sync_timeline_events()

    def perform_destroy(self, instance):
        inv = instance.evidence.investigation
        assert_project_unlocked(inv)
        assert_can_delete_screenshot(self.request.user, instance)
        instance.delete()


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
        serializer.save(analyst_name=analyst, created_by=self.request.user)

    def perform_update(self, serializer):
        old_inv = serializer.instance.evidence.investigation
        assert_project_unlocked(old_inv)
        if 'evidence' in serializer.validated_data:
            assert_project_unlocked(serializer.validated_data['evidence'].investigation)
        instance = serializer.save()
        if old_inv.pk != instance.evidence.investigation_id:
            old_inv.sync_timeline_events()

    def perform_destroy(self, instance):
        inv = instance.evidence.investigation
        assert_project_unlocked(inv)
        assert_can_delete_pcap(self.request.user, instance)
        instance.delete()

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if _clean_query_str(request.query_params.get('download')).lower() in ('1', 'true'):
            if not instance.file or not instance.file.storage.exists(instance.file.name):
                return Response({'error': 'No file available'}, status=status.HTTP_404_NOT_FOUND)
            filename = _safe_header_filename(instance.file.name, fallback='capture.pcap')
            response = FileResponse(
                instance.file.open('rb'),
                content_type='application/vnd.tcpdump.pcap',
            )
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
            inv_str = _clean_query_str(inv_id)
            if inv_str:
                inv = Investigation.objects.filter(investigation_id__iexact=inv_str).first()
                if not inv and is_valid_pk_int(inv_str):
                    inv = Investigation.objects.filter(pk=int(inv_str)).first()
        elif ticket_id:
            cleaned_ticket = _clean_query_str(ticket_id)
            if cleaned_ticket:
                inv = Investigation.objects.filter(ticket_id__iexact=cleaned_ticket).order_by('-updated_at').first()

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
        return Response(
            EvidenceItemSerializer(item, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )
