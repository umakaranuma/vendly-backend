from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status

from mServices.ResponseService import ResponseService
from mServices.QueryBuilderService import QueryBuilderService
from vendly_backend.models import Category

@api_view(["GET"])
@permission_classes([AllowAny])
def categories_list_view(request: Request) -> Response:
    try:
        page = int(request.GET.get("page", 1))
        limit = int(request.GET.get("limit", 50))
        
        query = (
            QueryBuilderService("categories")
            .select("categories.id", "categories.name", "categories.slug", "categories.description", "categories.sort_order", "categories.created_at")
            .paginate(page, limit, ["categories.sort_order"], "categories.sort_order", "asc")
        )
        return ResponseService.response("SUCCESS", query, "Categories retrieved successfully.")
    except Exception as e:
        return ResponseService.response("INTERNAL_SERVER_ERROR", {"error": str(e)}, "Server Error")

@api_view(["GET"])
@permission_classes([AllowAny])
def category_detail_view(request: Request, category_id: int) -> Response:
    try:
        category = Category.objects.get(id=category_id)
        
        payload = {
            "id": category.id,
            "name": category.name,
            "slug": category.slug,
            "description": category.description,
            "sort_order": category.sort_order,
            "created_at": category.created_at,
            "updated_at": category.updated_at
        }
        return ResponseService.response("SUCCESS", payload, "Category retrieved successfully.")
    except Category.DoesNotExist:
        return ResponseService.response("NOT_FOUND", {}, "Category not found.", status.HTTP_404_NOT_FOUND)
