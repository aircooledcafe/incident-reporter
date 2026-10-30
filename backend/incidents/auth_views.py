from django.contrib.auth import (
    authenticate,
    get_user_model,
    login,
    logout,
    update_session_auth_hash,
)
from django.contrib.auth.password_validation import validate_password
from django.contrib.sessions.models import Session
from django.core.exceptions import ValidationError as DjangoValidationError
from django.middleware.csrf import get_token
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import permissions, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    UserProfile,
    get_or_create_user_profile,
    get_user_display_name,
    sync_user_flags_for_role,
)
from .permissions import (
    UserManagementPermission,
    can_write_investigations,
    validate_user_management_action,
)
from .serializers import AuthUserSerializer, ManagedUserSerializer

User = get_user_model()


def _invalidate_user_sessions(target_user, keep_session_key: str | None = None) -> None:
    """Deletes active Django database sessions belonging to `target_user`."""
    active_sessions = Session.objects.filter(expire_date__gte=timezone.now())
    target_uid = str(target_user.pk)
    for session in active_sessions:
        if keep_session_key and session.session_key == keep_session_key:
            continue
        try:
            decoded = session.get_decoded()
        except Exception:
            continue
        if str(decoded.get('_auth_user_id')) == target_uid:
            session.delete()


@method_decorator(ensure_csrf_cookie, name='dispatch')
class AuthStatusAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        csrf_token = get_token(request)
        needs_setup = not User.objects.exists()
        if request.user and request.user.is_authenticated and request.user.is_active:
            return Response({
                "authenticated": True,
                "needs_initial_setup": False,
                "csrf_token": csrf_token,
                "user": AuthUserSerializer(request.user).data,
            })
        return Response({
            "authenticated": False,
            "needs_initial_setup": needs_setup,
            "csrf_token": csrf_token,
            "user": None,
        })


class InitialSetupAPIView(APIView):
    """
    First-run bootstrap endpoint allowing creation of the initial Super Admin account
    ONLY when zero users exist in the database. Permanently disabled once any user exists.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        if User.objects.exists():
            raise PermissionDenied(
                "Initial setup has already been completed. Sign in with an existing account."
            )

        username = (request.data.get('username') or '').strip()
        password = request.data.get('password') or ''
        email = (request.data.get('email') or '').strip()
        first_name = (request.data.get('first_name') or '').strip()
        last_name = (request.data.get('last_name') or '').strip()

        if not username:
            return Response(
                {"username": ["Username is required."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not password:
            return Response(
                {"password": ["Password is required."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        temp_user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
        )
        try:
            validate_password(password, user=temp_user)
        except DjangoValidationError as exc:
            return Response(
                {"password": list(exc.messages)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )
        profile = get_or_create_user_profile(user)
        profile.role = UserProfile.ROLE_SUPER_ADMIN
        profile.save(update_fields=['role', 'updated_at'])
        sync_user_flags_for_role(user, UserProfile.ROLE_SUPER_ADMIN)

        login(request, user)
        return Response(
            {
                "authenticated": True,
                "csrf_token": get_token(request),
                "user": AuthUserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = (request.data.get('username') or '').strip()
        password = request.data.get('password') or ''

        if not username or not password:
            return Response(
                {"detail": "Username and password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate(request, username=username, password=password)
        if user is None or not user.is_active:
            return Response(
                {"detail": "Invalid username or password, or account is disabled."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        get_or_create_user_profile(user)
        login(request, user)
        return Response({
            "authenticated": True,
            "csrf_token": get_token(request),
            "user": AuthUserSerializer(user).data,
        })


class LogoutAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({
            "authenticated": False,
            "csrf_token": get_token(request),
            "detail": "Signed out successfully.",
        })


class ChangeOwnPasswordAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        current_password = request.data.get('current_password') or ''
        new_password = request.data.get('new_password') or ''

        if not request.user.check_password(current_password):
            return Response(
                {"current_password": ["Current password is incorrect."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            validate_password(new_password, user=request.user)
        except DjangoValidationError as exc:
            return Response(
                {"new_password": list(exc.messages)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        request.user.set_password(new_password)
        request.user.save(update_fields=['password'])
        update_session_auth_hash(request, request.user)
        _invalidate_user_sessions(
            request.user,
            keep_session_key=request.session.session_key,
        )
        return Response({"detail": "Password updated successfully."})


class APITokenAPIView(APIView):
    """
    Allows Analyst, Admin, and Super Admin users to view or rotate their DRF API token
    for programmatic SOC tool evidence ingestion (`POST /api/soc/ingest/`).
    """
    permission_classes = [permissions.IsAuthenticated]

    def _check_access(self, request):
        if not can_write_investigations(request.user):
            raise PermissionDenied(
                "Executive (read-only) accounts cannot generate SOC ingestion API tokens."
            )

    def get(self, request):
        self._check_access(request)
        token, _ = Token.objects.get_or_create(user=request.user)
        return Response({"token": token.key, "created": token.created})

    def post(self, request):
        self._check_access(request)
        Token.objects.filter(user=request.user).delete()
        token = Token.objects.create(user=request.user)
        return Response({"token": token.key, "created": token.created})


class AnalystDirectoryAPIView(APIView):
    """
    Returns active non-executive users (Analysts, Admins, Super Admins) for UI analyst autocomplete.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        users = (
            User.objects.filter(is_active=True)
            .select_related('profile')
            .order_by('first_name', 'last_name', 'username')
        )
        results = []
        for u in users:
            profile = get_or_create_user_profile(u)
            if profile.role != UserProfile.ROLE_EXECUTIVE:
                results.append({
                    "id": u.pk,
                    "username": u.username,
                    "display_name": get_user_display_name(u),
                    "role": profile.role,
                    "role_display": profile.get_role_display(),
                })
        return Response(results)


