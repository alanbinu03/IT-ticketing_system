from __future__ import annotations

import re

from app.common.exceptions import AppError

_UPPER = re.compile(r"[A-Z]")
_LOWER = re.compile(r"[a-z]")
_DIGIT = re.compile(r"\d")


def validate_password(password: str) -> None:
    if len(password) < 8 or len(password) > 128:
        raise AppError("WEAK_PASSWORD", "Password must be between 8 and 128 characters.", 400)
    if not _UPPER.search(password) or not _LOWER.search(password):
        raise AppError(
            "WEAK_PASSWORD",
            "Password must include both uppercase and lowercase letters.",
            400,
        )
    if not _DIGIT.search(password):
        raise AppError("WEAK_PASSWORD", "Password must include at least one number.", 400)
