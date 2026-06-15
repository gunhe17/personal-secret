from __future__ import annotations

from personal_secret.api.infrastructure.outbox.audit import audit_log


# #
# registry

HANDLERS = [
    audit_log,
]


# #
# dispatch

def dispatch(*, event: dict) -> None:
    for handler in HANDLERS:
        handler.handle(event=event)