class UserViewSet(viewsets.ModelViewSet):
    """
    User account administration:
    - SUPER_ADMIN: Full access to create, modify, reset passwords, and delete SUPER_ADMIN, ADMIN, ANALYST, and EXECUTIVE accounts.
    - ADMIN: Access to view users and create, assign roles (ANALYST / EXECUTIVE), activate/deactivate, reset passwords, and delete lesser users (ANALYST and EXECUTIVE) only.
    """
    queryset = User.objects.select_related('profile').all().order_by('username')
    serializer_class = ManagedUserSerializer
    permission_classes = [UserManagementPermission]

    def perform_update(self, serializer):
        was_active = serializer.instance.is_active
        instance = serializer.save()
        if was_active and not instance.is_active:
            Token.objects.filter(user=instance).delete()
            _invalidate_user_sessions(instance)

    def perform_destroy(self, instance):
        validate_user_management_action(
            actor=self.request.user,
            target_user=instance,
            is_delete=True,
        )
        Token.objects.filter(user=instance).delete()
        _invalidate_user_sessions(instance)
        instance.delete()

    @action(detail=True, methods=['post'])
    def reset_password(self, request, pk=None):
        target_user = self.get_object()
        validate_user_management_action(
            actor=request.user,
            target_user=target_user,
        )

        new_password = request.data.get('new_password') or ''
        if not new_password:
            return Response(
                {"new_password": ["A new password is required."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            validate_password(new_password, user=target_user)
        except DjangoValidationError as exc:
            return Response(
                {"new_password": list(exc.messages)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        target_user.set_password(new_password)
        target_user.save(update_fields=['password'])
        Token.objects.filter(user=target_user).delete()

        if target_user.pk == request.user.pk:
            update_session_auth_hash(request, target_user)
            _invalidate_user_sessions(
                target_user,
                keep_session_key=request.session.session_key,
            )
        else:
            _invalidate_user_sessions(target_user)

        return Response({
            "detail": f"Password reset successfully for '{target_user.username}'."
        })
