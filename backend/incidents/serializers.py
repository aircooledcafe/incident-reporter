import os
from pathlib import Path
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import (
    UserProfile,
    Project,
    RelatedIncident,
    CustomerContact,
    ExternalResearch,
    EvidenceItem,
    EvidenceScreenshot,
    get_or_create_user_profile,
    get_user_display_name,
    get_user_role,
    sync_user_flags_for_role,
)
from .permissions import (
    build_user_permissions_summary,
    can_actor_modify_user,
    can_user_delete_evidence_item,
    can_user_delete_screenshot,
    validate_user_management_action,
)
from .reports import collect_mitre_summary

User = get_user_model()


class AuthUserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    role_display = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()
    preferred_display_name = serializers.SerializerMethodField()
    job_role = serializers.SerializerMethodField()
    pronouns = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'display_name',
            'preferred_display_name',
            'job_role',
            'pronouns',
            'avatar_url',
            'role',
            'role_display',
            'is_active',
            'last_login',
            'date_joined',
            'permissions',
        ]
        read_only_fields = fields

    def get_role(self, obj) -> str:
        return get_user_role(obj)

    def get_role_display(self, obj) -> str:
        profile = get_or_create_user_profile(obj)
        return profile.get_role_display()

    def get_display_name(self, obj) -> str:
        return get_user_display_name(obj)

    def get_preferred_display_name(self, obj) -> str:
        return get_or_create_user_profile(obj).preferred_display_name or ""

    def get_job_role(self, obj) -> str:
        return get_or_create_user_profile(obj).job_role or ""

    def get_pronouns(self, obj) -> str:
        return get_or_create_user_profile(obj).pronouns or ""

    def get_avatar_url(self, obj) -> str:
        profile = get_or_create_user_profile(obj)
        if not profile.avatar:
            return ""
        return f"{settings.MEDIA_URL}{profile.avatar.name}"

    def get_permissions(self, obj) -> dict:
        return build_user_permissions_summary(obj)


class ManagedUserSerializer(serializers.ModelSerializer):
    role = serializers.ChoiceField(
        choices=UserProfile.ROLE_CHOICES,
        default=UserProfile.ROLE_ANALYST,
        write_only=False,
    )
    role_display = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()
    preferred_display_name = serializers.CharField(
        required=False,
        allow_blank=True,
    )
    job_role = serializers.CharField(
        required=False,
        allow_blank=True,
    )
    pronouns = serializers.CharField(
        required=False,
        allow_blank=True,
    )
    avatar_url = serializers.SerializerMethodField()
    password = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=False,
        style={'input_type': 'password'},
    )
    can_actor_modify = serializers.SerializerMethodField()
    is_self = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'display_name',
            'preferred_display_name',
            'job_role',
            'pronouns',
            'avatar_url',
            'role',
            'role_display',
            'is_active',
            'password',
            'last_login',
            'date_joined',
            'can_actor_modify',
            'is_self',
        ]
        read_only_fields = [
            'id',
            'display_name',
            'avatar_url',
            'role_display',
            'last_login',
            'date_joined',
            'can_actor_modify',
            'is_self',
        ]

    def to_representation(self, instance):
        profile = get_or_create_user_profile(instance)
        instance.role = profile.role
        instance.preferred_display_name = profile.preferred_display_name
        instance.job_role = profile.job_role
        instance.pronouns = profile.pronouns
        return super().to_representation(instance)

    def get_role_display(self, obj) -> str:
        return get_or_create_user_profile(obj).get_role_display()

    def get_display_name(self, obj) -> str:
        return get_user_display_name(obj)

    def get_avatar_url(self, obj) -> str:
        profile = get_or_create_user_profile(obj)
        if not profile.avatar:
            return ""
        return f"{settings.MEDIA_URL}{profile.avatar.name}"

    def get_can_actor_modify(self, obj) -> bool:
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            return False
        if request.user.pk == obj.pk and get_user_role(request.user) == UserProfile.ROLE_ADMIN:
            return False
        return can_actor_modify_user(request.user, obj)

    def get_is_self(self, obj) -> bool:
        request = self.context.get('request')
        return bool(request and request.user and request.user.pk == obj.pk)

    def validate(self, attrs):
        request = self.context.get('request')
        actor = request.user if request else None
        requested_role = attrs.get('role')
        requested_is_active = attrs.get('is_active')

        if self.instance is None:
            if not attrs.get('password'):
                raise serializers.ValidationError({'password': 'A password is required when creating a user.'})
            role_to_check = requested_role or UserProfile.ROLE_ANALYST
            if actor:
                validate_user_management_action(
                    actor=actor,
                    target_user=None,
                    requested_role=role_to_check,
                    requested_is_active=requested_is_active,
                )
            temp_user = User(
                username=attrs.get('username', ''),
                email=attrs.get('email', ''),
                first_name=attrs.get('first_name', ''),
                last_name=attrs.get('last_name', ''),
            )
            try:
                validate_password(attrs['password'], user=temp_user)
            except DjangoValidationError as exc:
                raise serializers.ValidationError({'password': list(exc.messages)})
        else:
            if actor:
                validate_user_management_action(
                    actor=actor,
                    target_user=self.instance,
                    requested_role=requested_role,
                    requested_is_active=requested_is_active,
                )
            if 'password' in attrs:
                try:
                    validate_password(attrs['password'], user=self.instance)
                except DjangoValidationError as exc:
                    raise serializers.ValidationError({'password': list(exc.messages)})

        return attrs

    def create(self, validated_data):
        role = validated_data.pop('role', UserProfile.ROLE_ANALYST)
        preferred_display_name = validated_data.pop('preferred_display_name', '')
        job_role = validated_data.pop('job_role', '')
        pronouns = validated_data.pop('pronouns', '')
        password = validated_data.pop('password')
        is_super = role == UserProfile.ROLE_SUPER_ADMIN
        user = User(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            is_active=validated_data.get('is_active', True),
            is_superuser=is_super,
            is_staff=is_super,
        )
        user.set_password(password)
        user.save()
        profile = get_or_create_user_profile(user)
        profile.role = role
        profile.preferred_display_name = preferred_display_name
        profile.job_role = job_role
        profile.pronouns = pronouns
        profile.save(update_fields=['role', 'preferred_display_name', 'job_role', 'pronouns', 'updated_at'])
        sync_user_flags_for_role(user, role)
        return user

    def update(self, instance, validated_data):
        role = validated_data.pop('role', None)
        preferred_display_name = validated_data.pop('preferred_display_name', None)
        job_role = validated_data.pop('job_role', None)
        pronouns = validated_data.pop('pronouns', None)
        password = validated_data.pop('password', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)

        instance.save()

        profile = get_or_create_user_profile(instance)
        changed = False
        if role is not None and profile.role != role:
            profile.role = role
            changed = True
        if preferred_display_name is not None and profile.preferred_display_name != preferred_display_name:
            profile.preferred_display_name = preferred_display_name
            changed = True
        if job_role is not None and profile.job_role != job_role:
            profile.job_role = job_role
            changed = True
        if pronouns is not None and profile.pronouns != pronouns:
            profile.pronouns = pronouns
            changed = True
        if changed:
            profile.save()

        sync_user_flags_for_role(instance, profile.role)
        return instance


class EvidenceScreenshotSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    filename = serializers.SerializerMethodField()
    created_by_username = serializers.SerializerMethodField()
    can_actor_delete = serializers.SerializerMethodField()

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
            'created_by',
            'created_by_username',
            'can_actor_delete',
            'uploaded_at',
        ]
        read_only_fields = [
            'id',
            'created_by',
            'created_by_username',
            'can_actor_delete',
            'uploaded_at',
            'image_url',
            'filename',
        ]

    def get_image_url(self, obj):
        if not obj.image:
            return ""
        return f"{settings.MEDIA_URL}{obj.image.name}"

    def get_filename(self, obj):
        if not obj.image:
            return ""
        return os.path.basename(obj.image.name)

    def get_created_by_username(self, obj) -> str:
        if obj.created_by_id and obj.created_by:
            return obj.created_by.username
        return ""

    def get_can_actor_delete(self, obj) -> bool:
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            return False
        return can_user_delete_screenshot(request.user, obj)


class EvidenceItemSerializer(serializers.ModelSerializer):
    screenshots = EvidenceScreenshotSerializer(many=True, read_only=True)
    evidence_type_display = serializers.CharField(
        source='get_evidence_type_display',
        read_only=True,
    )
    created_by_username = serializers.SerializerMethodField()
    can_actor_delete = serializers.SerializerMethodField()

    class Meta:
        model = EvidenceItem
        fields = [
            'id',
            'project',
            'evidence_type',
            'evidence_type_display',
            'analyst_name',
            'created_by',
            'created_by_username',
            'can_actor_delete',
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
        read_only_fields = [
            'id',
            'created_by',
            'created_by_username',
            'can_actor_delete',
            'created_at',
            'updated_at',
            'evidence_type_display',
            'screenshots',
        ]

    def get_created_by_username(self, obj) -> str:
        if obj.created_by_id and obj.created_by:
            return obj.created_by.username
        return ""

    def get_can_actor_delete(self, obj) -> bool:
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            return False
        return can_user_delete_evidence_item(request.user, obj)


class RelatedIncidentSerializer(serializers.ModelSerializer):
    class Meta:
        model = RelatedIncident
        fields = [
            'id',
            'project',
            'title',
            'link',
            'analyst_name',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class CustomerContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerContact
        fields = [
            'id',
            'project',
            'name',
            'role_title',
            'email',
            'phone',
            'notes',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


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
    related_incidents = RelatedIncidentSerializer(many=True, read_only=True)
    customer_contacts = CustomerContactSerializer(many=True, read_only=True)
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
    locked_by_username = serializers.SerializerMethodField()
    locked_by_display = serializers.SerializerMethodField()

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
            'action_plan',
            'key_customer_contacts',
            'customer_contacts',
            'related_incidents',
            'key_assets_affected',
            'key_users_affected',
            'key_malicious_indicators',
            'external_research_link',
            'external_research_summary',
            'external_research_items',
            'status',
            'is_locked',
            'locked_by',
            'locked_by_username',
            'locked_by_display',
            'locked_at',
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
            'is_locked',
            'locked_by',
            'locked_by_username',
            'locked_by_display',
            'locked_at',
            'artifact_folder',
            'artifact_folder_path',
            'archive_files',
            'created_at',
            'updated_at',
        ]

    def get_locked_by_username(self, obj) -> str:
        if obj.locked_by_id and obj.locked_by:
            return obj.locked_by.username
        return ""

    def get_locked_by_display(self, obj) -> str:
        if obj.locked_by_id and obj.locked_by:
            return get_user_display_name(obj.locked_by)
        return ""

    def get_timeline_evidence(self, obj):
        items = obj.get_timeline_evidence()
        return EvidenceItemSerializer(items, many=True, context=self.context).data

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
