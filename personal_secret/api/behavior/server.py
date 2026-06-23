from __future__ import annotations

from uuid import UUID
from typing import AsyncIterator
from dataclasses import dataclass

from fastapi import Header, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from personal_secret.api.behavior.context.access import AccountContext
from personal_secret.api.behavior.context.access import TeamAccessContext
from personal_secret.api.behavior.context.access import OwnerAccessContext
from personal_secret.api.behavior.context.event import EventGroupContext
from personal_secret.api.behavior.action.event import Event
from personal_secret.api.behavior.action.tenant import Tenant

from personal_secret.api.infrastructure.database.postgresql.session import postgresql_transactional_session

# scope
@dataclass(frozen=True)
class Scope:
    # db
    session: AsyncSession
    # account
    account_id: UUID | None = None
    team_id: UUID | None = None
    # event
    event_group_id: UUID | None = None


# #
# dependency

async def use_postgresql_with_event() -> AsyncIterator[Scope]:
    async with postgresql_transactional_session() as session:
        # #
        # Before

        event_group_context = await EventGroupContext.setup()

        yield Scope(
            session=session,
            account_id=None,
            team_id=None,
            event_group_id=event_group_context.event_group_id,
        )

        # Before commit

    # #
    # After

    await Event.dispatch_event(event_group_id=event_group_context.event_group_id)

def use_postgresql_session_with_event(scope: Scope = Depends(use_postgresql_with_event)) -> AsyncSession:
    return scope.session

def use_postgresql_context_with_event(scope: Scope = Depends(use_postgresql_with_event)) -> Scope:
    return scope


async def use_postgresql_with_authenticated_account_and_event(
    authorization: str | None = Header(default=None),
) -> AsyncIterator[Scope]:
    async with postgresql_transactional_session() as session:
        # #
        # Before

        account_context = await AccountContext.setup(session=session, authorization=authorization)

        event_group_context = await EventGroupContext.setup()

        yield Scope(
            session=session,
            account_id=account_context.account_id,
            team_id=None,
            event_group_id=event_group_context.event_group_id,
        )

        # Before commit

    # #
    # After

    await Event.dispatch_event(
        event_group_id=event_group_context.event_group_id,
        account_id=account_context.account_id,
    )

def use_postgresql_session_with_authenticated_account_and_event(scope: Scope = Depends(use_postgresql_with_authenticated_account_and_event)) -> AsyncSession:
    return scope.session

def use_postgresql_context_with_authenticated_account_and_event(scope: Scope = Depends(use_postgresql_with_authenticated_account_and_event)) -> Scope:
    return scope


async def use_postgresql_with_authenticated_team_and_event(
    team_id: UUID,
    authorization: str | None = Header(default=None),
) -> AsyncIterator[Scope]:
    async with postgresql_transactional_session() as session:
        # #
        # Before

        account_context = await AccountContext.setup(session=session, authorization=authorization)

        team_access_context = await TeamAccessContext.setup(
            team_id=team_id,
            session=session,
            account=account_context,
        )

        await Tenant.set_tenant_scope(session=session, team_id=team_id)

        event_group_context = await EventGroupContext.setup()

        yield Scope(
            session=session,
            account_id=team_access_context.account_id,
            team_id=team_access_context.team_id,
            event_group_id=event_group_context.event_group_id,
        )

        # Before commit

    # #
    # After

    await Event.dispatch_event(
        event_group_id=event_group_context.event_group_id,
        account_id=team_access_context.account_id,
        team_id=team_access_context.team_id,
    )

def use_postgresql_session_with_authenticated_team_and_event(scope: Scope = Depends(use_postgresql_with_authenticated_team_and_event)) -> AsyncSession:
    return scope.session

def use_postgresql_context_with_authenticated_team_and_event(scope: Scope = Depends(use_postgresql_with_authenticated_team_and_event)) -> Scope:
    return scope


async def use_postgresql_with_authenticated_owner_and_event(
    team_id: UUID,
    authorization: str | None = Header(default=None),
) -> AsyncIterator[Scope]:
    async with postgresql_transactional_session() as session:
        # #
        # Before

        account_context = await AccountContext.setup(session=session, authorization=authorization)

        owner_access_context = await OwnerAccessContext.setup(
            team_id=team_id,
            session=session,
            account=account_context,
        )

        await Tenant.set_tenant_scope(session=session, team_id=team_id)

        event_group_context = await EventGroupContext.setup()

        yield Scope(
            session=session,
            account_id=owner_access_context.account_id,
            team_id=owner_access_context.team_id,
            event_group_id=event_group_context.event_group_id,
        )

        # Before commit

    # #
    # After

    await Event.dispatch_event(
        event_group_id=event_group_context.event_group_id,
        account_id=owner_access_context.account_id,
        team_id=owner_access_context.team_id,
    )

def use_postgresql_session_with_authenticated_owner_and_event(scope: Scope = Depends(use_postgresql_with_authenticated_owner_and_event)) -> AsyncSession:
    return scope.session

def use_postgresql_context_with_authenticated_owner_and_event(scope: Scope = Depends(use_postgresql_with_authenticated_owner_and_event)) -> Scope:
    return scope
