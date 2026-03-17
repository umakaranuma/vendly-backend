from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status

from mServices.ResponseService import ResponseService
from mServices.QueryBuilderService import QueryBuilderService
from vendly_backend.models import Booking, Vendor

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
            
            if hasattr(user, 'vendor') and user.vendor:
                # If the user is a vendor, get vendor bookings
                query = query.apply_conditions(f'{{"vendor_id": {user.vendor.id}}}', ["vendor_id"], "", [])
            else:
                # Customers get their own bookings
                query = query.apply_conditions(f'{{"customer_id": {user.id}}}', ["customer_id"], "", [])

            if booking_status:
                query = query.apply_conditions(f'{{"status": "{booking_status}"}}', ["status"], "", [])

            query = (
                query.select("bookings.id", "bookings.event_type", "bookings.booking_date", "bookings.location", "bookings.amount", "bookings.status", "core_users.first_name", "core_users.last_name", "vendors.name as vendor_name")
                .leftJoin("core_users", "core_users.id", "bookings.customer_id")
                .leftJoin("vendors", "vendors.id", "bookings.vendor_id")
                .paginate(page, limit, ["bookings.created_at"], "bookings.created_at", "desc")
            )
            return ResponseService.response("SUCCESS", query, "Bookings retrieved successfully.")
        except Exception as e:
            return ResponseService.response("INTERNAL_SERVER_ERROR", {"error": str(e)}, "Server Error")

    elif request.method == "POST":
        data = request.data
        vendor_id = data.get("vendor_id")
        event_type = data.get("event_type")
        booking_date = data.get("booking_date")
        location = data.get("location")
        amount = data.get("amount")
        deposit = data.get("deposit")
        
        if not vendor_id or not event_type or not booking_date:
            return ResponseService.response("BAD_REQUEST", {"detail": "vendor_id, event_type, and booking_date are required."}, "Validation error", status.HTTP_400_BAD_REQUEST)

        try:
            vendor = Vendor.objects.get(id=vendor_id)
        except Vendor.DoesNotExist:
            return ResponseService.response("NOT_FOUND", {}, "Vendor not found.", status.HTTP_404_NOT_FOUND)

        booking = Booking.objects.create(
            customer=user,
            vendor=vendor,
            event_type=event_type,
            booking_date=booking_date,
            location=location,
            amount=amount,
            deposit=deposit,
            status="pending"
        )
        payload = {
            "id": booking.id,
            "status": booking.status,
            "event_type": booking.event_type,
            "booking_date": booking.booking_date,
            "vendor_id": booking.vendor.id
        }
        return ResponseService.response("SUCCESS", payload, "Booking created successfully.", status.HTTP_201_CREATED)

@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def booking_detail_view(request: Request, booking_id: int) -> Response:
    try:
        booking = Booking.objects.get(id=booking_id)
    except Booking.DoesNotExist:
        return ResponseService.response("NOT_FOUND", {}, "Booking not found.", status.HTTP_404_NOT_FOUND)

    user = request.user
    is_customer = booking.customer_id == user.id
    is_vendor = hasattr(user, 'vendor') and user.vendor and booking.vendor_id == user.vendor.id
    
    if not (is_customer or is_vendor):
        return ResponseService.response("FORBIDDEN", {}, "Access denied.", status.HTTP_403_FORBIDDEN)

    if request.method == "GET":
        payload = {
            "id": booking.id,
            "customer_id": booking.customer_id,
            "vendor_id": booking.vendor_id,
            "event_type": booking.event_type,
            "booking_date": booking.booking_date,
            "location": booking.location,
            "amount": str(booking.amount) if booking.amount else None,
            "deposit": str(booking.deposit) if booking.deposit else None,
            "status": booking.status,
            "created_at": booking.created_at,
            "updated_at": booking.updated_at
        }
        return ResponseService.response("SUCCESS", payload, "Booking fetched successfully.")

    elif request.method == "PATCH":
        new_status = request.data.get("status")
        if new_status not in ["pending", "confirmed", "completed", "cancelled"]:
            return ResponseService.response("BAD_REQUEST", {"detail": "Invalid status."}, "Validation error", status.HTTP_400_BAD_REQUEST)

        booking.status = new_status
        booking.save(update_fields=["status", "updated_at"])
        
        return ResponseService.response("SUCCESS", {"id": booking.id, "status": booking.status}, "Booking updated successfully.")
