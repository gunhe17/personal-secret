from __future__ import annotations

import asyncio
import signal

from personal_secret.api.config import get_outbox_config

from personal_secret.api.usecase.outbox.drain import drain, Input

from personal_secret.api.infrastructure.postgresql.client import db_client
from personal_secret.api.infrastructure.postgresql.session import transactional_session


# #
# worker

async def _run() -> None:
    config = get_outbox_config()

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)

    print(f"outbox worker: started (interval={config.OUTBOX_POLL_INTERVAL_SEC}s, batch={config.OUTBOX_BATCH_SIZE})")
    while not stop.is_set():
        # 한 배치 = 한 트랜잭션 (claim + mark 원자적, 잠금은 커밋까지)
        async with transactional_session(db_client.SessionLocal) as session:
            result = await drain(session=session, input=Input())

        if result["succeeded"] or result["failed"]:
            print(f"outbox worker: claimed={result['claimed']} succeeded={result['succeeded']} failed={result['failed']}")

        if result["claimed"] == 0:
            try:
                await asyncio.wait_for(stop.wait(), timeout=config.OUTBOX_POLL_INTERVAL_SEC)
            except asyncio.TimeoutError:
                pass

    print("outbox worker: stopped")


# #
# run

if __name__ == "__main__":
    asyncio.run(_run())
