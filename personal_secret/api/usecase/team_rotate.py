from __future__ import annotations

import argparse
import asyncio
import json
from uuid import UUID

from personal_secret.api.core.usecase import In
from personal_secret.api.core.usecase import Out
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

class Input(In):
    secrets: dict[str, str] = {}   # secret_id -> ciphertext
    members: dict[str, str]        # account_id -> team_locked_key


# #
# output

class Output(Out):
    pass


# #
# usecase

@typecheck
async def rotate(*, session, input: Input, team_id: UUID, actor_id: UUID | None = None) -> Output:
    # reencrypt
    for id, value in input.secrets.items():
        secret = await SecretRepository.get_by_id(
            session=session,
            id=UUID(id),
            team_id=team_id,
        )
        await SecretRepository.update(
            session=session,
            entity=secret.with_value(Ciphertext.from_str(value)),
        )

    # rekey
    for account_id, team_locked_key in input.members.items():
        membership = await AccountTeamRepository.get_by_account_and_team(
            session=session,
            account_id=UUID(account_id),
            team_id=team_id,
        )
        await AccountTeamRepository.update(
            session=session,
            entity=membership.with_team_locked_key(TeamLockedKey.from_str(team_locked_key)),
        )

    # return
    event, _ = TeamEvent.rotated(team_id=team_id)
    return Output.new(
        data={
            "secrets_reencrypted": len(input.secrets),
            "members_rekeyed": len(input.members),
        },
        event=[
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
    )


# #
# cli

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--team-id", required=True)
    parser.add_argument("--payload", required=True, help='JSON {"secrets":{id:ct},"members":{account_id:key}}')
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
