from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("vendly_backend", "0007_chat_report_reason_status"),
    ]

    operations = [
        migrations.AlterField(
            model_name="chatreport",
            name="reason_type",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name="chatreport",
            name="status",
            field=models.CharField(default="open", max_length=50),
        ),
    ]
