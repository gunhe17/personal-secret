from __future__ import annotations

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from personal_secret.api.config import get_postgres_config
from personal_secret.api.core.model import Base
from personal_secret.api.infrastructure.database.common.client import Database
from personal_secret.api.infrastructure.database.postgresql.rls import apply_rls

import personal_secret.api.domain  # noqa: F401


# #
# client

class Postgres(Database):
    _tables_created = False

    def __init__(self, url: str):
        self.database_url = url
        self.engine: AsyncEngine = create_async_engine(
            self.database_url,
            echo=False,
        )
        self.SessionLocal = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            autoflush=False,
            expire_on_commit=False,
            autocommit=False,
        )

    # #
    # ddl

    def _create_tables(self, conn):
        inspector = inspect(conn)
        existing = set(inspector.get_table_names())
        model_tables = set(Base.metadata.tables.keys())
        missing = model_tables - existing
        if missing:
            Base.metadata.create_all(conn)
            for t in missing:
                print(f"  + {t}")
        # RLS 정책은 모델 밖 DDL — 매번 idempotent 재적용
        apply_rls(conn)
        return len(missing)

    async def create_tables_once_in_process(self):
        if Postgres._tables_created:
            return
        print("Database: create_tables called")
        async with self.engine.begin() as conn:
            created = await conn.run_sync(self._create_tables)
        Postgres._tables_created = True
        print(f"Database: create_tables worked ({created} tables created)")

    async def delete_tables(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    async def close(self):
        await self.engine.dispose()


# #
# client

db_client = Postgres(get_postgres_config().database_url())


# #
# cli

if __name__ == "__main__":
    import asyncio

    async def main():
        await db_client.create_tables_once_in_process()

    asyncio.run(main())
