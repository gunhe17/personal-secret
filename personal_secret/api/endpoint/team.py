from __future__ import annotations

from uuid import UUID

from fastapi import Depends
from starlette.responses import JSONResponse

from personal_secret.api.behavior import use_postgresql_session_with_authenticated_account_and_event
from personal_secret.api.behavior import use_postgresql_context_with_authenticated_account_and_event
from personal_secret.api.behavior import use_postgresql_session_with_authenticated_team_and_event
from personal_secret.api.behavior import use_postgresql_context_with_authenticated_team_and_event
from personal_secret.api.behavior import use_postgresql_session_with_authenticated_owner_and_event
from personal_secret.api.behavior import use_postgresql_context_with_authenticated_owner_and_event

from personal_secret.api.usecase import team_create
from personal_secret.api.usecase import team_get_only_key
from personal_secret.api.usecase import team_invite
from personal_secret.api.usecase import team_remove
from personal_secret.api.usecase import team_rotate


# #
# command

async def post_create(
    body: team_create.Input,
    *,
    session=Depends(use_postgresql_session_with_authenticated_account_and_event),
    context=Depends(use_postgresql_context_with_authenticated_account_and_event),
) -> JSONResponse:
    created = await team_create.create(
        session=session,
        event_group_id=context.event_group_id,
        input=body,
        account_id=context.account_id,
    )
    return JSONResponse(status_code=200, content=created.to_dict())


async def get_key(
    team_id: UUID,
    *,
    session=Depends(use_postgresql_session_with_authenticated_team_and_event),
    context=Depends(use_postgresql_context_with_authenticated_team_and_event),
) -> JSONResponse:
    keyed = await team_get_only_key.get_only_key(
        session=session,
        event_group_id=context.event_group_id,
        input=team_get_only_key.Input(),
        team_id=team_id,
        account_id=context.account_id,
    )
    return JSONResponse(status_code=200, content=keyed.to_dict())


# #
# member management

async def post_invite(
    team_id: UUID,
    body: team_invite.Input,
    *,
    session=Depends(use_postgresql_session_with_authenticated_owner_and_event),
    context=Depends(use_postgresql_context_with_authenticated_owner_and_event),
) -> JSONResponse:
    invited = await team_invite.invite(
        session=session,
        event_group_id=context.event_group_id,
        input=body,
        team_id=team_id,
        account_id=context.account_id,
    )
    return JSONResponse(status_code=200, content=invited.to_dict())


async def delete_member(
    team_id: UUID,
    account_id: UUID,
    *,
    session=Depends(use_postgresql_session_with_authenticated_owner_and_event),
    context=Depends(use_postgresql_context_with_authenticated_owner_and_event),
) -> JSONResponse:
    removed = await team_remove.remove(
        session=session,
        event_group_id=context.event_group_id,
        input=team_remove.Input(account_id=str(account_id)),
        team_id=team_id,
        account_id=context.account_id,
    )
    return JSONResponse(status_code=200, content=removed.to_dict())


async def post_rotate(
    team_id: UUID,
    body: team_rotate.Input,
    *,
    session=Depends(use_postgresql_session_with_authenticated_owner_and_event),
    context=Depends(use_postgresql_context_with_authenticated_owner_and_event),
) -> JSONResponse:
    rotated = await team_rotate.rotate(
        session=session,
        event_group_id=context.event_group_id,
        input=body,
        team_id=team_id,
        account_id=context.account_id,
    )
    return JSONResponse(status_code=200, content=rotated.to_dict())
