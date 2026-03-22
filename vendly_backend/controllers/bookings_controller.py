from datetime import datetime

from django.core.paginator import Paginator
from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status

from mServices.ResponseService import ResponseService
from mServices.ValidatorService import ValidatorService
from vendly_backend.activity_log import log_activity
from vendly_backend.booking_statuses import (
    ALLOWED_BOOKING_STATUS_NAMES,
    ALLOWED_BOOKING_STATUS_TYPES,
    get_booking_status_ref,
)
from vendly_backend.models import Booking, Vendor, VendorPackage


def _vendor_for_user(user):
    try:
        return user.vendor
    except Vendor.DoesNotExist:
        return None


def _user_can_access_booking(user, booking: Booking) -> bool:
    if booking.customer_id == user.id or booking.requested_by_id == user.id:
        return True
    return booking.vendor.user_id == user.id


def _vendor_booking_side(user, vendor_profile: Vendor | None, booking: Booking):
    """For vendor accounts: incoming vs outgoing request; null for customer-only list."""
    if vendor_profile is None:
        return None
    if booking.requested_by_id == user.id:
        return "requested"
    if booking.vendor_id == vendor_profile.id:
        return "received"
    return None


def _serialize_booking_list_row(booking: Booking, user, vendor_profile):
    bd = booking.booking_date
    bd_out = bd.isoformat() if hasattr(bd, "isoformat") else bd
    return {
        "id": booking.id,
        "event_type": booking.event_type,
        "booking_date": bd_out,
        "location": booking.location,
        "amount": str(booking.amount) if booking.amount is not None else None,
        "status": booking.status.name if booking.status else None,
        "status_type": booking.status.status_type if booking.status else None,
        "first_name": booking.customer.first_name,
        "last_name": booking.customer.last_name,
        "vendor_name": booking.vendor.name,
        "requested_by_id": booking.requested_by_id,
        "vendor_booking_side": _vendor_booking_side(user, vendor_profile, booking),
    }


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def bookings_list_view(request: Request) -> Response:
    user = request.user
    
    if request.method == "GET":
        try:
            page = int(request.GET.get("page", 1))
            limit = int(request.GET.get("limit", 20))
            raw_status_type = (request.GET.get("status_type") or "").strip()
            booking_status = (request.GET.get("status") or "").strip()
            if page < 1 or limit < 1:
                raise ValueError("Invalid pagination")

            vendor_profile = _vendor_for_user(user)
            if vendor_profile is not None:
                qs = Booking.objects.filter(Q(vendor_id=vendor_profile.id) | Q(requested_by=user))
            else:
                qs = Booking.objects.filter(customer=user)

            if raw_status_type:
                if raw_status_type not in ALLOWED_BOOKING_STATUS_TYPES:
                    return ResponseService.response(
                        "BAD_REQUEST",
                        {"status_type": ["Invalid status_type filter."]},
                        "Validation error",
                        status.HTTP_400_BAD_REQUEST,
                    )
                qs = qs.filter(status__status_type=raw_status_type)
            elif booking_status:
                if booking_status not in ALLOWED_BOOKING_STATUS_NAMES:
                    return ResponseService.response(
                        "BAD_REQUEST",
                        {"status": ["Invalid status filter."]},
                        "Validation error",
                        status.HTTP_400_BAD_REQUEST,
                    )
                sid = get_booking_status_ref(booking_status).id
                qs = qs.filter(status_id=sid)

            qs = qs.select_related("status", "vendor", "customer", "requested_by").order_by("-created_at")
            paginator = Paginator(qs, limit)
            page_obj = paginator.get_page(page)
            data = [
                _serialize_booking_list_row(b, user, vendor_profile) for b in page_obj.object_list
            ]
            result = {
                "total_records": paginator.count,
                "per_page": limit,
                "current_page": page_obj.number,
                "last_page": paginator.num_pages or 1,
                "data": data,
            }
            return ResponseService.response("SUCCESS", result, "Bookings retrieved successfully.")
        except ValueError:
            return ResponseService.response(
                "VALIDATION_ERROR",
                {"pagination": ["Invalid parameters"]},
                "Invalid Request",
                status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return ResponseService.response("INTERNAL_SERVER_ERROR", {"error": str(e)}, "Server Error")

    elif request.method == "POST":
        data = request.data
        errors = ValidatorService.validate(
            data,
            rules={
                "vendor_id": "required|integer|exists:vendors,id",
                "event_type": "required|string|max:255",
                "booking_date": "required|date",
                "location": "nullable|string|max:255",
                "amount": "nullable|numeric",
                "deposit": "nullable|numeric",
                "package_id": "nullable|integer|exists:vendor_packages,id",
            },
            custom_messages={
                "vendor_id.required": "vendor_id is required.",
                "vendor_id.integer": "vendor_id must be an integer.",
                "event_type.required": "event_type is required.",
                "event_type.max": "event_type may not be greater than 255 characters.",
                "booking_date.required": "booking_date is required.",
                "booking_date.date": "booking_date must be a valid date (YYYY-MM-DD).",
                "package_id.integer": "package_id must be an integer.",
            },
        )
        if errors:
            return ResponseService.response(
                "VALIDATION_ERROR",
                errors,
                "Validation Error",
                status.HTTP_400_BAD_REQUEST,
            )

        vendor = Vendor.objects.get(id=data.get("vendor_id"))
        booking_date = datetime.strptime(data.get("booking_date"), "%Y-%m-%d")
        event_type = data.get("event_type")
        location = data.get("location")
        amount = data.get("amount")
        deposit = data.get("deposit")
        if amount in (None, ""):
            amount = None
        if deposit in (None, ""):
            deposit = None

        raw_package_id = data.get("package_id")
        vendor_package = None
        if raw_package_id not in (None, ""):
            try:
                vendor_package = VendorPackage.objects.get(id=int(raw_package_id), vendor_id=vendor.id)
            except VendorPackage.DoesNotExist:
                return ResponseService.response(
                    "VALIDATION_ERROR",
                    {"package_id": ["The selected package does not belong to this vendor."]},
                    "Validation Error",
                    status.HTTP_400_BAD_REQUEST,
                )
            if not vendor_package.is_active:
                return ResponseService.response(
                    "VALIDATION_ERROR",
                    {"package_id": ["This package is not available."]},
                    "Validation Error",
                    status.HTTP_400_BAD_REQUEST,
                )
            if amount is None:
                amount = vendor_package.price

        booking = Booking.objects.create(
            customer=user,
            requested_by=user,
            vendor=vendor,
            vendor_package=vendor_package,
            event_type=event_type,
            booking_date=booking_date,
            location=location,
            amount=amount,
            deposit=deposit,
            status=get_booking_status_ref("pending"),
        )
        log_activity(
            actor=user,
            category="booking",
            event="created",
            resource_type="booking",
            resource_id=booking.id,
            payload={
                "vendor_id": vendor.id,
                "booking_status": booking.status.name if booking.status else None,
                "package_id": booking.vendor_package_id,
                "amount": str(booking.amount) if booking.amount is not None else None,
                "deposit": str(booking.deposit) if booking.deposit is not None else None,
            },
        )

        if booking.amount is not None or booking.deposit is not None:
            log_activity(
                actor=user,
                category="payment",
                event="booking_amount_recorded",
                resource_type="booking",
                resource_id=booking.id,
                payload={
                    "amount": str(booking.amount) if booking.amount is not None else None,
                    "deposit": str(booking.deposit) if booking.deposit is not None else None,
                },
            )

        payload = {
            "id": booking.id,
            "status": booking.status.name if booking.status else None,
            "status_type": booking.status.status_type if booking.status else None,
            "status_id": booking.status_id,
            "event_type": booking.event_type,
            "booking_date": booking.booking_date,
            "vendor_id": booking.vendor.id,
            "package_id": booking.vendor_package_id,
            "amount": str(booking.amount) if booking.amount is not None else None,
            "requested_by_id": booking.requested_by_id,
        }
        return ResponseService.response("SUCCESS", payload, "Booking created successfully.", status.HTTP_201_CREATED)

@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def booking_detail_view(request: Request, booking_id: int) -> Response:
    try:
        booking = Booking.objects.select_related("status", "vendor", "customer", "requested_by").get(id=booking_id)
    except Booking.DoesNotExist:
        return ResponseService.response("NOT_FOUND", {}, "Booking not found.", status.HTTP_404_NOT_FOUND)

    if not _user_can_access_booking(request.user, booking):
        return ResponseService.response(
            "FORBIDDEN",
            {"detail": "You do not have access to this booking."},
            "Forbidden",
            status.HTTP_403_FORBIDDEN,
        )

    vendor_profile = _vendor_for_user(request.user)

    if request.method == "GET":
        payload = {
            "id": booking.id,
            "customer_id": booking.customer_id,
            "vendor_id": booking.vendor_id,
            "package_id": booking.vendor_package_id,
            "event_type": booking.event_type,
            "booking_date": booking.booking_date,
            "location": booking.location,
            "amount": str(booking.amount) if booking.amount else None,
            "deposit": str(booking.deposit) if booking.deposit else None,
            "status": booking.status.name if booking.status else None,
            "status_type": booking.status.status_type if booking.status else None,
            "status_id": booking.status_id,
            "requested_by_id": booking.requested_by_id,
            "vendor_booking_side": _vendor_booking_side(request.user, vendor_profile, booking),
            "created_at": booking.created_at,
            "updated_at": booking.updated_at,
        }
        return ResponseService.response("SUCCESS", payload, "Booking fetched successfully.")

    elif request.method == "PATCH":
        new_status = request.data.get("status")
        if new_status not in ALLOWED_BOOKING_STATUS_NAMES:
            return ResponseService.response("BAD_REQUEST", {"detail": "Invalid status."}, "Validation error", status.HTTP_400_BAD_REQUEST)

        booking.status = get_booking_status_ref(new_status)
        booking.save(update_fields=["status", "updated_at"])
        status_name = booking.status.name if booking.status else None
        log_activity(
            actor=request.user,
            category="booking",
            event="status_updated",
            resource_type="booking",
            resource_id=booking.id,
            payload={"status": status_name},
        )

        if status_name == "completed":
            log_activity(
                actor=request.user,
                category="payment",
                event="booking_completed",
                resource_type="booking",
                resource_id=booking.id,
                payload={"amount": str(booking.amount) if booking.amount is not None else None},
            )

        return ResponseService.response(
            "SUCCESS",
            {"id": booking.id, "status": status_name, "status_id": booking.status_id},
            "Booking updated successfully.",
        )
