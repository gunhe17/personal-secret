from __future__ import annotations

import argparse
import asyncio
import json
from uuid import UUID

from pydantic import BaseModel

from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.secret.ciphertext import Ciphertext
from personal_secret.api.domain.secret.secret_repository import SecretRepository

from personal_secret.api.domain.account_team.team_locked_key import TeamLockedKey
from personal_secret.api.domain.account_team.account_team_repository import AccountTeamRepository

from personal_secret.api.domain.team.team_event import TeamEvent

from personal_secret.api.domain.event.event_repository import EventRepository

from personal_secret.api.infrastructure.database.postgresql.client import db_client
from personal_secret.api.infrastructure.database.common.session import transactional_session


# #
# input
# (클라가 새 team_key 생성 → 전 시크릿 재암호화 + 잔류 멤버 재봉인 후 한 번에 제출)

class SecretEntry(BaseModel):
    id: str
    value: str


class MemberEntry(BaseModel):
    account_id: str
    team_locked_key: str


class Input(BaseModel):
    secrets: list[SecretEntry] = []
    members: list[MemberEntry]


# #
# usecase

@typecheck
async def rotate(*, session, input: Input, team_id: UUID, actor_id: UUID | None = None) -> dict:
    # reencrypt
    for entry in input.secrets:
        secret = await SecretRepository.get_by_id(
            session=session,
            id=UUID(entry.id),
            team_id=team_id,
        )
        await SecretRepository.update(
            session=session,
            entity=secret.with_value(Ciphertext.from_str(entry.value)),
        )

    # rekey
    for member in input.members:
        membership = await AccountTeamRepository.get_by_account_and_team(
            session=session,
            account_id=UUID(member.account_id),
            team_id=team_id,
        )
        await AccountTeamRepository.update(
            session=session,
            entity=membership.with_team_locked_key(TeamLockedKey.from_str(member.team_locked_key)),
        )

    # return
    event, _ = TeamEvent.rotated(team_id=team_id)
    return {
        "data": {
            "secrets_reencrypted": len(input.secrets),
            "members_rekeyed": len(input.members),
        },
        "event": [
            e.to_dict()
            for e in (
                await EventRepository.emit(
                    session=session,
                    events=[event],
                    actor_id=actor_id,
                    actor_team_id=team_id,
                )
            )
        ],
    }


# #
# cli

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--team-id", required=True)
    parser.add_argument("--payload", required=True, help='JSON {"secrets":[...],"members":[...]}')
    return parser.parse_args()

async def _main():
    args = _parse_args()
    async with transactional_session(db_client.SessionLocal) as session:
        print(
            await rotate(
                session=session,
                input=Input(**json.loads(args.payload)),
                team_id=UUID(args.team_id),
            )
        )

if __name__ == "__main__":
    asyncio.run(_main())
