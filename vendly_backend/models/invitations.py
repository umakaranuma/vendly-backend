from django.db import models
from django.utils.text import slugify

from vendly_backend.models.core import CoreUser


class InvitationTemplateType(models.Model):
    name = models.CharField(max_length=255, unique=True)
    type_key = models.CharField(max_length=255, unique=True)
    description = models.TextField(null=True, blank=True)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "invitation_template_types"
        app_label = "vendly_backend"
        ordering = ["sort_order", "id"]

    def save(self, *args, **kwargs):
        if not self.type_key:
            normalized = slugify(self.name or "").replace("-", "_")
            self.type_key = f"template_{normalized}" if normalized else "template_type"
        super().save(*args, **kwargs)


class InvitationTemplate(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    style = models.CharField(max_length=255, null=True, blank=True)
    icon = models.TextField(null=True, blank=True)
    
    invitation_type = models.ForeignKey(
        InvitationTemplateType,
        on_delete=models.PROTECT,
        related_name="templates",
        null=True,
        blank=True,
    )
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "invitation_templates"
        app_label = "vendly_backend"


class Invitation(models.Model):
    user = models.ForeignKey(CoreUser, on_delete=models.CASCADE, related_name="invitations")
    
    invitation_type = models.CharField(max_length=50)
    event_type = models.CharField(max_length=255)
    template = models.ForeignKey(InvitationTemplate, on_delete=models.SET_NULL, null=True, blank=True, related_name="invitations")
    answers = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "invitations"
        app_label = "vendly_backend"
