from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status

from mServices.ResponseService import ResponseService
from mServices.QueryBuilderService import QueryBuilderService
from vendly_backend.models import CoreUser, Notification, UserNotificationSetting


def _resolve_target_user(request: Request):
    """Optional `?id=` selects which user; defaults to the authenticated user."""
    user_id = request.GET.get("id")
    if user_id is None:
        return request.user, None

    try:
        target_user_id = int(user_id)
    except (TypeError, ValueError):
        return None, ResponseService.response(
            "VALIDATION_ERROR",
            {"id": ["Invalid id."]},
            "Validation Error",
            status.HTTP_400_BAD_REQUEST,
        )

    try:
        return CoreUser.objects.get(pk=target_user_id), None
    except CoreUser.DoesNotExist:
        return None, ResponseService.response(
            "NOT_FOUND",
            {},
            "User not found.",
            status.HTTP_404_NOT_FOUND,
        )

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def notifications_view(request: Request) -> Response:
    user, error = _resolve_target_user(request)
    if error is not None:
        return error
    
    try:
        page = int(request.GET.get("page", 1))
        limit = int(request.GET.get("limit", 20))
        
        query = (
            QueryBuilderService("notifications")
            .select("notifications.id", "notifications.type", "notifications.title", "notifications.body", "notifications.data", "notifications.read_at", "notifications.created_at")
            .apply_conditions(f'{{"user_id": {user.id}}}', ["user_id"], "", [])
            .paginate(page, limit, ["notifications.created_at"], "notifications.created_at", "desc")
        )
        
        unread_count = Notification.objects.filter(user=user, read_at__isnull=True).count()
        
        result = query
        result["unread_count"] = unread_count
        
        return ResponseService.response("SUCCESS", result, "Notifications retrieved successfully.")
    except Exception as e:
        return ResponseService.response("INTERNAL_SERVER_ERROR", {"error": str(e)}, "Server Error")

@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def read_notification_view(request: Request, notification_id: int) -> Response:
    from django.utils import timezone
    user, error = _resolve_target_user(request)
    if error is not None:
        return error
    try:
        notification = Notification.objects.get(id=notification_id, user=user)
    except Notification.DoesNotExist:
        return ResponseService.response("NOT_FOUND", {}, "Notification not found.", status.HTTP_404_NOT_FOUND)

    notification.read_at = timezone.now()
    notification.save(update_fields=["read_at"])
    
    return ResponseService.response("SUCCESS", {}, "Notification marked as read.", status.HTTP_204_NO_CONTENT)

@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def notification_settings_view(request: Request) -> Response:
    user, error = _resolve_target_user(request)
    if error is not None:
        return error
    settings, created = UserNotificationSetting.objects.get_or_create(user=user)
    
    data = request.data
    if "push" in data:
        settings.push_enabled = data.get("push")
    if "email" in data:
        settings.email_enabled = data.get("email")
        
    settings.save()
    
    payload = {
        "push": settings.push_enabled,
        "email": settings.email_enabled
    }
    return ResponseService.response("SUCCESS", payload, "Settings updated.", status.HTTP_200_OK)
