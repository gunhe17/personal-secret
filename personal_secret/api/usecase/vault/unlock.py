from __future__ import annotations

import argparse
import asyncio
import getpass

from pydantic import BaseModel

from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.common.exception import InvalidMasterPasswordError, NotInitializedError
from personal_secret.api.domain.vault.vault_repository import VaultRepository

from personal_secret.api.infrastructure.crypto.client import crypto
from personal_secret.api.infrastructure.crypto.cache import session_cache
from personal_secret.api.infrastructure.postgresql.client import db_client
from personal_secret.api.infrastructure.postgresql.session import transactional_session


# #
# input

class Input(BaseModel):
    password: str


# #
# usecase

@typecheck
async def unlock(*, session, input: Input) -> dict:
    # load
    vault = await VaultRepository.get(session=session)
    if vault is None:
        raise NotInitializedError()

    # KEK 파생 → DEK 봉인 해제 (틀린 비밀번호면 복호화 실패 = 인증 실패)
    kek = crypto.derive_kek(password=input.password, salt=vault.salt.to_bytes())
    try:
        dek = crypto.decrypt(key=kek, data=vault.wrapped_dek.to_bytes())
    except Exception:
        raise InvalidMasterPasswordError()

    # 세션에 DEK 적재 (DB 변경 없음 → 이벤트 없음)
    session_cache.unlock(dek=dek)
    return {"data": {"unlocked": True}}


# #
# cli

def _parse_args() -> argparse.Namespace:
    return argparse.ArgumentParser().parse_args()

async def _main():
    _parse_args()
    async with transactional_session(db_client.SessionLocal) as session:
        print(await unlock(
            session=session,
            input=Input(password=getpass.getpass("master password: ")),
        ))

if __name__ == "__main__":
    asyncio.run(_main())
