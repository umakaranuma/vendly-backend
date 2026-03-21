from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status

from mServices.ResponseService import ResponseService
from mServices.QueryBuilderService import QueryBuilderService
from vendly_backend.models import UserFavoriteVendor, Vendor
from vendly_backend.permissions import is_admin_user


def _get_target_user_id(request: Request):
    """
    Resolve which user's favorites to return.
    - Non-admin: can only access their own data.
    - Admin: can access any user via `?id=<user_id>`.
    """
    is_admin = is_admin_user(request.user)

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

    if not is_admin and target_user_id != request.user.id:
        return 0, ResponseService.response(
            "FORBIDDEN",
            {},
            "You are not allowed to access this user's favorites.",
            status.HTTP_403_FORBIDDEN,
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
            QueryBuilderService("user_favorite_vendors")
            .select("vendors.id", "vendors.name", "vendors.city", "vendors.category_id", "vendors.rating", "vendors.review_count", "vendors.price_from")
            .leftJoin("vendors", "vendors.id", "user_favorite_vendors.vendor_id")
            .apply_conditions(f'{{"user_id": {target_user_id}}}', ["user_id"], "", [])
            .paginate(page, limit, ["user_favorite_vendors.created_at"], "user_favorite_vendors.created_at", "desc")
        )
        return ResponseService.response("SUCCESS", query, "Favorites retrieved successfully.")
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
