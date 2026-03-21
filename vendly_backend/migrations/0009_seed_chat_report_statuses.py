from django.db import migrations


def seed_chat_report_statuses(apps, schema_editor):
    CoreStatus = apps.get_model("vendly_backend", "CoreStatus")
    rows = [
        ("open", "chat_report_open", 10),
        ("in_review", "chat_report_in_review", 20),
        ("action_taken", "chat_report_action_taken", 30),
        ("resolved", "chat_report_resolved", 40),
        ("rejected", "chat_report_rejected", 50),
    ]
    for name, status_type, order in rows:
        CoreStatus.objects.get_or_create(
            status_type=status_type,
            defaults={
                "entity_type": "chat_report",
                "name": name,
                "sort_order": order,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ("vendly_backend", "0008_chat_report_text_reason_and_status"),
    ]

    operations = [
        migrations.RunPython(seed_chat_report_statuses, migrations.RunPython.noop),
    ]
