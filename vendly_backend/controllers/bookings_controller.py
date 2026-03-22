from datetime import datetime

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status

from mServices.ResponseService import ResponseService
from mServices.QueryBuilderService import QueryBuilderService
from mServices.ValidatorService import ValidatorService
from vendly_backend.activity_log import log_activity
from vendly_backend.booking_statuses import ALLOWED_BOOKING_STATUS_NAMES, get_booking_status_ref
from vendly_backend.models import Booking, Vendor, VendorPackage

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def bookings_list_view(request: Request) -> Response:
    user = request.user
    
    if request.method == "GET":
        try:
            page = int(request.GET.get("page", 1))
            limit = int(request.GET.get("limit", 20))
            booking_status = request.GET.get("status", "")
            
            query = QueryBuilderService("bookings")

            if booking_status:
                if booking_status not in ALLOWED_BOOKING_STATUS_NAMES:
                    return ResponseService.response(
                        "BAD_REQUEST",
                        {"status": ["Invalid status filter."]},
                        "Validation error",
                        status.HTTP_400_BAD_REQUEST,
                    )
                sid = get_booking_status_ref(booking_status).id
                query = query.apply_conditions(f'{{"status_id": {sid}}}', ["status_id"], "", [])

            query = (
                query.select(
                    "bookings.id",
                    "bookings.event_type",
                    "bookings.booking_date",
                    "bookings.location",
                    "bookings.amount",
                    "core_statuses.name as status",
                    "core_users.first_name",
                    "core_users.last_name",
                    "vendors.name as vendor_name",
                )
                .leftJoin("core_users", "core_users.id", "bookings.customer_id")
                .leftJoin("vendors", "vendors.id", "bookings.vendor_id")
                .leftJoin("core_statuses", "core_statuses.id", "bookings.status_id")
                .paginate(page, limit, ["bookings.created_at"], "bookings.created_at", "desc")
            )
            return ResponseService.response("SUCCESS", query, "Bookings retrieved successfully.")
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
            "status_id": booking.status_id,
            "event_type": booking.event_type,
            "booking_date": booking.booking_date,
            "vendor_id": booking.vendor.id,
            "package_id": booking.vendor_package_id,
            "amount": str(booking.amount) if booking.amount is not None else None,
        }
        return ResponseService.response("SUCCESS", payload, "Booking created successfully.", status.HTTP_201_CREATED)

@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def booking_detail_view(request: Request, booking_id: int) -> Response:
    try:
        booking = Booking.objects.select_related("status").get(id=booking_id)
    except Booking.DoesNotExist:
        return ResponseService.response("NOT_FOUND", {}, "Booking not found.", status.HTTP_404_NOT_FOUND)

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
            "status_id": booking.status_id,
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
