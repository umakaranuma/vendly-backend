from __future__ import annotations

from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status

from mServices.ResponseService import ResponseService
from vendly_backend.models import Notification
from vendly_backend.permissions import IsAdmin


def _paginate(queryset, page: int, limit: int):
    total = queryset.count()
    page = max(page, 1)
    limit = max(limit, 1)
    offset = (page - 1) * limit
    items = list(queryset[offset : offset + limit])
    next_page = page + 1 if offset + limit < total else None
    return items, total, next_page


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdmin])
def admin_notifications_activity_view(request: Request) -> Response:
    page = int(request.GET.get("page", 1))
    limit = int(request.GET.get("limit", 20))

    user_id = request.GET.get("user_id")
    read = request.GET.get("read")  # true | false | ""
    notif_type = request.GET.get("type", "").strip()

    qs = Notification.objects.select_related("user").order_by("-created_at")
    if user_id:
        qs = qs.filter(user_id=int(user_id))
    if notif_type:
        qs = qs.filter(type=notif_type)
    if read == "true":
        qs = qs.filter(read_at__isnull=False)
    elif read == "false":
        qs = qs.filter(read_at__isnull=True)

    items, total, next_page = _paginate(qs, page, limit)

    payload = []
    for n in items:
        user_name = f"{n.user.first_name} {n.user.last_name}".strip() if n.user else ""
        payload.append(
            {
                "id": n.id,
                "user_id": n.user_id,
                "user_name": user_name,
                "type": n.type,
                "title": n.title,
                "body": n.body,
                "data": n.data,
                "read_at": n.read_at,
                "created_at": n.created_at,
                "status": "seen" if n.read_at is not None else "unseen",
            }
        )

    return ResponseService.response(
        "SUCCESS",
        {"items": payload, "total": total, "next_page": next_page},
        "Admin notifications activity retrieved successfully.",
        status.HTTP_200_OK,
    )


@api_view(["PATCH"])
@permission_classes([IsAuthenticated, IsAdmin])
def admin_notification_activity_update_view(request: Request, notification_id: int) -> Response:
    read = request.data.get("read")  # boolean
    if read is None:
        return ResponseService.response(
            "BAD_REQUEST",
            {"detail": "Body must include `read` (true/false)."},
            "Validation error",
            status.HTTP_400_BAD_REQUEST,
        )

    # Accept boolean-ish values
    if isinstance(read, str):
        if read.lower() == "true":
            read = True
        elif read.lower() == "false":
            read = False

    if not isinstance(read, bool):
        return ResponseService.response(
            "BAD_REQUEST",
            {"detail": "`read` must be a boolean."},
            "Validation error",
            status.HTTP_400_BAD_REQUEST,
        )

    try:
        n = Notification.objects.get(id=notification_id)
    except Notification.DoesNotExist:
        return ResponseService.response(
            "NOT_FOUND",
            {},
            "Notification not found.",
            status.HTTP_404_NOT_FOUND,
        )

    n.read_at = timezone.now() if read else None
    n.save(update_fields=["read_at"])

    return ResponseService.response(
        "SUCCESS",
        {"id": n.id, "read_at": n.read_at},
        "Notification status updated successfully.",
        status.HTTP_200_OK,
    )

