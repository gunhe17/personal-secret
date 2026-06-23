from __future__ import annotations

import argparse
import asyncio
from uuid import uuid4

from personal_secret.api.core.usecase import In
from personal_secret.api.core.usecase import Out
from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.account.account import Account
from personal_secret.api.domain.account.email import Email
from personal_secret.api.domain.account.personal_lock import PersonalLock
from personal_secret.api.domain.account.personal_locked_key import PersonalLockedKey
from personal_secret.api.domain.account.personal_unlock_salt import PersonalUnlockSalt
from personal_secret.api.domain.account.login_salt import LoginSalt
from personal_secret.api.domain.account.login_verifier import LoginVerifier
from personal_secret.api.domain.account.account_repository import AccountRepository
from personal_secret.api.domain.account.account_event import AccountEvent

from personal_secret.api.domain.team.team import Team
from personal_secret.api.domain.team.team_name import TeamName
from personal_secret.api.domain.team.team_repository import TeamRepository
from personal_secret.api.domain.team.team_event import TeamEvent

from personal_secret.api.domain.team_access.team_access import TeamAccess
from personal_secret.api.domain.team_access.role import Role
from personal_secret.api.domain.team_access.team_locked_key import TeamLockedKey
from personal_secret.api.domain.team_access.team_access_repository import TeamAccessRepository
from personal_secret.api.domain.team_access.team_access_event import TeamAccessEvent

from personal_secret.api.domain.event.event.event_repository import EventRepository

from personal_secret.api.infrastructure.hash.argon2.client import argon2
from personal_secret.api.infrastructure.database.postgresql.client import db_client
from personal_secret.api.infrastructure.database.common.session import transactional_session


# #
# input

class Input(In):
    email: str
    personal_lock: str
    personal_locked_key: str
    personal_unlock_salt: str
    login_salt: str
    login_proof: str
    team_locked_key: str


# #
# output

class Output(Out):
    pass


# #
# usecase

@typecheck
async def register(*, session, event_group_id, input: Input) -> Output:
    # account
    account_event, account = AccountEvent.created(
        account=await AccountRepository.add_unique_by_email(
            session=session,
            entity=Account.new(
                email=Email.from_str(input.email),
                personal_lock=PersonalLock.from_str(input.personal_lock),
                personal_locked_key=PersonalLockedKey.from_str(input.personal_locked_key),
                personal_unlock_salt=PersonalUnlockSalt.from_str(input.personal_unlock_salt),
                login_salt=LoginSalt.from_str(input.login_salt),
                login_verifier=LoginVerifier.from_str(
                    argon2.hash(value=input.login_proof),
                ),
            ),
        ),
    )

    # personal team
    team_event, team = TeamEvent.created(
        team=await TeamRepository.add(
            session=session,
            entity=Team.new(
                name=TeamName.from_str("personal"),
            ),
        ),
    )

    # owner team access
    member_event, _ = TeamAccessEvent.created(
        team_access=await TeamAccessRepository.add_unique_by_account_and_team(
            session=session,
            entity=TeamAccess.new(
                account_id=account.id,
                team_id=team.id,
                role=Role.owner(),
                team_locked_key=TeamLockedKey.from_str(input.team_locked_key),
            ),
        ),
    )

    # return
    return Output(
        data={
            **account.to_dict(),
            "personal_team_id": str(team.id),
        },
        event=[
            event.to_dict()
            for event in (
                await EventRepository.emit(
                    session=session,
                    id=event_group_id,
                    name="auth_register",
                    atomics=[account_event, team_event, member_event],
                )
            )
        ],
    )


# #
# cli

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--personal-lock", required=True)
    parser.add_argument("--personal-locked-key", required=True)
    parser.add_argument("--personal-unlock-salt", required=True)
    parser.add_argument("--login-salt", required=True)
    parser.add_argument("--login-proof", required=True)
    parser.add_argument("--team-locked-key", required=True)
    return parser.parse_args()

async def _main():
    args = _parse_args()
    async with transactional_session(db_client.SessionLocal) as session:
        print(
            await register(
                session=session,
                event_group_id=uuid4(),
                input=Input(
                    email=args.email,
                    personal_lock=args.personal_lock,
                    personal_locked_key=args.personal_locked_key,
                    personal_unlock_salt=args.personal_unlock_salt,
                    login_salt=args.login_salt,
                    login_proof=args.login_proof,
                    team_locked_key=args.team_locked_key,
                ),
            )
        )

if __name__ == "__main__":
    asyncio.run(_main())
