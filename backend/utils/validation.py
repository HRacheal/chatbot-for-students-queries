"""Request validation helpers."""

import re

from bson import ObjectId
from flask import request

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,30}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_BYTES = 72  # bcrypt only uses the first 72 bytes


class ValidationError(ValueError):
    """Raised when request data is invalid. The message is safe to show to users."""


def get_json_object():
    """Return the request body as a dict, or raise ``ValidationError``."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValidationError("Request body must be a JSON object")
    return data


def require_string(data, field, max_length, label=None, strip=True):
    value = data.get(field)
    label = label or field
    if not isinstance(value, str):
        raise ValidationError(f"{label} is required")
    if strip:
        value = value.strip()
    if not value:
        raise ValidationError(f"{label} is required")
    if len(value) > max_length:
        raise ValidationError(f"{label} must be at most {max_length} characters")
    return value


def validate_username(username):
    if not USERNAME_RE.match(username):
        raise ValidationError(
            "Username must be 3-30 characters: letters, numbers, '.', '_' or '-'"
        )
    return username


def validate_email(email):
    email = email.strip().lower()
    if len(email) > 254 or not EMAIL_RE.match(email):
        raise ValidationError("Please provide a valid email address")
    return email


def validate_password(password):
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValidationError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise ValidationError("Password is too long")
    return password


def validate_object_id(value, label="id"):
    if not isinstance(value, str) or not ObjectId.is_valid(value):
        raise ValidationError(f"Invalid {label}")
    return value
