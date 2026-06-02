from __future__ import annotations

import argparse
import asyncio
import getpass

from pydantic import BaseModel

from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.common.exception import AlreadyInitializedError
from personal_secret.api.domain.vault.vault import Vault
from personal_secret.api.domain.vault.salt import Salt
from personal_secret.api.domain.vault.wrapped_dek import WrappedDek
from personal_secret.api.domain.vault.vault_repository import VaultRepository
from personal_secret.api.domain.vault.vault_event import VaultEvent

from personal_secret.api.domain.event.event_repository import EventRepository

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
async def init(*, session, input: Input) -> dict:
    # guard — 단일 행 집합체, 한 번만 초기화
    if await VaultRepository.get(session=session) is not None:
        raise AlreadyInitializedError()

    # 봉투 — salt·DEK 랜덤, 비밀번호로 KEK 파생, DEK를 KEK로 봉인
    salt = crypto.generate_salt()
    kek = crypto.derive_kek(password=input.password, salt=salt)
    dek = crypto.generate_dek()
    wrapped_dek = crypto.encrypt(key=kek, plaintext=dek)

    vault = Vault.new(
        salt=Salt.from_bytes(bytes=salt),
        wrapped_dek=WrappedDek.from_bytes(bytes=wrapped_dek),
    )

    # event(초기화) → 저장 + 응답 조합
    event, entity = VaultEvent.initialized(vault=await VaultRepository.add(session=session, entity=vault))
    session_cache.unlock(dek=dek)  # init은 unlocked 상태로 끝남
    return {
        "data": entity.to_dict(),
        "event": [e.to_dict() for e in (await EventRepository.emit(session=session, events=[event]))],
    }


# #
# cli

def _parse_args() -> argparse.Namespace:
    return argparse.ArgumentParser().parse_args()

async def _main():
    _parse_args()
    async with transactional_session(db_client.SessionLocal) as session:
        print(await init(
            session=session,
            input=Input(password=getpass.getpass("new master password: ")),
        ))

if __name__ == "__main__":
    asyncio.run(_main())
