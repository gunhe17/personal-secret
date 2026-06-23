import json
from uuid import UUID

from sqlalchemy import text

from personal_secret.api.core.behavior import Action
from personal_secret.api.infrastructure.database.postgresql.session import postgresql_transactional_session


class Event(Action):

    @staticmethod
    async def dispatch_event(
        event_group_id: UUID,
        account_id: UUID | None = None,
        team_id: UUID | None = None,
    ):
        payload = {"group_id": str(event_group_id)}
        if account_id is not None:
            payload["account_id"] = str(account_id)
        if team_id is not None:
            payload["team_id"] = str(team_id)

        async with postgresql_transactional_session() as session:
            await session.execute(
                text("SELECT pg_notify('event_group', :payload)"),
                {
                    "payload": json.dumps(payload),
                },
            )
