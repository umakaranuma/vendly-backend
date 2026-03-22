from __future__ import annotations

from django.db.models import Q
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status

from mServices.ResponseService import ResponseService
from vendly_backend.activity_log import log_activity
from vendly_backend.models import Booking
def _paginate(queryset, page: int, limit: int):
    total = queryset.count()
    page = max(page, 1)
    limit = max(limit, 1)
    offset = (page - 1) * limit
    items = list(queryset[offset : offset + limit])
    next_page = page + 1 if offset + limit < total else None
    return items, total, next_page


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_bookings_list_view(request: Request) -> Response:
    page = int(request.GET.get("page", 1))
    limit = int(request.GET.get("limit", 20))
    booking_status = request.GET.get("status", "").strip()

    allowed_statuses = {"pending", "confirmed", "completed", "cancelled"}
    if booking_status and booking_status not in allowed_statuses:
        return ResponseService.response(
            "BAD_REQUEST",
            {"detail": "Invalid status."},
            "Validation error",
            status.HTTP_400_BAD_REQUEST,
        )

    qs = Booking.objects.select_related("customer", "vendor").order_by("-created_at")
    if booking_status:
        qs = qs.filter(status=booking_status)

    items, total, next_page = _paginate(qs, page, limit)

    payload = []
    for b in items:
        customer_name = f"{b.customer.first_name} {b.customer.last_name}".strip()
        payload.append(
            {
                "id": b.id,
                "customer_id": b.customer_id,
                "customer_name": customer_name,
                "vendor_id": b.vendor_id,
                "vendor_name": b.vendor.name if b.vendor else None,
                "event_type": b.event_type,
                "booking_date": b.booking_date,
                "location": b.location,
                "amount": str(b.amount) if b.amount is not None else None,
                "deposit": str(b.deposit) if b.deposit is not None else None,
                "status": b.status,
                "created_at": b.created_at,
                "updated_at": b.updated_at,
            }
        )

    return ResponseService.response(
        "SUCCESS",
        {"items": payload, "total": total, "next_page": next_page},
        "Admin bookings retrieved successfully.",
        status.HTTP_200_OK,
    )


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def admin_booking_update_view(request: Request, booking_id: int) -> Response:
    new_status = request.data.get("status")
    allowed_statuses = {"pending", "confirmed", "completed", "cancelled"}
    if new_status not in allowed_statuses:
        return ResponseService.response(
            "BAD_REQUEST",
            {"detail": "Invalid status."},
            "Validation error",
            status.HTTP_400_BAD_REQUEST,
        )

    try:
        booking = Booking.objects.get(id=booking_id)
    except Booking.DoesNotExist:
        return ResponseService.response(
            "NOT_FOUND",
            {},
            "Booking not found.",
            status.HTTP_404_NOT_FOUND,
        )

    booking.status = new_status
    booking.save(update_fields=["status", "updated_at"])
    log_activity(
        actor=request.user,
        category="booking",
        event="admin_status_updated",
        resource_type="booking",
        resource_id=booking.id,
        payload={"status": booking.status},
    )

    return ResponseService.response(
        "SUCCESS",
        {"id": booking.id, "status": booking.status},
        "Booking updated successfully.",
        status.HTTP_200_OK,
    )

