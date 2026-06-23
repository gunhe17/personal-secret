from __future__ import annotations

import asyncio

from personal_secret.api.worker.worker import personal_secret_worker
from personal_secret.api.worker.work import Work

from personal_secret.api.endpoint.internal import event


# #
# worker

worker = personal_secret_worker()

# work
worker.work(
    Work(
        channel="event_group",
        handler=event.on_event_group,
    )
)


# #
# run

if __name__ == "__main__":
    asyncio.run(worker.run())
