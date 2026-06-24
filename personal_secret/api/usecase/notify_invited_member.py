from __future__ import annotations

from personal_secret.api.core.usecase import EventIn
from personal_secret.api.core.validate import typecheck

from personal_secret.api.infrastructure.notification.smtp.client import smtp


# #
# input

class Input(EventIn):
    email: str
    team_name: str
    role: str

    @classmethod
    def from_event(cls, atomic) -> "Input":
        payload = atomic.payload.to_dict()
        return cls(
            email=payload["email"],
            team_name=payload["team_name"],
            role=payload["role"],
        )


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
