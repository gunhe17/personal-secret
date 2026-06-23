from __future__ import annotations

from personal_secret.api.core.usecase import In
from personal_secret.api.core.validate import typecheck

from personal_secret.api.infrastructure.notification.smtp.client import smtp


# #
# input

class Input(In):
    _source_event = "team_access.created"

    email: str
    team_name: str
    role: str


# #
# reaction

@typecheck
async def run(*, session, input: Input) -> None:
    # notify
    await smtp.send(
        to=input.email,
        subject=f"{input.team_name} 팀에 초대되었습니다",
        body=f"{input.role} 권한으로 초대되었습니다. 로그인해 접근하세요.",
    )
