from __future__ import annotations

from django.db import IntegrityError
from django.utils.text import slugify
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from mServices.QueryBuilderService import QueryBuilderService
from mServices.ResponseService import ResponseService
from vendly_backend.models import Category
from vendly_backend.permissions import IsAdmin


def _category_payload(category: Category) -> dict:
    return {
        "id": category.id,
        "name": category.name,
        "slug": category.slug,
        "description": category.description,
        "sort_order": category.sort_order,
        "created_at": category.created_at,
        "updated_at": category.updated_at,
    }


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, IsAdmin])
def admin_categories_view(request: Request) -> Response:
    if request.method == "GET":
        try:
            page = int(request.GET.get("page", 1))
            limit = int(request.GET.get("limit", 50))
            query = (
                QueryBuilderService("categories")
                .select(
                    "categories.id",
                    "categories.name",
                    "categories.slug",
                    "categories.description",
                    "categories.sort_order",
                    "categories.created_at",
                    "categories.updated_at",
                )
                .paginate(page, limit, ["categories.sort_order"], "categories.sort_order", "asc")
            )
            return ResponseService.response("SUCCESS", query, "Categories retrieved successfully.")
        except Exception as e:
            return ResponseService.response("INTERNAL_SERVER_ERROR", {"error": str(e)}, "Server Error")

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

    return ResponseService.response(
        "SUCCESS",
        _category_payload(category),
        "Category created successfully.",
        status.HTTP_201_CREATED,
    )


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated, IsAdmin])
def admin_category_detail_view(request: Request, category_id: int) -> Response:
    try:
        category = Category.objects.get(id=category_id)
    except Category.DoesNotExist:
        return ResponseService.response("NOT_FOUND", {}, "Category not found.", status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        return ResponseService.response("SUCCESS", _category_payload(category), "Category retrieved successfully.")

    if request.method == "PATCH":
        data = request.data
        if "name" in data:
            name = (data.get("name") or "").strip()
            if not name:
                return ResponseService.response(
                    "BAD_REQUEST",
                    {"detail": "`name` cannot be empty."},
                    "Validation error",
                    status.HTTP_400_BAD_REQUEST,
                )
            category.name = name

        if "slug" in data:
            new_slug = (data.get("slug") or "").strip() or slugify(category.name)
            if Category.objects.exclude(id=category.id).filter(slug=new_slug).exists():
                return ResponseService.response(
                    "CONFLICT",
                    {"detail": "Slug already exists."},
                    "Validation error",
                    status.HTTP_409_CONFLICT,
                )
            category.slug = new_slug

        if "description" in data:
            category.description = data.get("description")
        if "sort_order" in data:
            category.sort_order = int(data.get("sort_order", 0))

        try:
            category.save()
        except IntegrityError:
            return ResponseService.response(
                "CONFLICT",
                {"detail": "Slug already exists."},
                "Validation error",
                status.HTTP_409_CONFLICT,
            )

        return ResponseService.response(
            "SUCCESS",
            _category_payload(category),
            "Category updated successfully.",
        )

    category.delete()
    return ResponseService.response("SUCCESS", {}, "Category deleted successfully.", status.HTTP_204_NO_CONTENT)
