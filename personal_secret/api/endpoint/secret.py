from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from personal_secret.api.infrastructure.postgresql.session import transactional_session_helper

from personal_secret.api.usecase.secret import create


# #
# command

async def post_create(
    body: create.Input,
    session: AsyncSession = Depends(transactional_session_helper),
) -> JSONResponse:
    created = await create.create(session=session, input=body)
    return JSONResponse(status_code=200, content=created)
