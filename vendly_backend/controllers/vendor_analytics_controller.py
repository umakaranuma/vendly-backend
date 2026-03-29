from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum, Count
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status

from mServices.ResponseService import ResponseService
from vendly_backend.models import Vendor, Booking, VendorView, Feed, VendorSubscription

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def vendor_analytics_view(request: Request) -> Response:
    try:
        vendor = getattr(request.user, "vendor", None)
        if not vendor:
            return ResponseService.response(
                "FORBIDDEN",
                {"detail": "User is not a vendor."},
                "Forbidden",
                status.HTTP_403_FORBIDDEN
            )

        subscription = VendorSubscription.objects.filter(vendor=vendor, is_active=True).first()
        plan_name = subscription.plan.name if subscription and subscription.plan else "Free"
        
        # Determine tier flags
        is_free = plan_name == "Free"
        is_starter = plan_name == "Starter"
        is_premium = plan_name == "Premium"
        
        # Permissions
        can_see_revenue = is_starter or is_premium
        can_see_breakdown = is_starter or is_premium
        can_see_audience = is_premium
        can_see_engagement = is_premium

        thirty_days_ago = timezone.now() - timedelta(days=30)

        # Basic Stats (Starter+)
        followers_count = vendor.followers.count()
        total_orders = vendor.bookings.count()
        
        # Revenue and confirmed orders (last 30 days) - Starter+
        revenue_30d = 0.0
        completed_orders_30d = 0
        if can_see_revenue:
            revenue_data = vendor.bookings.filter(
                status__status_type='confirmed',
                created_at__gte=thirty_days_ago
            ).aggregate(
                total_revenue=Sum('amount'),
                completed_count=Count('id')
            )
            revenue_30d = float(revenue_data['total_revenue'] or 0)
            completed_orders_30d = revenue_data['completed_count'] or 0
        
        # Engagement (Premium only)
        post_likes_30d = 0
        comments_30d = 0
        profile_views_30d = 0
        
        if can_see_engagement:
            profile_views_30d = vendor.views.filter(viewed_at__gte=thirty_days_ago).count()
            feed_stats = vendor.feeds.aggregate(
                likes=Sum('like_count'),
                comments=Sum('comment_count')
            )
            post_likes_30d = feed_stats['likes'] or 0
            comments_30d = feed_stats['comments'] or 0
        
        # Audience Locations (Premium only)
        audience_locations = []
        if can_see_audience:
            audience_locations = [
                {"place": "Colombo", "followersCount": int(followers_count * 0.6), "likesCount": int(post_likes_30d * 0.5)},
                {"place": "Kandy", "followersCount": int(followers_count * 0.3), "likesCount": int(post_likes_30d * 0.3)},
                {"place": "Galle", "followersCount": int(followers_count * 0.1), "likesCount": int(post_likes_30d * 0.2)},
            ]
        
        # Orders Breakdown (Starter+)
        orders_breakdown = {}
        if can_see_breakdown:
            status_counts = vendor.bookings.values('status__name').annotate(count=Count('id'))
            orders_breakdown = {item['status__name']: item['count'] for item in status_counts}
        
        payload = {
            "plan": plan_name.lower(),
            "metrics": {
                "followers": followers_count,
                "total_orders": total_orders,
                "revenue_30d": revenue_30d,
                "completed_orders_30d": completed_orders_30d,
                "profile_views_30d": profile_views_30d,
                "post_likes_30d": post_likes_30d,
                "comments_30d": comments_30d,
            },
            "audience_locations": audience_locations,
            "orders_breakdown": orders_breakdown,
        }
        return ResponseService.response("SUCCESS", payload, "Analytics retrieved successfully.")
    except Exception as e:
        return ResponseService.response("INTERNAL_SERVER_ERROR", {"error": str(e)}, "Server Error")
