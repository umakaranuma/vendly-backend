# Booking: store status_id (CoreStatus) instead of string status; seed booking_* statuses.

import django.db.models.deletion
from django.db import migrations, models


def seed_booking_statuses_and_backfill(apps, schema_editor):
    CoreStatus = apps.get_model("vendly_backend", "CoreStatus")
    Booking = apps.get_model("vendly_backend", "Booking")

    specs = [
        ("booking_pending", "pending", 10),
        ("booking_confirmed", "confirmed", 20),
        ("booking_completed", "completed", 30),
        ("booking_cancelled", "cancelled", 40),
    ]
    by_type = {}
    for status_type, name, sort_order in specs:
        obj, _ = CoreStatus.objects.update_or_create(
            status_type=status_type,
            defaults={"entity_type": "booking", "name": name, "sort_order": sort_order},
        )
        by_type[status_type] = obj

    legacy_to_type = {
        "pending": "booking_pending",
        "confirmed": "booking_confirmed",
        "completed": "booking_completed",
        "cancelled": "booking_cancelled",
    }

    for legacy, stype in legacy_to_type.items():
        rid = by_type[stype].pk
        Booking.objects.filter(status=legacy).update(status_ref_id=rid)

    # Any unexpected / null legacy value -> pending
    pending_id = by_type["booking_pending"].pk
    Booking.objects.filter(status_ref__isnull=True).update(status_ref_id=pending_id)


class Migration(migrations.Migration):

    dependencies = [
        ("vendly_backend", "0012_alter_chatreport_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="booking",
            name="status_ref",
            field=models.ForeignKey(
                blank=True,
                db_column="status_id",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="bookings",
                to="vendly_backend.corestatus",
            ),
        ),
        migrations.RunPython(seed_booking_statuses_and_backfill, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="booking",
            name="status",
        ),
        migrations.AlterField(
            model_name="booking",
            name="status_ref",
            field=models.ForeignKey(
                db_column="status_id",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="bookings",
                to="vendly_backend.corestatus",
            ),
        ),
    ]
