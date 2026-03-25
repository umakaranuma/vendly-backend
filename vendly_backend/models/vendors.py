from django.db import models

from vendly_backend.models.core import CoreUser, CoreStatus


class Category(models.Model):
    name = models.CharField(max_length=255)
    slug = models.CharField(max_length=255, unique=True)
    description = models.TextField(null=True, blank=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "categories"
        app_label = "vendly_backend"

    def __str__(self):
        return self.name


class Vendor(models.Model):
    user = models.OneToOneField(CoreUser, on_delete=models.CASCADE, related_name="vendor")
    name = models.CharField(max_length=255)
    slug = models.CharField(max_length=255, unique=True, null=True, blank=True)
    city = models.CharField(max_length=255, null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name="vendors")
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    review_count = models.IntegerField(default=0)
    price_from = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    bio = models.TextField(null=True, blank=True)
    followers_count = models.IntegerField(default=0)
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('suspended', 'Suspended'),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Admin status backing column (normalized). We keep `status` for backward compatibility.
    # New code should prefer `status_ref` when present.
    status_ref = models.ForeignKey(
        CoreStatus,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vendors",
        db_column="status_id",
    )

    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by_admin = models.ForeignKey(CoreUser, on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_vendors")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "vendors"
        app_label = "vendly_backend"
        
    def __str__(self):
        return self.name


class VendorGallery(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="gallery")
    url = models.TextField()
    sort_order = models.IntegerField(default=0)

    class Meta:
        db_table = "vendor_gallery"
        app_label = "vendly_backend"


class Listing(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="listings")
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    category = models.CharField(max_length=255, null=True, blank=True) # Free-text or FK to categories
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "listings"
        app_label = "vendly_backend"


class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=255)
    max_packages = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "subscription_plans"
        app_label = "vendly_backend"


class VendorPackage(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="packages")
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    features_text = models.TextField(null=True, blank=True)
    features_json = models.JSONField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "vendor_packages"
        app_label = "vendly_backend"


class VendorSubscription(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE, related_name="vendor_subscriptions")
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "vendor_subscriptions"
        app_label = "vendly_backend"
