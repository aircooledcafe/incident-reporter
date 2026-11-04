from django.db import migrations
import re


def renumber_investigation_ids_from_zero(apps, schema_editor):
    Investigation = apps.get_model('investigations', 'Investigation')

    # Remap legacy 100000-offset IDs (e.g. INV100001 -> INV000001, INV100009 -> INV000009)
    for inv in Investigation.objects.all().order_by('id'):
        if inv.investigation_id:
            match = re.match(r'^INV10(\d{4})$', inv.investigation_id)
            if match:
                val = int(match.group(1))
                new_id = f"INV{val:06d}"
                if not Investigation.objects.filter(investigation_id=new_id).exclude(id=inv.id).exists():
                    inv.investigation_id = new_id
                    inv.save(update_fields=['investigation_id'])
                else:
                    n = 1
                    cand = f"INV{n:06d}"
                    while Investigation.objects.filter(investigation_id=cand).exclude(id=inv.id).exists():
                        n += 1
                        cand = f"INV{n:06d}"
                    inv.investigation_id = cand
                    inv.save(update_fields=['investigation_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('investigations', '0002_investigation_investigation_id'),
    ]

    operations = [
        migrations.RunPython(renumber_investigation_ids_from_zero, migrations.RunPython.noop),
    ]
