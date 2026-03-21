from django.db import migrations, models
import django.db.models.deletion
from django.utils.text import slugify


def _normalize_type_key(raw_value: str) -> str:
    normalized = slugify((raw_value or "").strip()).replace("-", "_")
    return f"template_{normalized}" if normalized else "template_type"


def forwards(apps, schema_editor):
    InvitationTemplate = apps.get_model("vendly_backend", "InvitationTemplate")
    InvitationTemplateType = apps.get_model("vendly_backend", "InvitationTemplateType")

    for template in InvitationTemplate.objects.all().iterator():
        raw_type = getattr(template, "invitation_type_legacy", "") or ""
        type_key = _normalize_type_key(raw_type)
        default_name = (raw_type or "Type").strip().title() or "Type"

        type_obj, _ = InvitationTemplateType.objects.get_or_create(
            type_key=type_key,
            defaults={"name": default_name, "is_active": True, "sort_order": 0},
        )
        template.invitation_type_id = type_obj.id
        template.save(update_fields=["invitation_type"])


class Migration(migrations.Migration):

    dependencies = [
        ("vendly_backend", "0004_invitation_template_type_and_alter_fields"),
    ]

    operations = [
        migrations.RenameField(
            model_name="invitationtemplate",
            old_name="invitation_type",
            new_name="invitation_type_legacy",
        ),
        migrations.AddField(
            model_name="invitationtemplate",
            name="invitation_type",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="templates",
                to="vendly_backend.invitationtemplatetype",
            ),
        ),
        migrations.RunPython(forwards, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="invitationtemplate",
            name="invitation_type_legacy",
        ),
    ]
