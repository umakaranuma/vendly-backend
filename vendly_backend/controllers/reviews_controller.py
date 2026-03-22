from django.core.paginator import Paginator
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status

from mServices.ResponseService import ResponseService
from vendly_backend.models import VendorReview, Vendor, Booking

@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def vendor_reviews_view(request: Request, vendor_id: int) -> Response:
    try:
        vendor = Vendor.objects.get(id=vendor_id)
    except Vendor.DoesNotExist:
        return ResponseService.response("NOT_FOUND", {}, "Vendor not found.", status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        try:
            page = int(request.GET.get("page", 1))
            limit = int(request.GET.get("limit", 20))
            if page < 1 or limit < 1:
                raise ValueError("Invalid pagination")

            qs = (
                VendorReview.objects.filter(vendor_id=vendor.id)
                .select_related("reviewer")
                .order_by("-created_at")
            )
            paginator = Paginator(qs, limit)
            page_obj = paginator.get_page(page)
            rows = []
            for r in page_obj.object_list:
                u = r.reviewer
                rows.append(
                    {
                        "id": r.id,
                        "rating": float(r.rating) if r.rating is not None else None,
                        "comment": r.comment,
                        "created_at": r.created_at.isoformat() if r.created_at else None,
                        "first_name": u.first_name,
                        "last_name": u.last_name,
                        "avatar_url": u.avatar_url,
                    }
                )
            query = {
                "total_records": paginator.count,
                "per_page": limit,
                "current_page": page_obj.number,
                "last_page": paginator.num_pages or 1,
                "data": rows,
            }
            return ResponseService.response("SUCCESS", query, "Reviews retrieved successfully.")
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
        if not request.user.is_authenticated:
            return ResponseService.response("UNAUTHORIZED", {}, "Must be logged in to review.", status.HTTP_401_UNAUTHORIZED)
            
        data = request.data
        booking_id = data.get("booking_id")
        rating = data.get("rating")
        comment = data.get("comment", "")
        
        if not booking_id or not rating:
            return ResponseService.response("BAD_REQUEST", {"detail": "booking_id and rating are required."}, "Validation error", status.HTTP_400_BAD_REQUEST)
            
        try:
            booking = Booking.objects.get(id=booking_id)
        except Booking.DoesNotExist:
            return ResponseService.response("NOT_FOUND", {"detail": "Booking not found."}, "Validation error", status.HTTP_404_NOT_FOUND)
            
        if booking.vendor_id != vendor.id:
            return ResponseService.response("BAD_REQUEST", {"detail": "Booking vendor mismatch."}, "Validation error", status.HTTP_400_BAD_REQUEST)
            
        if booking.status != "completed":
            return ResponseService.response("BAD_REQUEST", {"detail": "Booking is not completed."}, "Validation error", status.HTTP_400_BAD_REQUEST)
            
        if hasattr(booking, 'review'):
            return ResponseService.response("CONFLICT", {"detail": "A review for this booking already exists."}, "Validation error", status.HTTP_409_CONFLICT)
            
        review = VendorReview.objects.create(
            booking=booking,
            reviewer=request.user,
            vendor=vendor,
            rating=rating,
            comment=comment
        )
        
        payload = {
            "id": review.id,
            "rating": review.rating,
            "comment": review.comment
        }
        return ResponseService.response("SUCCESS", payload, "Review submitted successfully.", status.HTTP_201_CREATED)
