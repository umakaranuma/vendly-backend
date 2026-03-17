---
name: django-code-writing
description: Guides writing Django/DRF backend code following the vendly_backend project structure and conventions. Use when creating views/controllers, models, migrations, URLs, serializers, or when the user asks about Django project structure in this codebase. Always trigger this skill when the user asks to create or modify any backend file — controllers, services, models, URLs, middleware, or migrations — in a Django project that uses ResponseService, QueryBuilderService, or ValidatorService patterns.
---

# Django Code Writing

Best practices and conventions for writing backend code in the **vendly_backend** Django/DRF project.

---

## Project Structure

```
vendly_backend/
├── controllers/              # One file per resource (views)
│   └── services/             # View-facing services only
├── models/                   # One file per model or logical group
│   └── __init__.py
├── migrations/               # Django migrations (no subfolders)
├── services/                 # Business logic (entity_service.py, email_service.py)
├── middleware.py             # EndpointPermissionMiddleware + ENDPOINT_PERMISSIONS
├── urls.py                   # Central URL config
└── settings/
    ├── base.py               # Shared config (ROOT_URLCONF = "vendly_backend.urls")
    └── development.py        # Environment-specific overrides
```

**Key rules:**
- Controllers live in `vendly_backend/controllers/` — one file per resource (e.g. `roles_controller.py`)
- Business logic lives in `vendly_backend/services/` — not inside controllers
- Shared utilities (`ResponseService`, `QueryBuilderService`, `ValidatorService`) come from `mServices` — do not duplicate them
- Auth routes use `path("api/login", include("accounts.urls"))` in `vendly_backend/urls.py`

---

## API Response Format

**Always** use `ResponseService` — never return raw `JsonResponse()` or `Response()`.

```python
from mServices.ResponseService import ResponseService

# Success
return ResponseService.response("SUCCESS", result_data, "Records retrieved successfully!")

# Error
return ResponseService.response("VALIDATION_ERROR", errors, "Validation Error")
```

### Status Keys

| Key | HTTP |
|---|---|
| `SUCCESS` | 200 |
| `NOT_FOUND` | 404 |
| `FORBIDDEN` | 403 |
| `INTERNAL_SERVER_ERROR` | 500 |
| `VALIDATION_ERROR` | 417 |
| `UNAUTHORIZED` | 401 |
| `CONFLICT` | 409 |

Response body always includes: `is_success`, `message`, `result`, `system_code`.

---

## List Endpoints — QueryBuilderService

All list/get-all endpoints must use `QueryBuilderService` for filters, search, sorting, and pagination.

```python
from mServices.QueryBuilderService import QueryBuilderService

query = (
    QueryBuilderService("core_reasons")
    .select("core_reasons.id", "reason", "type_id", "description")
    .leftJoin("other_table as alias", "alias.id", "core_reasons.foreign_key")   # if needed
    .apply_conditions(filter_json, allowed_filters, search_string, search_columns)
    .paginate(page, limit, allowed_sorting_columns, sort_by, sort_dir)
)
```

**Standard request params:** `page` (default 1), `limit` (default 10), `search`, `filters` (JSON), `sort_by`, `sort_dir` (default `"desc"`).

### Full Controller Example

```python
from rest_framework.decorators import api_view
from mServices.ResponseService import ResponseService
from mServices.QueryBuilderService import QueryBuilderService

@api_view(["GET", "POST"])
def reasons_view(request):
    if request.method == "GET":
        return list_reasons(request)
    elif request.method == "POST":
        return create_reason(request)

def list_reasons(request):
    try:
        page = int(request.GET.get("page", 1))
        limit = int(request.GET.get("limit", 10))
        search_string = request.GET.get("search", "")
        filter_json = request.GET.get("filters", "{}")

        allowed_filters = ["reason", "type_id"]
        search_columns = ["reason", "description"]
        sort_by = request.GET.get("sort_by") or "core_reasons.id"
        sort_dir = request.GET.get("sort_dir") or "desc"
        allowed_sorting_columns = ["core_reasons.id", "reason", "type_id"]

        query = (
            QueryBuilderService("core_reasons")
            .select("core_reasons.id", "reason", "type_id", "description")
            .apply_conditions(filter_json, allowed_filters, search_string, search_columns)
            .paginate(page, limit, allowed_sorting_columns, sort_by, sort_dir)
        )
        return ResponseService.response("SUCCESS", query, "Reasons retrieved successfully!")
    except Exception as e:
        return ResponseService.response("INTERNAL_SERVER_ERROR", {"error": str(e)}, "Server Error")
```

