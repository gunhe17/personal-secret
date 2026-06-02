from __future__ import annotations

import traceback


# #
# base

class ApplicationError(Exception):
    def __init__(self, message: str | None = None, code: int | None = None):
        self.msg = message
        self.code = code
        super().__init__(message or "")

    def __trace_back__(self) -> str:
        return ''.join(traceback.format_exception(type(self), self, self.__traceback__))


# #
# categories

class ClientError(ApplicationError):
    ...


class DevelopError(ApplicationError):
    ...
