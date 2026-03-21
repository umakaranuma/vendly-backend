from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("vendly_backend", "0010_chat_report_status_fk"),
    ]

    operations = [
        migrations.RenameField(
            model_name="chatreport",
            old_name="status_ref",
            new_name="status",
        ),
    ]
