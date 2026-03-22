# Controller Endpoint Implementation Rule

All Django controllers should follow this standardized implementation pattern for listing and creating resources.

## 1. Imports
Include high-level Django utilities and relevant project services.
```python
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from rest_framework.decorators import api_view
import json
import mServices.ResponseService as ResponseService
import mServices.QueryBuilderService as QueryBuilderService
from mServices.ValidatorService import ValidatorService
from envoy.services.entity_validator_service import EntityService
```

## 2. API Entry Point
Use the `@api_view` decorator and route requests to dedicated handler functions.
```python
@api_view(["GET", "POST"])
def get_resource(request):
    if request.method == "GET":
        return list_resources(request)
    elif request.method == "POST":
        return create_resource(request)
```

## 3. List Implementation
Utilize the `QueryBuilderService` for filtering, searching, and pagination.
- **Select Columns**: Explicitly list all columns needed.
- **Parameters**: Capture `filters`, `search`, `page`, `limit`, `sort_by`, and `sort_dir`.
- **Query Construction**: Chain `.select()`, `.apply_conditions()`, and `.paginate()`.
- **Response**: Always wrap in `ResponseService.response`.

## 4. Creation Implementation
Follow a strict validation and storage flow.
1. **Validation Rules**: Define `rules` and `custom_messages`.
2. **Validation Call**: Use `ValidatorService.validate(data, rules, custom_messages)`.
3. **Entity Storage**: Use `EntityService.store(entity_action, None, user=request.user)`.
4. **Model Creation**: Perform the create operation using validated data.
5. **Related Records**: Handle any bulk creation of related records (e.g., authorities).
6. **Success Response**: Return the created object data via `ResponseService`.

## 5. Standard Error Handling
Consistency in catching `ValidationError`, `ValueError`, and generic `Exception` is mandatory to ensure structured error responses.

```python
try:
    # Logic
except ValidationError as e:
    return ResponseService.response("VALIDATION_ERROR", e.message_dict, "Validation Error")
except ValueError:
    return ResponseService.response("VALIDATION_ERROR", {"pagination": ["Invalid parameters"]}, "Invalid Request")
except Exception as e:
    return ResponseService.response("INTERNAL_SERVER_ERROR", {"error": str(e)}, "Server Error")
```
