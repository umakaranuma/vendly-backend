from django.db import models

from vendly_backend.models.core import CoreStatus, CoreUser
from vendly_backend.models.vendors import Vendor, VendorPackage


class Booking(models.Model):
    customer = models.ForeignKey(CoreUser, on_delete=models.CASCADE, related_name="bookings")
    # User who submitted the booking (customer self-booking, or vendor initiating a request to another vendor).
    requested_by = models.ForeignKey(
        CoreUser,
        on_delete=models.CASCADE,
        related_name="requested_bookings",
    )
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="bookings")
    vendor_package = models.ForeignKey(
        VendorPackage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bookings",
    )
    event_type = models.CharField(max_length=255)
    booking_date = models.DateTimeField()
    location = models.CharField(max_length=255, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    deposit = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    status = models.ForeignKey(
        CoreStatus,
        on_delete=models.PROTECT,
        related_name="bookings",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bookings"
        app_label = "vendly_backend"


class VendorReview(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name="review")
    reviewer = models.ForeignKey(CoreUser, on_delete=models.CASCADE, related_name="reviews")
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="reviews")
    rating = models.DecimalField(max_digits=3, decimal_places=2)
    comment = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "vendor_reviews"
        app_label = "vendly_backend"
