from __future__ import annotations

import json
import os

from personal_secret.api.config import OutboxConfig
from personal_secret.api.config import get_outbox_config


# #
# audit log

class AuditLog:
    def __init__(self, *, config: OutboxConfig):
        self._config = config

    def handle(self, *, event: dict) -> None:
        # 경로는 append 시점에 읽는다 — 환경/테스트가 덮어쓸 수 있게
        path = self._config.AUDIT_LOG_PATH
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        line = json.dumps(event, ensure_ascii=False, sort_keys=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")


# #
# AuditLog

audit_log = AuditLog(config=get_outbox_config())
