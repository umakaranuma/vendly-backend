from __future__ import annotations

import json

from rest_framework.decorators import api_view
from rest_framework.request import Request

import mServices.ResponseService as ResponseService
import mServices.QueryBuilderService as QueryBuilderService
from mServices.ValidatorService import ValidatorService

from vendly_backend.models.example import ExampleItem


@api_view(["GET"])
def list_items(request: Request) -> ResponseService:  # type: ignore[valid-type]
    """
    Minimal example list endpoint demonstrating the mServices pattern.
    """
    try:
        ValidatorService.validate_request(request)  # type: ignore[attr-defined]

        raw_filter = request.GET.get("filter", "{}") or "{}"
        filter_json = json.loads(raw_filter)
        search_string = (request.GET.get("search") or "").strip()

        allowed_fields = ["id", "name"]

        result = QueryBuilderService.build_query(
            model=ExampleItem,
            filters=filter_json,
            search=search_string,
            allowed_fields=allowed_fields,
        )

        return ResponseService.response(
            "SUCCESS",
            result,
            "Items fetched successfully.",
        )
    except Exception as exc:  # noqa: BLE001
        return ResponseService.response(
            "INTERNAL_SERVER_ERROR",
            {"error": str(exc)},
            "An unexpected error occurred.",
        )

