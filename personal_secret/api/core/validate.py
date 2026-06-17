from __future__ import annotations

from functools import wraps
from typing import get_type_hints

from personal_secret.api.core.exception import DevelopError


def typecheck(func):
    hints: dict | None = None

    @wraps(func)
    def wrapper(*args, **kwargs):
        nonlocal hints
        if hints is None:
            hints = get_type_hints(func)
        for name, value in kwargs.items():
            expected = hints.get(name)
            if expected is None:
                continue
            if not isinstance(value, expected):
                raise DevelopError(
                    message=f"{name} {expected} 필요 (실제: {type(value).__name__})",
                    code=500,
                )
        return func(*args, **kwargs)

    return wrapper
