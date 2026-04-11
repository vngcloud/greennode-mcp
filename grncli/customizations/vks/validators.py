"""Input validators for VKS commands."""
from __future__ import annotations

import re

# VKS IDs: alphanumeric + hyphens only (e.g. k8s-df9600ed-08c4-4f83-a2d8-0d6434211ef8)
ID_PATTERN = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9]$')


def validate_id(value: str, name: str) -> None:
    """Validate that an ID contains only safe characters."""
    if not value or not ID_PATTERN.match(value):
        raise ValueError(
            f"Invalid {name}: '{value}'. "
            f"Must contain only alphanumeric characters and hyphens."
        )
