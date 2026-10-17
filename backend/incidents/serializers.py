import os
from pathlib import Path
from django.conf import settings
from rest_framework import serializers
from .models import (
    Project,
    ExternalResearch,
    EvidenceItem,
    EvidenceScreenshot,
)
from .reports import collect_mitre_summary


class EvidenceScreenshotSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    filename = serializers.SerializerMethodField()

    class Meta:
        model = EvidenceScreenshot
        fields = [
            'id',
            'evidence',
            'image',
            'image_url',
            'filename',
            'caption',
            'analyst_name',
            'uploaded_at',
        ]
        read_only_fields = ['id', 'uploaded_at', 'image_url', 'filename']

    def get_image_url(self, obj):
        if not obj.image:
            return ""
        return f"{settings.MEDIA_URL}{obj.image.name}"

    def get_filename(self, obj):
        if not obj.image:
            return ""
        return os.path.basename(obj.image.name)


class EvidenceItemSerializer(serializers.ModelSerializer):
    screenshots = EvidenceScreenshotSerializer(many=True, read_only=True)
    evidence_type_display = serializers.CharField(
        source='get_evidence_type_display',
        read_only=True,
    )

    class Meta:
        model = EvidenceItem
        fields = [
            'id',
            'project',
            'evidence_type',
            'evidence_type_display',
            'analyst_name',
            'timestamp',
            'end_timestamp',
            'summary',
            'affected_asset',
            'affected_user',
            'user_created_by_attacker',
            'malicious_hosts_ips',
            'commands_run',
            'mitre_tactic',
            'mitre_technique',
            'related_log_link',
            'search_result_link',
            'search_query_link',
            'notes',
            'is_key_evidence',
            'screenshots',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'evidence_type_display', 'screenshots']


class ExternalResearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExternalResearch
        fields = [
            'id',
            'project',
            'link',
            'summary',
            'analyst_name',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class ProjectSerializer(serializers.ModelSerializer):
    external_research_items = ExternalResearchSerializer(many=True, read_only=True)
    timeline_evidence = serializers.SerializerMethodField()
    evidence_count = serializers.SerializerMethodField()
    key_evidence_count = serializers.SerializerMethodField()
    analysts_contributing = serializers.SerializerMethodField()
    mitre_summary = serializers.SerializerMethodField()
    artifact_folder_path = serializers.CharField(
        source='artifact_folder_absolute_path',
        read_only=True,
    )
    archive_files = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            'id',
            'title',
            'customer_name',
            'customer_id',
            'ticket_id',
            'ticket_link',
            'summary',
            'key_assets_affected',
            'key_users_affected',
            'key_malicious_indicators',
            'external_research_link',
            'external_research_summary',
            'external_research_items',
            'status',
            'lead_analyst',
            'artifact_folder',
            'artifact_folder_path',
            'archive_files',
            'evidence_count',
            'key_evidence_count',
            'analysts_contributing',
            'mitre_summary',
            'timeline_evidence',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'artifact_folder',
            'artifact_folder_path',
            'archive_files',
            'created_at',
            'updated_at',
        ]

    def get_timeline_evidence(self, obj):
        items = obj.get_timeline_evidence()
        return EvidenceItemSerializer(items, many=True).data

    def get_evidence_count(self, obj):
        return obj.evidence_items.count()

    def get_key_evidence_count(self, obj):
        return obj.evidence_items.filter(is_key_evidence=True).count()

    def get_analysts_contributing(self, obj):
        analysts = set()
        if obj.lead_analyst:
            analysts.add(obj.lead_analyst)
        for name in obj.evidence_items.values_list('analyst_name', flat=True):
            if name and name.strip():
                analysts.add(name.strip())
        return sorted(analysts)

    def get_mitre_summary(self, obj):
        return collect_mitre_summary(obj.get_timeline_evidence())

    def get_archive_files(self, obj):
        if not obj.artifact_folder:
            return []
        folder_path = Path(settings.ARTIFACTS_ROOT) / obj.artifact_folder
        if not folder_path.exists():
            return []
        files = []
        for file_path in sorted(folder_path.rglob("*")):
            if file_path.is_file():
                rel = file_path.relative_to(Path(settings.ARTIFACTS_ROOT))
                files.append({
                    "relative_path": str(rel),
                    "subfolder": str(file_path.parent.relative_to(folder_path)),
                    "name": file_path.name,
                    "size_bytes": file_path.stat().st_size,
                    "url": f"{settings.MEDIA_URL}{rel}",
                })
        return files