---

## Validation — ValidatorService

```python
from mServices.ValidatorService import ValidatorService

errors = ValidatorService.validate(request.data, rules={
    "name": "required|max:255",
    "email": "required|email|exists:users,email",
}, custom_messages={
    "name.required": "Name is required.",
})

if errors:
    return ResponseService.response("VALIDATION_ERROR", errors, "Validation Error")
```

---

## Authentication — JWT

- Use **djangorestframework-simplejwt**: `RefreshToken.for_user(user)`, `JWTAuthentication`
- **Route protection** is handled by `EndpointPermissionMiddleware` in `vendly_backend/middleware.py`
- Public endpoints (login, webhooks, callbacks) must be listed in `ENDPOINT_PERMISSIONS` with value `"public"`
- Login responses must use the standard format:

```python
return ResponseService.response("SUCCESS", {
    "access_token": str(token.access_token),
    "user": user_data
}, "Login successful")
```

### Adding a Public Endpoint

In `vendly_backend/middleware.py`, add the route to `ENDPOINT_PERMISSIONS`:

```python
ENDPOINT_PERMISSIONS = {
    "api/login": "public",
    "api/verify-invitation": "public",
    "api/your-new-public-route": "public",   # ← add here
}
```

---

## Database Transactions

Use `transaction.atomic()` whenever **multiple tables** are modified together.

```python
from django.db import transaction

try:
    with transaction.atomic():
        # all writes here succeed or roll back together
        ModelA.objects.create(...)
        ModelB.objects.update(...)
except Exception as e:
    return ResponseService.response("INTERNAL_SERVER_ERROR", {"error": str(e)}, "Server Error")
```

---

## SQL Safety

**Never** concatenate user input into raw SQL strings.

```python
# ❌ Wrong — SQL injection risk
cursor.execute(f"SELECT * FROM users WHERE name = '{request.data['name']}'")

# ✅ Correct — parameterized query
cursor.execute("SELECT * FROM users WHERE name = %s", [request.data["name"]])

# ✅ Also correct — Django ORM
User.objects.filter(name=request.data["name"])

# ✅ Also correct — QueryBuilderService (uses parameter binding internally)
QueryBuilderService("users").apply_conditions(...)
```

---

## URL & Controller Conventions

- All API routes are prefixed with `api/` (e.g. `path("api/roles", get_roles)`)
- Import controller functions explicitly in `vendly_backend/urls.py` to avoid circular imports
- Combined list/create: one view function with `@api_view(["GET", "POST"])`, branch on `request.method`
- Detail routes (get/update/delete): separate view functions on distinct paths

```python
# vendly_backend/urls.py
from vendly_backend.controllers.roles_controller import roles_view, role_detail_view

urlpatterns = [
    path("api/roles", roles_view),
    path("api/roles/<int:role_id>", role_detail_view),
]
```

---

## Migrations

- One migration per logical change set — don't mix unrelated schema changes
- Follow Django's default naming: `XXXX_description.py`
- Keep migrations reversible where possible (`RunPython` with reverse function)
- Do not add FK constraints in the same migration as large schema changes — follow project convention

---

## Environment Variables

When a new env variable is introduced, always add the key (with a placeholder, no secrets) to **`.env.example`**:

```
# .env.example
JWT_SECRET=your-secret-here
EXTERNAL_API_URL=https://api.example.com
DB_DATABASE=vendly_db
```

---

## Rate Limiting

- Apply throttle classes to API endpoint groups; sensible default: **60 req/min per user/IP**
- Apply **stricter limits** to auth-sensitive endpoints (login, password reset, forgot-password)
- Use Django REST Framework's built-in throttle classes or a custom middleware
