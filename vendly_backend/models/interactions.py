from django.db import models

from vendly_backend.models.core import CoreUser
from vendly_backend.models.vendors import Vendor


class UserFavoriteVendor(models.Model):
    user = models.ForeignKey(CoreUser, on_delete=models.CASCADE, related_name="favorites")
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="favorited_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_favorite_vendors"
        app_label = "vendly_backend"
        unique_together = ("user", "vendor")


class VendorView(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="views")
    user = models.ForeignKey(CoreUser, on_delete=models.SET_NULL, null=True, blank=True, related_name="vendor_views")
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "vendor_views"
        app_label = "vendly_backend"


class AuditLog(models.Model):
    actor = models.ForeignKey(CoreUser, on_delete=models.CASCADE, related_name="audit_logs")
    action = models.CharField(max_length=255)
    resource_type = models.CharField(max_length=255, null=True, blank=True)
    resource_id = models.IntegerField(null=True, blank=True)
    payload = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_log"
        app_label = "vendly_backend"
