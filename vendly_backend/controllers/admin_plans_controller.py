from __future__ import annotations

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from mServices.QueryBuilderService import QueryBuilderService
from mServices.ResponseService import ResponseService
from mServices.ValidatorService import ValidatorService
from vendly_backend.models import SubscriptionPlan

def _plan_payload(plan: SubscriptionPlan) -> dict:
    return {
        "id": plan.id,
        "name": plan.name,
        "max_packages": plan.max_packages,
        "price": str(plan.price) if plan.price is not None else None,
        "description": plan.description,
        "created_at": plan.created_at,
        "updated_at": plan.updated_at,
    }


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def admin_plans_view(request: Request) -> Response:
    if request.method == "GET":
        try:
            page = int(request.GET.get("page", 1))
            limit = int(request.GET.get("limit", 50))
            query = (
                QueryBuilderService("subscription_plans")
                .select(
                    "subscription_plans.id",
                    "subscription_plans.name",
                    "subscription_plans.max_packages",
                    "subscription_plans.price",
                    "subscription_plans.description",
                    "subscription_plans.created_at",
                    "subscription_plans.updated_at",
                )
                .paginate(page, limit, ["subscription_plans.id", "subscription_plans.name"], "subscription_plans.id", "asc")
            )
            return ResponseService.response("SUCCESS", query, "Subscription plans retrieved successfully.")
        except Exception as e:
            return ResponseService.response("INTERNAL_SERVER_ERROR", {"error": str(e)}, "Server Error")

    data = request.data
    errors = ValidatorService.validate(
        data,
        rules={
            "name": "required|string|max:255",
            "max_packages": "required|integer",
            "price": "nullable|numeric",
            "description": "nullable|string",
        }
    )
    if errors:
        return ResponseService.response("VALIDATION_ERROR", errors, "Validation Error", status.HTTP_400_BAD_REQUEST)

    try:
        plan = SubscriptionPlan.objects.create(
            name=data["name"],
            max_packages=data["max_packages"],
            price=data.get("price"),
            description=data.get("description"),
        )
        return ResponseService.response(
            "SUCCESS",
            _plan_payload(plan),
            "Subscription plan created successfully.",
            status.HTTP_201_CREATED,
        )
    except Exception as e:
        return ResponseService.response("INTERNAL_SERVER_ERROR", {"error": str(e)}, "Server Error")


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def admin_plan_detail_view(request: Request, plan_id: int) -> Response:
    try:
        plan = SubscriptionPlan.objects.get(id=plan_id)
    except SubscriptionPlan.DoesNotExist:
        return ResponseService.response("NOT_FOUND", {}, "Subscription plan not found.", status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        return ResponseService.response("SUCCESS", _plan_payload(plan), "Subscription plan retrieved successfully.")

    if request.method == "PATCH":
        data = request.data
        errors = ValidatorService.validate(
            data,
            rules={
                "name": "nullable|string|max:255",
                "max_packages": "nullable|integer",
                "price": "nullable|numeric",
                "description": "nullable|string",
            }
        )
        if errors:
            return ResponseService.response("VALIDATION_ERROR", errors, "Validation Error", status.HTTP_400_BAD_REQUEST)

        if "name" in data:
            plan.name = data["name"]
        if "max_packages" in data:
            plan.max_packages = data["max_packages"]
        if "price" in data:
            plan.price = data["price"]
        if "description" in data:
            plan.description = data["description"]

        try:
            plan.save()
            return ResponseService.response("SUCCESS", _plan_payload(plan), "Subscription plan updated successfully.")
        except Exception as e:
            return ResponseService.response("INTERNAL_SERVER_ERROR", {"error": str(e)}, "Server Error")

    if request.method == "DELETE":
        try:
            plan.delete()
            return ResponseService.response("SUCCESS", {}, "Subscription plan deleted successfully.", status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return ResponseService.response("INTERNAL_SERVER_ERROR", {"error": str(e)}, "Server Error")
