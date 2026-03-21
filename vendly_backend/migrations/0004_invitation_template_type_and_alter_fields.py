from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("vendly_backend", "0003_corestatus_seed"),
    ]

    operations = [
        migrations.CreateModel(
            name="InvitationTemplateType",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255, unique=True)),
                ("type_key", models.CharField(max_length=255, unique=True)),
                ("description", models.TextField(blank=True, null=True)),
                ("sort_order", models.IntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "invitation_template_types",
                "ordering": ["sort_order", "id"],
            },
        ),
        migrations.AlterField(
            model_name="invitation",
            name="invitation_type",
            field=models.CharField(max_length=50),
        ),
        migrations.AlterField(
            model_name="invitationtemplate",
            name="invitation_type",
            field=models.CharField(max_length=50),
        ),
    ]
