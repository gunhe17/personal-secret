from __future__ import annotations

from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from personal_secret.api.infrastructure.postgresql.session import transactional_session_helper

from personal_secret.api.endpoint.auth import require_auth

from personal_secret.api.usecase import account_get_only_public_key


# #
# command (인증 필요 — 공개키 열람으로 계정 enumeration 방지)

async def get_public_key(
    email: str,
    account_id: UUID = Depends(require_auth),
    session: AsyncSession = Depends(transactional_session_helper),
) -> JSONResponse:
    found = await account_get_only_public_key.get_only_public_key(session=session, input=account_get_only_public_key.Input(email=email), actor_id=account_id)
    return JSONResponse(status_code=200, content=found)
