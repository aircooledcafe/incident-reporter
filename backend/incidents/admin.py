from django.contrib import admin
from .models import (
    Project,
    ExternalResearch,
    EvidenceItem,
    EvidenceScreenshot,
)

admin.site.register(Project)
admin.site.register(ExternalResearch)
admin.site.register(EvidenceItem)
admin.site.register(EvidenceScreenshot)
