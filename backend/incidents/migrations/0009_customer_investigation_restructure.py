# Migration to restructure models into Customer and Investigation

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def migrate_projects_and_contacts(apps, schema_editor):
    Customer = apps.get_model('incidents', 'Customer')
    Project = apps.get_model('incidents', 'Project')
    CustomerContact = apps.get_model('incidents', 'CustomerContact')

    default_customer, _ = Customer.objects.get_or_create(
        name="Default Organization",
        defaults={
            "customer_id": "DEFAULT-ORG",
            "notes": "System default organization for existing investigations.",
        },
    )

    for p in Project.objects.all():
        raw_name = (getattr(p, 'customer_name', '') or '').strip()
        raw_code = (getattr(p, 'legacy_customer_code', '') or '').strip()
        name = raw_name or f"Customer {p.pk}"
        code = raw_code or f"CUST-{p.pk}"

        if Customer.objects.filter(customer_id=code).exclude(name=name).exists():
            code = f"{code}-{p.pk}"

        cust, _ = Customer.objects.get_or_create(
            name=name,
            defaults={
                "customer_id": code,
                "notes": f"Migrated from existing investigation #{p.pk}",
            },
        )
        p.customer = cust
        p.save(update_fields=['customer'])

        for contact in CustomerContact.objects.filter(project_id=p.pk):
            contact.customer = cust
            contact.save(update_fields=['customer'])

    for contact in CustomerContact.objects.filter(customer__isnull=True):
        contact.customer = default_customer
        contact.save(update_fields=['customer'])


class Migration(migrations.Migration):

    dependencies = [
        ('incidents', '0008_evidencepcap'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # 1. Rename existing Project.customer_id to legacy_customer_code to free up the column name
        migrations.RenameField(
            model_name='project',
            old_name='customer_id',
            new_name='legacy_customer_code',
        ),

        # 2. Create Customer
        migrations.CreateModel(
            name='Customer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
                ('customer_id', models.CharField(max_length=64, unique=True)),
                ('notes', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),

        # 3. Add temporary nullable customer to Project
        migrations.AddField(
            model_name='project',
            name='customer',
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='investigations',
                to='incidents.customer',
            ),
        ),

        # 4. Add temporary nullable customer to CustomerContact
        migrations.AddField(
            model_name='customercontact',
            name='customer',
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='contacts',
                to='incidents.customer',
            ),
        ),

        # 5. Data migration
        migrations.RunPython(migrate_projects_and_contacts, migrations.RunPython.noop),

        # 6. Make customer non-nullable on CustomerContact and add escalation_tier & updated_at
        migrations.AlterField(
            model_name='customercontact',
            name='customer',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='contacts',
                to='incidents.customer',
            ),
        ),
        migrations.AddField(
            model_name='customercontact',
            name='escalation_tier',
            field=models.CharField(
                choices=[('PRIMARY', 'Primary'), ('SECONDARY', 'Secondary'), ('TERTIARY', 'Tertiary')],
                default='PRIMARY',
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name='customercontact',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name='customercontact',
            name='email',
            field=models.EmailField(blank=True, default='', max_length=254),
        ),
        migrations.AlterField(
            model_name='customercontact',
            name='notes',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='customercontact',
            name='phone',
            field=models.CharField(blank=True, default='', max_length=64),
        ),
        migrations.RemoveField(
            model_name='customercontact',
            name='project',
        ),
        migrations.AlterModelOptions(
            name='customercontact',
            options={'ordering': ['escalation_tier', 'created_at']},
        ),

        # 7. Make customer non-nullable on Project
        migrations.AlterField(
            model_name='project',
            name='customer',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='investigations',
                to='incidents.customer',
            ),
        ),

        # 8. Add timeline_events & lead_analyst_user to Project
        migrations.AddField(
            model_name='project',
            name='timeline_events',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='project',
            name='lead_analyst_user',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='led_investigations',
                to=settings.AUTH_USER_MODEL,
            ),
        ),

        # 9. Remove legacy customer_name and legacy_customer_code fields from Project
        migrations.RemoveField(
            model_name='project',
            name='customer_name',
        ),
        migrations.RemoveField(
            model_name='project',
            name='legacy_customer_code',
        ),

        # 10. Rename Model Project to Investigation
        migrations.RenameModel(
            old_name='Project',
            new_name='Investigation',
        ),

        # 11. Update ForeignKey references from project to investigation
        migrations.RenameField(
            model_name='evidenceitem',
            old_name='project',
            new_name='investigation',
        ),
        migrations.RenameField(
            model_name='relatedincident',
            old_name='project',
            new_name='investigation',
        ),
        migrations.RenameField(
            model_name='externalresearch',
            old_name='project',
            new_name='investigation',
        ),
    ]
