from __future__ import annotations

from uuid import UUID

from fastapi import Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from personal_secret.api.infrastructure.postgresql.session import transactional_session_helper

from personal_secret.api.endpoint.auth import require_member

from personal_secret.api.usecase import secret_create
from personal_secret.api.usecase import secret_reveal
from personal_secret.api.usecase import secret_list
from personal_secret.api.usecase import secret_update
from personal_secret.api.usecase import secret_delete


# #
# body

class UpdateBody(BaseModel):
    value: str


# #
# command

async def post_create(
    team_id: UUID,
    body: secret_create.Input,
    membership=Depends(require_member),
    session: AsyncSession = Depends(transactional_session_helper),
) -> JSONResponse:
    created = await secret_create.create(session=session, input=body, team_id=team_id, actor_id=membership.account_id)
    return JSONResponse(status_code=200, content=created)


async def get_list(
    team_id: UUID,
    domain: str | None = None,
    service: str | None = None,
    project: str | None = None,
    membership=Depends(require_member),
    session: AsyncSession = Depends(transactional_session_helper),
) -> JSONResponse:
    listed = await secret_list.list_secrets(
        session=session,
        input=secret_list.Input(domain=domain, service=service, project=project),
        team_id=team_id,
        actor_id=membership.account_id,
    )
    return JSONResponse(status_code=200, content=listed)


async def get_reveal(
    team_id: UUID,
    secret_id: UUID,
    membership=Depends(require_member),
    session: AsyncSession = Depends(transactional_session_helper),
) -> JSONResponse:
    revealed = await secret_reveal.reveal(session=session, input=secret_reveal.Input(id=str(secret_id)), team_id=team_id, actor_id=membership.account_id)
    return JSONResponse(status_code=200, content=revealed)


async def put_update(
    team_id: UUID,
    secret_id: UUID,
    body: UpdateBody,
    membership=Depends(require_member),
    session: AsyncSession = Depends(transactional_session_helper),
) -> JSONResponse:
    updated = await secret_update.update(
        session=session,
        input=secret_update.Input(id=str(secret_id), value=body.value),
        team_id=team_id,
        actor_id=membership.account_id,
    )
    return JSONResponse(status_code=200, content=updated)


async def delete_secret(
    team_id: UUID,
    secret_id: UUID,
    membership=Depends(require_member),
    session: AsyncSession = Depends(transactional_session_helper),
) -> JSONResponse:
    removed = await secret_delete.delete(session=session, input=secret_delete.Input(id=str(secret_id)), team_id=team_id, actor_id=membership.account_id)
    return JSONResponse(status_code=200, content=removed)
