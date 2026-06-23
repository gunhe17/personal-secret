from __future__ import annotations

from fastapi import Depends
from starlette.responses import JSONResponse

from personal_secret.api.behavior import use_postgresql_session_with_event
from personal_secret.api.behavior import use_postgresql_context_with_event

from personal_secret.api.usecase import auth_register
from personal_secret.api.usecase import auth_login
from personal_secret.api.usecase import auth_get_only_salts


# #
# command

async def post_register(
    body: auth_register.Input,
    *,
    session=Depends(use_postgresql_session_with_event),
    context=Depends(use_postgresql_context_with_event),
) -> JSONResponse:
    registered = await auth_register.register(
        session=session,
        event_group_id=context.event_group_id,
        input=body,
    )
    return JSONResponse(status_code=200, content=registered.to_dict())


async def get_salts(
    email: str,
    *,
    session=Depends(use_postgresql_session_with_event),
    context=Depends(use_postgresql_context_with_event),
) -> JSONResponse:
    found = await auth_get_only_salts.get_only_salts(
        session=session,
        event_group_id=context.event_group_id,
        input=auth_get_only_salts.Input(email=email),
    )
    return JSONResponse(status_code=200, content=found.to_dict())


async def post_login(
    body: auth_login.Input,
    *,
    session=Depends(use_postgresql_session_with_event),
    context=Depends(use_postgresql_context_with_event),
) -> JSONResponse:
    logged_in = await auth_login.login(
        session=session,
        event_group_id=context.event_group_id,
        input=body,
    )
    return JSONResponse(status_code=200, content=logged_in.to_dict())
