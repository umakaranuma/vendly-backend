import json
from typing import Any

from mServices.ValidatorService import ValidatorService

VENDOR_PACKAGE_CREATE_RULES = {
    "name": "required|string|max:255",
    "price": "required|numeric",
    "features_text": "nullable|string",
    "is_active": "nullable|boolean",
}

VENDOR_PACKAGE_CREATE_MESSAGES = {
    "name.required": "Name is required.",
    "name.string": "Name must be a string.",
    "name.max": "Name may not be greater than 255 characters.",
    "price.required": "Price is required.",
    "price.numeric": "Price must be a number.",
}


def _validate_features_json(value: Any) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return None
    if isinstance(value, str):
        try:
            json.loads(value)
        except json.JSONDecodeError:
            return ["features_json must be valid JSON."]
        return None
    return ["features_json must be a JSON object, array, or string."]


def validate_vendor_package_create(data: dict) -> dict | None:
    errors = ValidatorService.validate(
        data,
        rules=VENDOR_PACKAGE_CREATE_RULES,
        custom_messages=VENDOR_PACKAGE_CREATE_MESSAGES,
    )
    fj_errors = _validate_features_json(data.get("features_json"))
    if fj_errors:
        errors = errors or {}
        errors.setdefault("features_json", []).extend(fj_errors)
    return errors if errors else None


def normalize_features_json_for_storage(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        return json.loads(value)
    return value
