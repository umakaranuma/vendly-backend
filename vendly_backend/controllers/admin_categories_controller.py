from __future__ import annotations

from django.db import IntegrityError
from django.utils.text import slugify
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status

from mServices.ResponseService import ResponseService
from vendly_backend.models import Category
from vendly_backend.permissions import IsAdmin


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsAdmin])
def admin_categories_create_view(request: Request) -> Response:
    data = request.data
    name = (data.get("name") or "").strip()
    if not name:
        return ResponseService.response(
            "BAD_REQUEST",
            {"detail": "`name` is required."},
            "Validation error",
            status.HTTP_400_BAD_REQUEST,
        )

    slug = (data.get("slug") or "").strip() or slugify(name)
    description = data.get("description")
    sort_order = data.get("sort_order", 0)

    try:
        category = Category.objects.create(
            name=name,
            slug=slug,
            description=description,
            sort_order=int(sort_order) if sort_order is not None else 0,
        )
    except IntegrityError:
        return ResponseService.response(
            "CONFLICT",
            {"detail": "Slug already exists."},
            "Validation error",
            status.HTTP_409_CONFLICT,
        )

    payload = {
        "id": category.id,
        "name": category.name,
        "slug": category.slug,
        "description": category.description,
        "sort_order": category.sort_order,
        "created_at": category.created_at,
        "updated_at": category.updated_at,
    }

    return ResponseService.response(
        "SUCCESS",
        payload,
        "Category created successfully.",
        status.HTTP_201_CREATED,
    )

