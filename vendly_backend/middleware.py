import mServices.ResponseService as ResponseService
from django.urls import Resolver404, resolve
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken

from vendly_backend.models import CoreUser as User


class EndpointPermissionMiddleware:
    """
    Middleware to enforce authentication and role-based access control for specific endpoints.
    Also catches invalid URLs and returns a proper 404 JSON response.
    """

    ENDPOINT_PERMISSIONS = {
        "api/admin/login": "public",
        "api/auth/register/customer": "public",
        "api/auth/register/vendor": "public",
        "api/auth/confirm-otp": "public",
        "api/auth/login": "public",
        "api/categories": "public",
        "api/categories/<int:category_id>": "public",
        "api/vendors": "public",
        "api/vendors/<int:vendor_id>": "public",
        "api/vendors/<int:vendor_id>/packages": "public",
        "api/vendors/<int:vendor_id>/posts": "public",
        "api/vendors/<int:vendor_id>/reviews": "public",
        "api/posts": "public",
        "api/posts/<int:post_id>": "public",
        "api/feed/posts": "public",
        "api/feed/posts/<int:post_id>/comments": "public",
        "api/subscription/plans": "public",
    }

    def __init__(self, get_response):
        self.get_response = get_response
        self.jwt_auth = JWTAuthentication()

    def __call__(self, request):
        try:
            setattr(request, "_dont_enforce_csrf_checks", True)

            try:
                resolved_path = resolve(request.path_info).route
            except Resolver404:
                return ResponseService.response(
                    "NOT_FOUND",
                    {
                        "endpoint": [
                            {
                                "error_type": "not_found",
                                "tokens": {"_attribute": "endpoint"},
                            }
                        ]
                    },
                    "Endpoint does not exist.",
                )

            permission = self.ENDPOINT_PERMISSIONS.get(resolved_path, "authenticated")

            if permission == "public":
                # Optional JWT: anonymous OK; valid Bearer attaches user for admin/vendor actions on the same path.
                # Invalid/expired tokens are stripped so DRF treats the request as anonymous (no spurious 401).
                auth_header = request.headers.get("Authorization", None)
                if auth_header and auth_header.startswith("Bearer "):
                    try:
                        raw_token = auth_header.split(" ")[1]
                        validated_token = self.jwt_auth.get_validated_token(raw_token)
                        user_id = validated_token.get("user_id")
                        if user_id:
                            user = User.objects.filter(id=user_id).first()
                            if user:
                                request.user = user
                            elif "HTTP_AUTHORIZATION" in request.META:
                                del request.META["HTTP_AUTHORIZATION"]
                    except (InvalidToken, AuthenticationFailed, IndexError, KeyError, TypeError):
                        if "HTTP_AUTHORIZATION" in request.META:
                            del request.META["HTTP_AUTHORIZATION"]
                return self.get_response(request)

            auth_header = request.headers.get("Authorization", None)

            if not auth_header or not auth_header.startswith("Bearer "):
                return ResponseService.response(
                    "UNAUTHORIZED",
                    {
                        "token": [
                            {
                                "error_type": "required",
                                "tokens": {"_attribute": "token"},
                            }
                        ]
                    },
                    "Invalid authentication credentials.",
                )

            try:
                raw_token = auth_header.split(" ")[1]
                validated_token = self.jwt_auth.get_validated_token(raw_token)
                user_id = validated_token.get("user_id")

                if not user_id:
                    return ResponseService.response(
                        "UNAUTHORIZED",
                        {
                            "token": [
                                {
                                    "error_type": "invalid",
                                    "tokens": {"_attribute": "token"},
                                }
                            ]
                        },
                        "Invalid authentication credentials.",
                    )

                user = User.objects.filter(id=user_id).first()

                if not user:
                    return ResponseService.response(
                        "UNAUTHORIZED",
                        {
                            "user": [
                                {
                                    "error_type": "not_found",
                                    "tokens": {"_attribute": "user"},
                                }
                            ]
                        },
                        "Invalid authentication credentials.",
                    )

                request.user = user

            except InvalidToken:
                return ResponseService.response(
                    "UNAUTHORIZED",
                    {
                        "token": [
                            {
                                "error_type": "invalid",
                                "tokens": {"_attribute": "token"},
                            }
                        ]
                    },
                    "Token is invalid or expired.",
                )
            except AuthenticationFailed as e:
                return ResponseService.response(
                    "UNAUTHORIZED",
                    {
                        "token": [
                            {
                                "error_type": "authentication_failed",
                                "tokens": {"_attribute": "token"},
                            }
                        ]
                    },
                    str(e),
                )

        except Exception as e:
            return ResponseService.response(
                "INTERNAL_SERVER_ERROR",
                {"error": str(e)},
                "An unexpected error occurred.",
            )

        return self.get_response(request)

