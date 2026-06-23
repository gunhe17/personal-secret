from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from personal_secret.api.core.behavior import Context

from personal_secret.api.behavior.common.exception import ForbiddenError, UnauthorizedError

from personal_secret.api.domain.account_token.fingerprint import Fingerprint
from personal_secret.api.domain.account_token.account_token_repository import AccountTokenRepository
from personal_secret.api.domain.team_access.team_access_repository import TeamAccessRepository

from personal_secret.api.infrastructure.hash.sha256.client import sha256


# #
# account

@dataclass(frozen=True)
class AccountContext(Context):
    account_id: UUID

    @classmethod
    async def setup(
        cls,
        *,
        session: AsyncSession,
        authorization: str | None = None,
    ) -> AccountContext:
        return AccountContext(
            account_id=(
                await _resolve_account(
                    session=session, 
                    authorization=authorization
                )
            )
        )


# #
# team access

@dataclass(frozen=True)
class TeamAccessContext(Context):
    account_id: UUID
    team_id: UUID

    @classmethod
    async def setup(
        cls,
        team_id: UUID,
        *,
        session: AsyncSession,
        account: AccountContext,
    ) -> TeamAccessContext:
        await TeamAccessRepository.get_valid_by_account_and_team(
            session=session,
            account_id=account.account_id,
            team_id=team_id,
        )
        return TeamAccessContext(
            account_id=account.account_id,
            team_id=team_id,
        )


# #
# owner

@dataclass(frozen=True)
class OwnerAccessContext(Context):
    account_id: UUID
    team_id: UUID

    @classmethod
    async def setup(
        cls,
        team_id: UUID,
        *,
        session: AsyncSession,
        account: AccountContext,
    ) -> OwnerAccessContext:
        team_access = await TeamAccessRepository.get_valid_by_account_and_team(
            session=session,
            account_id=account.account_id,
            team_id=team_id,
        )
        if not team_access.role.is_owner():
            raise ForbiddenError("Team")

        return OwnerAccessContext(
            account_id=account.account_id,
            team_id=team_id,
        )


# #
# helpers

async def _resolve_account(*, session: AsyncSession, authorization: str | None) -> UUID:
    # bearer
    if authorization is None or not authorization.startswith("Bearer "):
        raise UnauthorizedError()

    # authenticate
    raw = authorization[len("Bearer "):].strip()
    account_token = await AccountTokenRepository.get_valid_by_fingerprint(
        session=session,
        fingerprint=Fingerprint.from_str(sha256.hash(value=raw)),
    )
    return account_token.account_id