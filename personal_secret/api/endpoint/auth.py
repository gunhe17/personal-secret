from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import Depends, Header
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from personal_secret.api.domain.common.exception import ForbiddenError, UnauthorizedError

from personal_secret.api.domain.token.fingerprint import Fingerprint
from personal_secret.api.domain.token.token_repository import TokenRepository

from personal_secret.api.domain.account_team.account_team import AccountTeam
from personal_secret.api.domain.account_team.account_team_repository import AccountTeamRepository

from personal_secret.api.infrastructure.crypto.client import crypto
from personal_secret.api.infrastructure.postgresql.session import transactional_session_helper

from personal_secret.api.usecase import auth_register
from personal_secret.api.usecase import auth_login
from personal_secret.api.usecase import auth_get_only_salts


# #
# command

async def post_register(
    body: auth_register.Input,
    session: AsyncSession = Depends(transactional_session_helper),
) -> JSONResponse:
    registered = await auth_register.register(session=session, input=body)
    return JSONResponse(status_code=200, content=registered)


async def get_salts(
    email: str,
    session: AsyncSession = Depends(transactional_session_helper),
) -> JSONResponse:
    found = await auth_get_only_salts.get_only_salts(session=session, input=auth_get_only_salts.Input(email=email))
    return JSONResponse(status_code=200, content=found)


async def post_login(
    body: auth_login.Input,
    session: AsyncSession = Depends(transactional_session_helper),
) -> JSONResponse:
    logged_in = await auth_login.login(session=session, input=body)
    return JSONResponse(status_code=200, content=logged_in)


# #
# guard — authentication

async def require_auth(
    authorization: str | None = Header(default=None),
    session: AsyncSession = Depends(transactional_session_helper),
) -> UUID:
    # bearer
    if authorization is None or not authorization.startswith("Bearer "):
        raise UnauthorizedError()
    raw = authorization[len("Bearer "):].strip()

    # lookup
    token = await TokenRepository.find_by_fingerprint(
        session=session,
        fingerprint=Fingerprint.from_str(crypto.hash_token(token=raw)),
    )
    if token is None or token.is_expired(now=datetime.now(timezone.utc)):
        raise UnauthorizedError()
    return token.account_id


# #
# guard — authorization

async def require_member(
    team_id: UUID,
    account_id: UUID = Depends(require_auth),
    session: AsyncSession = Depends(transactional_session_helper),
) -> AccountTeam:
    membership = await AccountTeamRepository.find_by_account_and_team(
        session=session,
        account_id=account_id,
        team_id=team_id,
    )
    if membership is None:
        raise ForbiddenError("Team")

    # RLS 백스톱 — 이 트랜잭션의 모든 tenant 쿼리를 team_id 로 강제
    await session.execute(
        text("SELECT set_config('app.current_team', :team, true)"),
        {"team": str(team_id)},
    )
    return membership


async def require_owner(membership: AccountTeam = Depends(require_member)) -> AccountTeam:
    if not membership.role.is_owner():
        raise ForbiddenError("Team")
    return membership
