from django.db import migrations, models
import django.db.models.deletion


def forwards(apps, schema_editor):
    ChatReport = apps.get_model("vendly_backend", "ChatReport")
    CoreStatus = apps.get_model("vendly_backend", "CoreStatus")

    for report in ChatReport.objects.all().iterator():
        raw_status = (getattr(report, "status_legacy", "") or "open").strip().lower() or "open"
        status_ref = CoreStatus.objects.filter(
            entity_type="chat_report",
            status_type=f"chat_report_{raw_status}",
        ).first()
        if status_ref is None:
            status_ref, _ = CoreStatus.objects.get_or_create(
                status_type=f"chat_report_{raw_status}",
                defaults={
                    "entity_type": "chat_report",
                    "name": raw_status,
                    "sort_order": 100,
                },
            )
        report.status_ref_id = status_ref.id
        report.save(update_fields=["status_ref"])


class Migration(migrations.Migration):

    dependencies = [
        ("vendly_backend", "0009_seed_chat_report_statuses"),
    ]

    operations = [
        migrations.RenameField(
            model_name="chatreport",
            old_name="status",
            new_name="status_legacy",
        ),
        migrations.AddField(
            model_name="chatreport",
            name="status_ref",
            field=models.ForeignKey(
                blank=True,
                db_column="status_id",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="chat_reports",
                to="vendly_backend.corestatus",
            ),
        ),
        migrations.RunPython(forwards, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="chatreport",
            name="status_legacy",
        ),
    ]
