from __future__ import annotations

import secrets

from personal_secret.api.infrastructure.token.common.client import Token


# #
# secrets

class Secrets(Token):
    def generate(self) -> str:
        return secrets.token_urlsafe(32)


# #
# client

token = Secrets()
