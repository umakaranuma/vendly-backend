from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("vendly_backend", "0005_invitationtemplate_type_fk"),
    ]

    operations = [
        migrations.CreateModel(
            name="ChatReport",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reason", models.TextField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("conversation", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reports", to="vendly_backend.conversation")),
                ("reporter", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="chat_reports", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "chat_reports",
            },
        ),
        migrations.CreateModel(
            name="ChatReportMessage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sender_type", models.CharField(max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("message", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reported_in", to="vendly_backend.message")),
                ("report", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reported_messages", to="vendly_backend.chatreport")),
                ("sender", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="messages_reported", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "chat_report_messages",
                "unique_together": {("report", "message")},
            },
        ),
    ]
