from pathlib import Path
from django.conf import settings
from django.contrib import admin
from django.contrib.staticfiles import finders
from django.http import Http404, HttpResponse
from django.urls import path, include, re_path
from django.views.static import serve
from rest_framework.authtoken.models import Token


def protected_artifact_serve(request, path):
    """
    Serves investigation screenshots, PCAP captures, and generated report files from MEDIA_ROOT
    only to authenticated, active users (via Django session cookie or DRF API Token).
    """
    user = getattr(request, 'user', None)
    is_authed = bool(user and user.is_authenticated and user.is_active)

    if not is_authed:
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.lower().startswith('token '):
            raw_key = auth_header[6:].strip()
            token = Token.objects.select_related('user').filter(key=raw_key).first()
            if token and token.user.is_active:
                is_authed = True

    if not is_authed:
        return HttpResponse("Authentication required.", status=401)

    response = serve(request, path, document_root=settings.MEDIA_ROOT)
    if request.GET.get('download') == '1':
        safe_filename = Path(path).name.replace('"', '')
        response['Content-Disposition'] = f'attachment; filename="{safe_filename}"'
    return response


def serve_django_static(request, path):
    """
    Serves Django /admin/ static assets from STATIC_ROOT (Docker/production)
    with automatic fallback to app staticfiles finders in local development.
    """
    static_root = Path(settings.STATIC_ROOT)
    if (static_root / path).is_file():
        return serve(request, path, document_root=settings.STATIC_ROOT)
    found = finders.find(path)
    if found:
        found_path = Path(found)
        return serve(request, found_path.name, document_root=found_path.parent)
    raise Http404(f"Static file not found: {path}")


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('incidents.urls')),
    re_path(r'^artifacts/(?P<path>.*)$', protected_artifact_serve),
    re_path(r'^django-static/(?P<path>.*)$', serve_django_static),
]
