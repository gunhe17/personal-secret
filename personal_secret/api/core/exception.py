from __future__ import annotations

import inspect
import os
import traceback


# #
# base

class ApplicationError(Exception):
    def __init__(self, message: str | None = None, code: int | None = None):
        self.code = code
        self.category = self._category()                     # "ClientError" | "DevelopError"
        self.location = self._origin()                       # "personal_secret/api/.../x.py:135"
        self.msg = (
            f"{type(self).__name__} - {self.category} ({self.code})"
            f"\n\t message: {message or ''}"
            f"\n\t path: {self.location}"
        )
        super().__init__(self.msg)

    def _category(self) -> str:
        # MRO에서 2분류(ClientError/DevelopError)를 찾아 큰 범주 표기
        for klass in type(self).__mro__:
            if klass.__name__ in ("ClientError", "DevelopError"):
                return klass.__name__
        return "ApplicationError"

    @staticmethod
    def _origin() -> str:
        # 예외 정의(exception.py) 프레임을 건너뛰어 실제 raise한 코드 위치를 찾는다
        frame = inspect.currentframe().f_back
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
