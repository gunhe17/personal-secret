from __future__ import annotations

from uuid import UUID
from dataclasses import dataclass, replace

from personal_secret.api.core.entity import Entity
from personal_secret.api.core.validate import typecheck

from personal_secret.api.domain.secret.domain import Domain
from personal_secret.api.domain.secret.service import Service
from personal_secret.api.domain.secret.project import Project
from personal_secret.api.domain.secret.field import Field
from personal_secret.api.domain.secret.ciphertext import Ciphertext


@dataclass(frozen=True, kw_only=True)
class Secret(Entity):
    team_id: UUID
    domain: Domain
    service: Service
    project: Project
    field: Field
    value: Ciphertext

    # #
    # factory

    @classmethod
    @typecheck
    def new(
        cls,
        *,
        team_id: UUID,
        domain: Domain,
        service: Service,
        project: Project,
        field: Field,
        value: Ciphertext,
    ) -> "Secret":
        secret = cls(
            team_id=team_id,
            domain=domain,
            service=service,
            project=project,
            field=field,
            value=value,
            by_factory=True,
        )
        return secret

    # #
    # update

    def with_value(self, value: Ciphertext) -> "Secret":
        return replace(self, value=value, by_factory=True)

    # #
    # query

    def to_dict(self):
        # value(암호문)는 to_dict 에 안 실음
        return {
            "id": str(self.id),
            "team_id": str(self.team_id),
            "domain": self.domain.to_str(),
            "service": self.service.to_str(),
            "project": self.project.to_str(),
            "field": self.field.to_str(),
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
            "updated_at": (
                self.updated_at.isoformat() if self.updated_at else None
            ),
            "deleted_at": (
                self.deleted_at.isoformat() if self.deleted_at else None
            ),
        }

    def to_model(self):
        return {
            "id": self.id,
            "team_id": self.team_id,
            "domain": self.domain.to_str(),
            "service": self.service.to_str(),
            "project": self.project.to_str(),
            "field": self.field.to_str(),
            "value": self.value.to_str(),
        }
