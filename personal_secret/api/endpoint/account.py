from __future__ import annotations

from fastapi import Depends
from starlette.responses import JSONResponse

from personal_secret.api.behavior import (
    use_postgresql_session_with_authenticated_account_and_event,
    use_postgresql_context_with_authenticated_account_and_event
)

from personal_secret.api.usecase import account_get_only_public_key


# #
# command

async def get_public_key(
    email: str,
    *,
    session=Depends(use_postgresql_session_with_authenticated_account_and_event),
    context=Depends(use_postgresql_context_with_authenticated_account_and_event),
) -> JSONResponse:
    found = await account_get_only_public_key.get_only_public_key(
        session=session,
        event_group_id=context.event_group_id,
        input=account_get_only_public_key.Input(email=email),
        account_id=context.account_id,
    )
    return JSONResponse(status_code=200, content=found.to_dict())
