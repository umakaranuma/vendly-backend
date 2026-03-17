from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum

from mServices.ResponseService import ResponseService
from vendly_backend.models import Booking, VendorView, PostLike, CommentLike
from vendly_backend.permissions import IsVendor

@api_view(["GET"])
@permission_classes([IsAuthenticated, IsVendor])
def vendor_analytics_view(request: Request) -> Response:
    vendor = request.user.vendor
    date_from = request.GET.get("from")
    date_to = request.GET.get("to")
    
    try:
        # Note: in a real implementation we would filter by date_from and date_to
        views_count = VendorView.objects.filter(vendor=vendor).count()
        
        # Approximate likes from posts + comments
        post_likes = PostLike.objects.filter(post__vendor=vendor).count()
        # comment_likes = CommentLike.objects.filter(comment__post__vendor=vendor).count()
        likes_count = post_likes # + comment_likes
        
        bookings_count = Booking.objects.filter(vendor=vendor).count()
        
        revenue = Booking.objects.filter(
            vendor=vendor, 
            status="completed"
        ).aggregate(Sum('amount'))['amount__sum'] or 0.00
        
        payload = {
            "views": views_count,
            "likes": likes_count,
            "bookings_count": bookings_count,
            "revenue": str(revenue),
            "chart_data": {
                "labels": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
                "data": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0] # Mocked chart data
            }
        }
        return ResponseService.response("SUCCESS", payload, "Analytics retrieved successfully.")
    except Exception as e:
        return ResponseService.response("INTERNAL_SERVER_ERROR", {"error": str(e)}, "Server Error")
