from django.db import models

from vendly_backend.models.core import CoreUser


class Session(models.Model):
    user = models.ForeignKey(CoreUser, on_delete=models.CASCADE, related_name="sessions")
    token = models.TextField()
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "sessions"
        app_label = "vendly_backend"


class Notification(models.Model):
    user = models.ForeignKey(CoreUser, on_delete=models.CASCADE, related_name="notifications")
    type = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    body = models.TextField(null=True, blank=True)
    data = models.JSONField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notifications"
        app_label = "vendly_backend"


class UserNotificationSetting(models.Model):
    user = models.OneToOneField(CoreUser, on_delete=models.CASCADE, related_name="notification_settings")
    push_enabled = models.BooleanField(default=True)
    email_enabled = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_notification_settings"
        app_label = "vendly_backend"
