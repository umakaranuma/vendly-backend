from datetime import datetime, timedelta
from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status

from mServices.ResponseService import ResponseService
from mServices.ValidatorService import ValidatorService
from vendly_backend.models import Booking, Vendor, VendorAvailability
from vendly_backend.booking_statuses import get_booking_status_ref

def _vendor_for_user(user):
    try:
        return user.vendor
    except Vendor.DoesNotExist:
        return None

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def vendor_calendar_view(request: Request, vendor_id: int) -> Response:
    """
    Returns confirmed bookings and manual availability for a vendor.
    Used by the calendar view on the vendor profile.
    """
    try:
        vendor = Vendor.objects.get(id=vendor_id)
    except Vendor.DoesNotExist:
        return ResponseService.response("NOT_FOUND", {}, "Vendor not found.", status.HTTP_404_NOT_FOUND)

    # Date range from query params (default to current month)
    start_date_str = request.GET.get("start_date")
    end_date_str = request.GET.get("end_date")

    if start_date_str:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    else:
        start_date = datetime.now().date().replace(day=1)
    
    if end_date_str:
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    else:
        end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(days=1)

    # 1. Fetch confirmed bookings
    confirmed_status = get_booking_status_ref("confirmed")
    bookings = Booking.objects.filter(
        vendor=vendor,
        status=confirmed_status,
        booking_date__date__range=[start_date, end_date]
    ).values("id", "booking_date", "event_type")

    # 2. Fetch manual availability overrides
    availabilities = VendorAvailability.objects.filter(
        vendor=vendor,
        date__range=[start_date, end_date]
    ).values("date", "is_available", "reason")

    # Format response
    booked_dates = []
    for b in bookings:
        booked_dates.append({
            "type": "booking",
            "id": b["id"],
            "date": b["booking_date"].date().isoformat(),
            "label": b["event_type"],
            "is_available": False
        })
    
    manual_entries = []
    for a in availabilities:
        manual_entries.append({
            "type": "manual",
            "date": a["date"].isoformat(),
            "is_available": a["is_available"],
            "label": a["reason"] or ("Available" if a["is_available"] else "Blocked")
        })

    return ResponseService.response("SUCCESS", {
        "vendor_id": vendor_id,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "calendar_data": booked_dates + manual_entries
    }, "Calendar data retrieved successfully.")

@api_view(["POST", "PATCH"])
@permission_classes([IsAuthenticated])
def vendor_availability_update_view(request: Request) -> Response:
    """
    Allows a vendor to set their availability for a specific date.
    """
    user = request.user
    vendor = _vendor_for_user(user)
    if not vendor:
        return ResponseService.response("FORBIDDEN", {"detail": "Only vendors can manage availability."}, "Forbidden", status.HTTP_403_FORBIDDEN)

    data = request.data
    errors = ValidatorService.validate(
        data,
        rules={
            "date": "required|date",
            "is_available": "required|boolean",
            "reason": "nullable|string|max:255",
        }
    )
    if errors:
        return ResponseService.response("VALIDATION_ERROR", errors, "Validation error", status.HTTP_400_BAD_REQUEST)

    target_date = datetime.strptime(data["date"], "%Y-%m-%d").date()
    is_available = data["is_available"]
    reason = data.get("reason", "")

    availability, created = VendorAvailability.objects.update_or_create(
        vendor=vendor,
        date=target_date,
        defaults={
            "is_available": is_available,
            "reason": reason
        }
    )

    return ResponseService.response("SUCCESS", {
        "date": availability.date.isoformat(),
        "is_available": availability.is_available,
        "reason": availability.reason,
        "created": created
    }, "Availability updated successfully.")
