from django.db import models

from vendly_backend.models.core import CoreUser


class InvitationTemplate(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    style = models.CharField(max_length=255, null=True, blank=True)
    icon = models.TextField(null=True, blank=True)
    
    INVITATION_TYPE_CHOICES = (
        ('card', 'Card'),
        ('video', 'Video'),
        ('website', 'Website'),
    )
    invitation_type = models.CharField(max_length=20, choices=INVITATION_TYPE_CHOICES)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "invitation_templates"
        app_label = "vendly_backend"


class Invitation(models.Model):
    user = models.ForeignKey(CoreUser, on_delete=models.CASCADE, related_name="invitations")
    
    INVITATION_TYPE_CHOICES = (
        ('card', 'Card'),
        ('video', 'Video'),
        ('website', 'Website'),
    )
    invitation_type = models.CharField(max_length=20, choices=INVITATION_TYPE_CHOICES)
    event_type = models.CharField(max_length=255)
    template = models.ForeignKey(InvitationTemplate, on_delete=models.SET_NULL, null=True, blank=True, related_name="invitations")
    answers = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "invitations"
        app_label = "vendly_backend"
