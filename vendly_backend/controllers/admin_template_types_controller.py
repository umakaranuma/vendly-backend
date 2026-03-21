from __future__ import annotations

from django.utils.text import slugify
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from mServices.ResponseService import ResponseService
from vendly_backend.models import InvitationTemplateType
from vendly_backend.permissions import IsAdmin


def _build_type_key(name: str) -> str:
    normalized = slugify((name or "").strip()).replace("-", "_")
    return f"template_{normalized}" if normalized else "template_type"


def _parse_bool(value, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes"}:
            return True
        if lowered in {"false", "0", "no"}:
            return False
    return default


@api_view(["GET"])
@permission_classes([AllowAny])
def template_types_public_view(request: Request) -> Response:
    items = InvitationTemplateType.objects.filter(is_active=True).order_by("sort_order", "id")
    payload = [
        {
            "id": t.id,
            "name": t.name,
            "type_key": t.type_key,
            "description": t.description,
            "sort_order": t.sort_order,
        }
        for t in items
    ]
    return ResponseService.response("SUCCESS", payload, "Template types retrieved successfully.")


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, IsAdmin])
def admin_template_types_view(request: Request) -> Response:
    if request.method == "GET":
        items = InvitationTemplateType.objects.all().order_by("sort_order", "id")
        payload = [
            {
                "id": t.id,
                "name": t.name,
                "type_key": t.type_key,
                "description": t.description,
                "sort_order": t.sort_order,
                "is_active": t.is_active,
                "created_at": t.created_at,
                "updated_at": t.updated_at,
            }
            for t in items
        ]
        return ResponseService.response("SUCCESS", payload, "Template types retrieved successfully.")

    data = request.data
    name = (data.get("name") or "").strip()
    description = data.get("description")
    sort_order = int(data.get("sort_order", 0))
    is_active = _parse_bool(data.get("is_active"), True)

    if not name:
        return ResponseService.response(
            "BAD_REQUEST",
            {"detail": "name is required."},
            "Validation error",
            status.HTTP_400_BAD_REQUEST,
        )

    type_key = _build_type_key(name)
    if InvitationTemplateType.objects.filter(type_key=type_key).exists():
        return ResponseService.response(
            "CONFLICT",
            {"detail": f"type_key `{type_key}` already exists."},
            "Validation error",
            status.HTTP_409_CONFLICT,
        )

    item = InvitationTemplateType.objects.create(
        name=name,
        type_key=type_key,
        description=description,
        sort_order=sort_order,
        is_active=is_active,
    )
    payload = {
        "id": item.id,
        "name": item.name,
        "type_key": item.type_key,
        "description": item.description,
        "sort_order": item.sort_order,
        "is_active": item.is_active,
    }
    return ResponseService.response("SUCCESS", payload, "Template type created successfully.", status.HTTP_201_CREATED)


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated, IsAdmin])
def admin_template_type_detail_view(request: Request, type_id: int) -> Response:
    try:
        item = InvitationTemplateType.objects.get(id=type_id)
    except InvitationTemplateType.DoesNotExist:
        return ResponseService.response("NOT_FOUND", {}, "Template type not found.", status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        payload = {
            "id": item.id,
            "name": item.name,
            "type_key": item.type_key,
            "description": item.description,
            "sort_order": item.sort_order,
            "is_active": item.is_active,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
        }
        return ResponseService.response("SUCCESS", payload, "Template type retrieved successfully.")

    if request.method == "PATCH":
        data = request.data

        if "name" in data:
            new_name = (data.get("name") or "").strip()
            if not new_name:
                return ResponseService.response(
                    "BAD_REQUEST",
                    {"detail": "name cannot be empty."},
                    "Validation error",
                    status.HTTP_400_BAD_REQUEST,
                )
            new_type_key = _build_type_key(new_name)
            if InvitationTemplateType.objects.exclude(id=item.id).filter(type_key=new_type_key).exists():
                return ResponseService.response(
                    "CONFLICT",
                    {"detail": f"type_key `{new_type_key}` already exists."},
                    "Validation error",
                    status.HTTP_409_CONFLICT,
                )
            item.name = new_name
            item.type_key = new_type_key

        if "description" in data:
            item.description = data.get("description")
        if "sort_order" in data:
            item.sort_order = int(data.get("sort_order", 0))
        if "is_active" in data:
            item.is_active = _parse_bool(data.get("is_active"), item.is_active)

        item.save()
        payload = {
            "id": item.id,
            "name": item.name,
            "type_key": item.type_key,
            "description": item.description,
            "sort_order": item.sort_order,
            "is_active": item.is_active,
        }
        return ResponseService.response("SUCCESS", payload, "Template type updated successfully.")

    item.delete()
    return ResponseService.response("SUCCESS", {}, "Template type deleted successfully.", status.HTTP_204_NO_CONTENT)
