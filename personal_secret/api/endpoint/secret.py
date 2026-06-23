from __future__ import annotations

from uuid import UUID

from fastapi import Depends
from pydantic import BaseModel
from starlette.responses import JSONResponse

from personal_secret.api.behavior import use_postgresql_session_with_authenticated_team_and_event
from personal_secret.api.behavior import use_postgresql_context_with_authenticated_team_and_event

from personal_secret.api.usecase import secret_create
from personal_secret.api.usecase import secret_reveal
from personal_secret.api.usecase import secret_search
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
    *,
    session=Depends(use_postgresql_session_with_authenticated_team_and_event),
    context=Depends(use_postgresql_context_with_authenticated_team_and_event),
) -> JSONResponse:
    created = await secret_create.create(
        session=session,
        event_group_id=context.event_group_id,
        input=body,
        team_id=team_id,
        account_id=context.account_id,
    )
    return JSONResponse(status_code=200, content=created.to_dict())


async def get_list(
    team_id: UUID,
    domain: str | None = None,
    service: str | None = None,
    project: str | None = None,
    *,
    session=Depends(use_postgresql_session_with_authenticated_team_and_event),
    context=Depends(use_postgresql_context_with_authenticated_team_and_event),
) -> JSONResponse:
    listed = await secret_search.search(
        session=session,
        event_group_id=context.event_group_id,
        input=secret_search.Input(domain=domain, service=service, project=project),
        team_id=team_id,
        account_id=context.account_id,
    )
    return JSONResponse(status_code=200, content=listed.to_dict())


async def get_reveal(
    team_id: UUID,
    secret_id: UUID,
    *,
    session=Depends(use_postgresql_session_with_authenticated_team_and_event),
    context=Depends(use_postgresql_context_with_authenticated_team_and_event),
) -> JSONResponse:
    revealed = await secret_reveal.reveal(
        session=session,
        event_group_id=context.event_group_id,
        input=secret_reveal.Input(id=str(secret_id)),
        team_id=team_id,
        account_id=context.account_id,
    )
    return JSONResponse(status_code=200, content=revealed.to_dict())


async def put_update(
    team_id: UUID,
    secret_id: UUID,
    body: UpdateBody,
    *,
    session=Depends(use_postgresql_session_with_authenticated_team_and_event),
    context=Depends(use_postgresql_context_with_authenticated_team_and_event),
) -> JSONResponse:
    updated = await secret_update.update(
        session=session,
        event_group_id=context.event_group_id,
        input=secret_update.Input(id=str(secret_id), value=body.value),
        team_id=team_id,
        account_id=context.account_id,
    )
    return JSONResponse(status_code=200, content=updated.to_dict())


async def delete_secret(
    team_id: UUID,
    secret_id: UUID,
    *,
    session=Depends(use_postgresql_session_with_authenticated_team_and_event),
    context=Depends(use_postgresql_context_with_authenticated_team_and_event),
) -> JSONResponse:
    removed = await secret_delete.delete(
        session=session,
        event_group_id=context.event_group_id,
        input=secret_delete.Input(id=str(secret_id)),
        team_id=team_id,
        account_id=context.account_id,
    )
    return JSONResponse(status_code=200, content=removed.to_dict())
