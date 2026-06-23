from __future__ import annotations

import json
from uuid import UUID

from personal_secret.api.behavior import use_postgresql_with_action

from personal_secret.api.usecase import event_dispatch


# #
# subscribe

async def on_event_group(raw: str) -> None:
    # parse
    payload = json.loads(raw)
    event_group_id = UUID(payload["group_id"])
    account_id = UUID(payload["account_id"]) if "account_id" in payload else None
    team_id = UUID(payload["team_id"]) if "team_id" in payload else None

    # action
    async with use_postgresql_with_action(
        id=event_group_id,
        account_id=account_id,
        team_id=team_id,
    ) as scope:
        if scope is None:
            return
        
        await event_dispatch.dispatch(
            session=scope.session,
            id=event_group_id,
        )