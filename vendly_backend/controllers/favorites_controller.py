from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status

from mServices.ResponseService import ResponseService
from mServices.QueryBuilderService import QueryBuilderService
from vendly_backend.models import UserFavoriteVendor, Vendor


def _get_target_user_id(request: Request):
    """Resolve which user's favorites to return via optional `?id=` (defaults to the authenticated user)."""
    user_id = request.GET.get("id")
    if user_id is None:
        return request.user.id, None

    try:
        target_user_id = int(user_id)
    except (TypeError, ValueError):
        return 0, ResponseService.response(
            "VALIDATION_ERROR",
            {"id": ["Invalid id."]},
            "Validation Error",
            status.HTTP_400_BAD_REQUEST,
        )

    return target_user_id, None


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def favorites_list_view(request: Request) -> Response:
    try:
        target_user_id, error = _get_target_user_id(request)
        if error is not None:
            return error

        page = int(request.GET.get("page", 1))
        limit = int(request.GET.get("limit", 20))
        
        query = (
            QueryBuilderService("vendor_followers")
            .select("vendors.id", "vendors.name", "vendors.city", "vendors.category_id", "vendors.rating", "vendors.review_count", "vendors.price_from")
            .leftJoin("vendors", "vendors.id", "vendor_followers.vendor_id")
            .apply_conditions(f'{{"vendor_followers.user_id": {target_user_id}}}', ["vendor_followers.user_id"], "", [])
            .paginate(page, limit, ["vendor_followers.created_at"], "vendor_followers.created_at", "desc")
        )
        return ResponseService.response("SUCCESS", query, "Followed vendors retrieved successfully.")
    except Exception as e:
        return ResponseService.response("INTERNAL_SERVER_ERROR", {"error": str(e)}, "Server Error")

@api_view(["POST", "DELETE"])
@permission_classes([IsAuthenticated])
def favorite_vendor_view(request: Request, vendor_id: int) -> Response:
    try:
        vendor = Vendor.objects.get(id=vendor_id)
    except Vendor.DoesNotExist:
        return ResponseService.response("NOT_FOUND", {}, "Vendor not found.", status.HTTP_404_NOT_FOUND)

    if request.method == "POST":
        favorite, created = UserFavoriteVendor.objects.get_or_create(user=request.user, vendor=vendor)
        return ResponseService.response("SUCCESS", {}, "Vendor added to favorites.", status.HTTP_201_CREATED)
        
    elif request.method == "DELETE":
        UserFavoriteVendor.objects.filter(user=request.user, vendor=vendor).delete()
        return ResponseService.response("SUCCESS", {}, "Vendor removed from favorites.", status.HTTP_204_NO_CONTENT)
