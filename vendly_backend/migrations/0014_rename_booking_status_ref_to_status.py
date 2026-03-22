# Rename Booking.status_ref -> Booking.status (DB column stays status_id).

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("vendly_backend", "0013_booking_status_ref"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RenameField(
                    model_name="booking",
                    old_name="status_ref",
                    new_name="status",
                ),
            ],
            database_operations=[],
        ),
    ]
