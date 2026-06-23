from __future__ import annotations

from personal_secret.api.config import get_worker_config

from personal_secret.api.infrastructure.database.postgresql.notification import notification_connection

from personal_secret.api.worker.common.exception import NoWorkRegisteredError
from personal_secret.api.worker.lifecycle import Lifecycle
from personal_secret.api.worker.work import Work
from personal_secret.api.worker.pool import Pool


class Worker:
    def __init__(self, name: str, concurrency: int = 16):
        self._name = name
        self._concurrency = concurrency

        self._works: list[Work] = []

    def work(self, work: Work):
        self._works.append(work)

    async def run(self):
        if not self._works:
            raise NoWorkRegisteredError(name=self._name)

        pool = Pool(self._concurrency)
        lifecycle = Lifecycle()

        connection = await notification_connection()
        for work in self._works:
            await work.register(connection=connection, pool=pool)

        await lifecycle.wait()

        await connection.close()
        await pool.wait()


# #
# factory

def personal_secret_worker():
    return Worker(
        name="personal-secret-worker",
        concurrency=get_worker_config().CONCURRENCY,
    )
