from __future__ import annotations

from typing import Callable

from django.http import HttpRequest, HttpResponse, JsonResponse

try:
    import mServices.ResponseService as ResponseService
except ImportError:  # pragma: no cover
    ResponseService = None  # type: ignore


class EndpointPermissionMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        return response

    def permission_denied(self, message: str = "Permission denied") -> HttpResponse:
        if ResponseService is not None:
            return ResponseService.response(
                "FORBIDDEN",
                {"detail": message},
                "You do not have permission to perform this action.",
            )

        return JsonResponse(
            {
                "status": "FORBIDDEN",
                "data": {"detail": message},
                "message": "You do not have permission to perform this action.",
            },
            status=403,
        )

