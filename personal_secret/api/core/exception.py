from __future__ import annotations

import inspect
import os
import traceback

from personal_secret.api.core.i18n import DEFAULT, render


# #
# base

class ApplicationError(Exception):
    def __init__(
        self,
        *,
        message: str | None = None,
        key: str | None = None,
        params: dict | None = None,
        code: int | None = None,
    ):
        self.key = key
        self.params = params or {}
        self.code = code

        self.message = (
            render(key=key, params=self.params, locale=DEFAULT)
            if message is None and key is not None
            else (message or "")
        )
        self.category = self._category()  # "ClientError" | "DevelopError"
        self.location = self._origin()  # "personal_secret/api/.../x.py:135"
        self.msg = (
            f"{type(self).__name__} - {self.category} ({self.code})"
            f"\n\t message: {self.message}"
            f"\n\t path: {self.location}"
        )
        super().__init__(self.msg)

    def _category(self) -> str:
        for klass in type(self).__mro__:
            if klass.__name__ in ("ClientError", "DevelopError"):
                return klass.__name__
        return "ApplicationError"

    @staticmethod
    def _origin() -> str:
        current = inspect.currentframe()
        frame = current.f_back if current is not None else None
        while frame is not None and frame.f_code.co_filename.endswith("exception.py"):
            frame = frame.f_back
        if frame is None:
            return "?"
        path = frame.f_code.co_filename
        i = path.find("personal_secret")
        rel = path[i:] if i != -1 else os.path.basename(path)
        return f"{rel}:{frame.f_lineno}"

    def __trace_back__(self) -> str:
        return ''.join(traceback.format_exception(type(self), self, self.__traceback__))


# #
# categories

class ClientError(ApplicationError):
    ...


class DevelopError(ApplicationError):
    ...
