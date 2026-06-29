from __future__ import annotations

from typing import Literal

NORMAL_PRIVACY_LEVEL = "normal"
SENSITIVE_PRIVACY_LEVEL = "sensitive"

PrivacyLevel = Literal["normal", "sensitive"]


def normalize_privacy_level(value: str | None) -> PrivacyLevel:
    return NORMAL_PRIVACY_LEVEL if value == NORMAL_PRIVACY_LEVEL else SENSITIVE_PRIVACY_LEVEL


def is_sensitive_privacy_level(value: str | None) -> bool:
    return normalize_privacy_level(value) == SENSITIVE_PRIVACY_LEVEL
