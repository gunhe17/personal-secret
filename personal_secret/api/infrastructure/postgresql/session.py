from __future__ import annotations

from contextlib import asynccontextmanager

from sqlalchemy.exc import SQLAlchemyError

from personal_secret.api.config import TestPostgresConfig
from personal_secret.api.infrastructure.postgresql.client import Postgres, db_client
from personal_secret.api.infrastructure.common.exception import DatabaseError


# #
# session

@asynccontextmanager
async def transactional_session(session_factory):
    session = session_factory()
    try:
        yield session
        await session.commit()

    except SQLAlchemyError as exc:
        await session.rollback()
        raise DatabaseError(operation="transaction", reason=str(exc))
    
    except Exception:
        await session.rollback()
        raise
    
    finally:
        await session.close()


# #
# fastapi dependency

async def transactional_session_helper():
    async with transactional_session(db_client.SessionLocal) as session:
        yield session


# #
# test

@asynccontextmanager
async def transactional_test_session_helper():
    Postgres._tables_created = False
    test_client = Postgres(TestPostgresConfig().database_url())
    await test_client.create_tables_once_in_process()
    try:
        async with transactional_session(test_client.SessionLocal) as session:
            yield session
    finally:
        await test_client.delete_tables()
        await test_client.close()