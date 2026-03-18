# Generated seed migration (manual) for core_status card support.
from django.db import migrations


def seed_core_statuses(apps, schema_editor):
    CoreStatus = apps.get_model("vendly_backend", "CoreStatus")
    Vendor = apps.get_model("vendly_backend", "Vendor")
    CoreUser = apps.get_model("vendly_backend", "CoreUser")

    # Vendor statuses
    vendor_pending, _ = CoreStatus.objects.update_or_create(
        status_type="vendor_pending",
        defaults={"entity_type": "vendor", "name": "pending", "sort_order": 10},
    )
    vendor_active, _ = CoreStatus.objects.update_or_create(
        status_type="vendor_active",
        defaults={"entity_type": "vendor", "name": "active", "sort_order": 20},
    )
    vendor_rejected, _ = CoreStatus.objects.update_or_create(
        status_type="vendor_rejected",
        defaults={"entity_type": "vendor", "name": "rejected", "sort_order": 30},
    )
    vendor_suspended, _ = CoreStatus.objects.update_or_create(
        status_type="vendor_suspended",
        defaults={"entity_type": "vendor", "name": "suspended", "sort_order": 40},
    )

    # Customer statuses
    customer_active, _ = CoreStatus.objects.update_or_create(
        status_type="customer_active",
        defaults={"entity_type": "customer", "name": "active", "sort_order": 10},
    )
    customer_suspended, _ = CoreStatus.objects.update_or_create(
        status_type="customer_suspended",
        defaults={"entity_type": "customer", "name": "suspended", "sort_order": 20},
    )

    # Backfill existing rows (best-effort) so admin cards show consistent names.
    Vendor.objects.filter(status_ref__isnull=True, status="pending").update(status_ref=vendor_pending)
    Vendor.objects.filter(status_ref__isnull=True, status="approved").update(status_ref=vendor_active)
    Vendor.objects.filter(status_ref__isnull=True, status="rejected").update(status_ref=vendor_rejected)
    Vendor.objects.filter(status_ref__isnull=True, status="suspended").update(status_ref=vendor_suspended)

    CoreUser.objects.filter(status_ref__isnull=True, is_active=True).update(status_ref=customer_active)
    CoreUser.objects.filter(status_ref__isnull=True, is_active=False).update(status_ref=customer_suspended)


class Migration(migrations.Migration):
    dependencies = [
        ("vendly_backend", "0002_corestatus_coreuser_status_ref_vendor_status_ref"),
    ]

    operations = [
        migrations.RunPython(seed_core_statuses, migrations.RunPython.noop),
    ]

