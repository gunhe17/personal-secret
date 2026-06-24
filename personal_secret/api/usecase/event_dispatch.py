from __future__ import annotations

from uuid import UUID

from personal_secret.api.domain.event.event.event_repository import EventRepository

from personal_secret.api.usecase import notify_invited_member


# #
# dispatch

async def dispatch(*, session, id: UUID) -> None:
    # find
    event = await EventRepository.find_by_id(session=session, id=id)
    if event is None:
        return

    # route
    commands = EVENT_COMMANDS.get(
        event.name.to_str(),
        [],
    )
    if not commands:
        return

    # load
    atomics = await EventRepository.filter_by_event_id(
        session=session,
        event_id=id,
    )

    # fan-out
    ledger = event.attempts
    for command in commands:
        reaction = command.__name__.rsplit(".", 1)[-1]
        for atomic in atomics:
            if ledger.is_done(reaction=reaction, atomic_id=atomic.id):
                continue
            try:
                await command.run(
                    session=session,
                    input=command.Input.from_event(atomic),
                )
                ledger = ledger.record_success(reaction=reaction, atomic_id=atomic.id)
            except Exception as exc:
                ledger = ledger.record_failure(reaction=reaction, atomic_id=atomic.id, error=str(exc))

    # persist ledger
    await EventRepository.update(
        session=session,
        entity=event.with_attempts(ledger),
    )


# #
# command

EVENT_COMMANDS = {
    "team_invite": [
        notify_invited_member,
    ],
}
