from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone

from mServices.ResponseService import ResponseService
from mServices.QueryBuilderService import QueryBuilderService
from vendly_backend.models import VendorSubscription

from vendly_backend.permissions import IsVendor

@api_view(["GET"])
@permission_classes([IsAuthenticated, IsVendor])
def vendor_subscription_view(request: Request) -> Response:
    vendor = request.user.vendor
    
    # Get active subscription
    active_sub = VendorSubscription.objects.filter(
        vendor=vendor,
        is_active=True,
        starts_at__lte=timezone.now()
    ).select_related('plan').first()
    
    if not active_sub:
        return ResponseService.response("SUCCESS", {"active": False}, "No active subscription found.")
        
    payload = {
        "active": True,
        "subscription_id": active_sub.id,
        "starts_at": active_sub.starts_at,
        "ends_at": active_sub.ends_at,
        "plan": {
            "id": active_sub.plan.id,
            "name": active_sub.plan.name,
            "max_packages": active_sub.plan.max_packages
        }
    }
    return ResponseService.response("SUCCESS", payload, "Subscription retrieved successfully.")

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def subscription_plans_view(request: Request) -> Response:
    try:
        page = int(request.GET.get("page", 1))
        limit = int(request.GET.get("limit", 20))
        
        query = (
            QueryBuilderService("subscription_plans")
            .select("subscription_plans.id", "subscription_plans.name", "subscription_plans.max_packages", "subscription_plans.price", "subscription_plans.description")
            .paginate(page, limit, ["subscription_plans.price"], "subscription_plans.price", "asc")
        )
        return ResponseService.response("SUCCESS", query, "Subscription plans retrieved successfully.")
    except Exception as e:
        return ResponseService.response("INTERNAL_SERVER_ERROR", {"error": str(e)}, "Server Error")
