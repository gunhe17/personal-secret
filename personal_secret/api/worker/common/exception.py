from __future__ import annotations

from personal_secret.api.core.exception import DevelopError


# #
# base

class WorkerDevelopError(DevelopError):
    ...


# #
# lifecycle

class NoWorkRegisteredError(WorkerDevelopError):
    def __init__(self, name: str):
        super().__init__(key="no_work_registered", params={"name": name}, code=500)


# #
# execution

class WorkFailedError(WorkerDevelopError):
    def __init__(self, channel: str, reason: str):
        super().__init__(key="work_failed", params={"channel": channel, "reason": reason}, code=500)
