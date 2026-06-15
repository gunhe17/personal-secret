from __future__ import annotations

from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from personal_secret.api.infrastructure.postgresql.session import transactional_session_helper

from personal_secret.api.domain.account_team.account_team import AccountTeam

from personal_secret.api.endpoint.auth import require_auth
from personal_secret.api.endpoint.auth import require_member
from personal_secret.api.endpoint.auth import require_owner

from personal_secret.api.usecase.team import create
from personal_secret.api.usecase.team import invite
from personal_secret.api.usecase.team import remove
from personal_secret.api.usecase.team import rotate


# #
# command

async def post_create(
    body: create.Input,
    account_id: UUID = Depends(require_auth),
    session: AsyncSession = Depends(transactional_session_helper),
) -> JSONResponse:
    created = await create.create(session=session, input=body, account_id=account_id)
    return JSONResponse(status_code=200, content=created)


async def get_key(
    team_id: UUID,
    membership: AccountTeam = Depends(require_member),
    session: AsyncSession = Depends(transactional_session_helper),
) -> JSONResponse:
    return JSONResponse(status_code=200, content={"data": membership.to_member_key()})


# #
# member management

async def post_invite(
    team_id: UUID,
    body: invite.Input,
    _owner: AccountTeam = Depends(require_owner),
    session: AsyncSession = Depends(transactional_session_helper),
) -> JSONResponse:
    invited = await invite.invite(session=session, input=body, team_id=team_id)
    return JSONResponse(status_code=200, content=invited)


async def delete_member(
    team_id: UUID,
    account_id: UUID,
    _owner: AccountTeam = Depends(require_owner),
    session: AsyncSession = Depends(transactional_session_helper),
) -> JSONResponse:
    removed = await remove.remove(session=session, input=remove.Input(account_id=str(account_id)), team_id=team_id)
    return JSONResponse(status_code=200, content=removed)


async def post_rotate(
    team_id: UUID,
    body: rotate.Input,
    _owner: AccountTeam = Depends(require_owner),
    session: AsyncSession = Depends(transactional_session_helper),
) -> JSONResponse:
    rotated = await rotate.rotate(session=session, input=body, team_id=team_id)
    return JSONResponse(status_code=200, content=rotated)
