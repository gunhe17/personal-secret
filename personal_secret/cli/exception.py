from __future__ import annotations


# #
# base

class CliError(Exception):
    ...


# #
# specific

class ApiError(CliError):
    def __init__(self, message: str):
        super().__init__(message)


class UsageError(CliError):
    def __init__(self, message: str):
        super().__init__(message)
