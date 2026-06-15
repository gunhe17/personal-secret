from __future__ import annotations

from uuid import UUID

from fastapi import Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from personal_secret.api.infrastructure.postgresql.session import transactional_session_helper

from personal_secret.api.endpoint.auth import require_member

from personal_secret.api.usecase.secret import create
from personal_secret.api.usecase.secret import reveal
from personal_secret.api.usecase.secret import list as list_usecase
from personal_secret.api.usecase.secret import update
from personal_secret.api.usecase.secret import delete


# #
# body

class UpdateBody(BaseModel):
    value: str


# #
# command

async def post_create(
    team_id: UUID,
    body: create.Input,
    _membership=Depends(require_member),
    session: AsyncSession = Depends(transactional_session_helper),
) -> JSONResponse:
    created = await create.create(session=session, input=body, team_id=team_id)
    return JSONResponse(status_code=200, content=created)


async def get_list(
    team_id: UUID,
    domain: str | None = None,
    service: str | None = None,
    project: str | None = None,
    _membership=Depends(require_member),
    session: AsyncSession = Depends(transactional_session_helper),
) -> JSONResponse:
    rows = await list_usecase.list_secrets(
        session=session,
        input=list_usecase.Input(domain=domain, service=service, project=project),
        team_id=team_id,
    )
    return JSONResponse(status_code=200, content={"data": rows})


async def get_reveal(
    team_id: UUID,
    secret_id: UUID,
    _membership=Depends(require_member),
    session: AsyncSession = Depends(transactional_session_helper),
) -> JSONResponse:
    revealed = await reveal.reveal(session=session, input=reveal.Input(id=str(secret_id)), team_id=team_id)
    return JSONResponse(status_code=200, content=revealed)


async def put_update(
    team_id: UUID,
    secret_id: UUID,
    body: UpdateBody,
    _membership=Depends(require_member),
    session: AsyncSession = Depends(transactional_session_helper),
) -> JSONResponse:
    updated = await update.update(
        session=session,
        input=update.Input(id=str(secret_id), value=body.value),
        team_id=team_id,
    )
    return JSONResponse(status_code=200, content=updated)


async def delete_secret(
    team_id: UUID,
    secret_id: UUID,
    _membership=Depends(require_member),
    session: AsyncSession = Depends(transactional_session_helper),
) -> JSONResponse:
    removed = await delete.delete(session=session, input=delete.Input(id=str(secret_id)), team_id=team_id)
    return JSONResponse(status_code=200, content=removed)
