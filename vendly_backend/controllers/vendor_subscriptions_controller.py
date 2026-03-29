from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from datetime import timedelta

from mServices.ResponseService import ResponseService
from vendly_backend.models import VendorSubscription, SubscriptionPlan


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def vendor_subscription_view(request: Request) -> Response:
    try:
        vendor = getattr(request.user, "vendor", None)
        if not vendor:
            return ResponseService.response(
                "FORBIDDEN", {"detail": "User is not a vendor."}, "Forbidden", status.HTTP_403_FORBIDDEN
            )

        # Get active subscription
        active_sub = (
            VendorSubscription.objects.filter(
                vendor=vendor, is_active=True, starts_at__lte=timezone.now()
            )
            .select_related("plan")
            .first()
        )

        if not active_sub:
            return ResponseService.response(
                "SUCCESS", {"active": False}, "No active subscription found."
            )

        payload = {
            "active": True,
            "subscription_id": active_sub.id,
            "starts_at": active_sub.starts_at,
            "ends_at": active_sub.ends_at,
            "plan": {
                "id": active_sub.plan.id,
                "name": active_sub.plan.name,
                "max_packages": active_sub.plan.max_packages,
            },
        }
        return ResponseService.response(
            "SUCCESS", payload, "Subscription retrieved successfully."
        )
    except Exception as e:
        return ResponseService.response(
            "INTERNAL_SERVER_ERROR", {"error": str(e)}, "Server Error"
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def subscription_plans_view(request: Request) -> Response:
    try:
        plans = SubscriptionPlan.objects.all().order_by("price")
        data = [
            {
                "id": p.id,
                "name": p.name,
                "price": float(p.price) if p.price is not None else 0,
                "max_packages": p.max_packages,
                "description": p.description,
            }
            for p in plans
        ]
        return ResponseService.response(
            "SUCCESS", data, "Subscription plans retrieved successfully."
        )
    except Exception as e:
        return ResponseService.response(
            "INTERNAL_SERVER_ERROR", {"error": str(e)}, "Server Error"
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def activate_subscription_view(request: Request) -> Response:
    try:
        vendor = getattr(request.user, "vendor", None)
        if not vendor:
            return ResponseService.response(
                "FORBIDDEN", {"detail": "User is not a vendor."}, "Forbidden", status.HTTP_403_FORBIDDEN
            )

        plan_id = request.data.get("plan_id")
        if not plan_id:
            return ResponseService.response(
                "BAD_REQUEST", {"plan_id": ["Required."]}, "Validation error", status.HTTP_400_BAD_REQUEST
            )

        try:
            plan = SubscriptionPlan.objects.get(id=plan_id)
        except SubscriptionPlan.DoesNotExist:
            return ResponseService.response(
                "NOT_FOUND", {"plan_id": ["Invalid plan ID."]}, "Not found", status.HTTP_404_NOT_FOUND
            )

        # Deactivate current subscriptions
        VendorSubscription.objects.filter(vendor=vendor, is_active=True).update(
            is_active=False, ends_at=timezone.now()
        )

        # Create new subscription (30 days validity)
        new_sub = VendorSubscription.objects.create(
            vendor=vendor,
            plan=plan,
            starts_at=timezone.now(),
            ends_at=timezone.now() + timedelta(days=30),
            is_active=True,
        )

        return ResponseService.response(
            "SUCCESS", {"subscription_id": new_sub.id, "plan_name": plan.name}, "Plan activated successfully."
        )
    except Exception as e:
        return ResponseService.response(
            "INTERNAL_SERVER_ERROR", {"error": str(e)}, "Server Error"
        )
