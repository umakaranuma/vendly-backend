from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("vendly_backend", "0006_chat_reports"),
    ]

    operations = [
        migrations.AddField(
            model_name="chatreport",
            name="admin_action_note",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="chatreport",
            name="reason_type",
            field=models.CharField(
                choices=[
                    ("harassment", "Harassment"),
                    ("abusive_chat", "Abusive Chat"),
                    ("spam", "Spam"),
                    ("threat", "Threat"),
                    ("other", "Other"),
                ],
                default="other",
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name="chatreport",
            name="reviewed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="chatreport",
            name="reviewed_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="reviewed_chat_reports",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="chatreport",
            name="status",
            field=models.CharField(
                choices=[
                    ("open", "Open"),
                    ("in_review", "In Review"),
                    ("action_taken", "Action Taken"),
                    ("resolved", "Resolved"),
                    ("rejected", "Rejected"),
                ],
                default="open",
                max_length=20,
            ),
        ),
    ]
