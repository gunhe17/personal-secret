from __future__ import annotations

from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from personal_secret.api.infrastructure.database.postgresql.session import transactional_session_helper

from personal_secret.api.domain.account_team.account_team import AccountTeam

from personal_secret.api.endpoint.auth import require_auth
from personal_secret.api.endpoint.auth import require_member
from personal_secret.api.endpoint.auth import require_owner

from personal_secret.api.usecase import team_create
from personal_secret.api.usecase import team_get_only_key
from personal_secret.api.usecase import team_invite
from personal_secret.api.usecase import team_remove
from personal_secret.api.usecase import team_rotate


# #
# command

async def post_create(
    body: team_create.Input,
    account_id: UUID = Depends(require_auth),
    session: AsyncSession = Depends(transactional_session_helper),
) -> JSONResponse:
    created = await team_create.create(session=session, input=body, account_id=account_id)
    return JSONResponse(status_code=200, content=created.to_dict())


async def get_key(
    team_id: UUID,
    membership: AccountTeam = Depends(require_member),
    session: AsyncSession = Depends(transactional_session_helper),
) -> JSONResponse:
    keyed = await team_get_only_key.get_only_key(session=session, input=team_get_only_key.Input(), team_id=team_id, actor_id=membership.account_id)
    return JSONResponse(status_code=200, content=keyed.to_dict())


# #
# member management

async def post_invite(
    team_id: UUID,
    body: team_invite.Input,
    owner: AccountTeam = Depends(require_owner),
    session: AsyncSession = Depends(transactional_session_helper),
) -> JSONResponse:
    invited = await team_invite.invite(session=session, input=body, team_id=team_id, actor_id=owner.account_id)
    return JSONResponse(status_code=200, content=invited.to_dict())


async def delete_member(
    team_id: UUID,
    account_id: UUID,
    owner: AccountTeam = Depends(require_owner),
    session: AsyncSession = Depends(transactional_session_helper),
) -> JSONResponse:
    removed = await team_remove.remove(session=session, input=team_remove.Input(account_id=str(account_id)), team_id=team_id, actor_id=owner.account_id)
    return JSONResponse(status_code=200, content=removed.to_dict())


async def post_rotate(
    team_id: UUID,
    body: team_rotate.Input,
    owner: AccountTeam = Depends(require_owner),
    session: AsyncSession = Depends(transactional_session_helper),
) -> JSONResponse:
    rotated = await team_rotate.rotate(session=session, input=body, team_id=team_id, actor_id=owner.account_id)
    return JSONResponse(status_code=200, content=rotated.to_dict())
