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

    atomics = await EventRepository.filter_by_event_id(
        session=session,
        event_id=id,
    )

    # route
    commands = EVENT_COMMANDS.get(
        event.name.to_str(),
        [],
    )

    # run
    for command in commands:
        await command.run(
            session=session,
            input=command.Input.from_events(atomics),
        )


# #
# command

EVENT_COMMANDS = {
    "team_invite": [
        notify_invited_member,
    ],
}
