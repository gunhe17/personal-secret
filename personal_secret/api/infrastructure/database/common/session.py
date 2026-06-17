from __future__ import annotations

from contextlib import asynccontextmanager

from sqlalchemy.exc import SQLAlchemyError

from personal_secret.api.infrastructure.database.common.exception import DatabaseError


# #
# transactional

@asynccontextmanager
async def transactional_session(session_factory):
    session = session_factory()
    try:
        yield session
        await session.commit()

    except SQLAlchemyError as exc:
        await session.rollback()
        raise DatabaseError(operation="", reason=str(exc))

    except Exception:
        await session.rollback()
        raise

    finally:
        await session.close()


# #
# plain

@asynccontextmanager
async def plain_session(session_factory):
    session = session_factory()
    try:
        yield session
    finally:
        await session.close()
