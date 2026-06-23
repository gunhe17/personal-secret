from __future__ import annotations

import base64
import uuid
from datetime import datetime, timedelta, timezone

from personal_secret.api.domain.secret.secret import Secret
from personal_secret.api.domain.secret.domain import Domain
from personal_secret.api.domain.secret.service import Service
from personal_secret.api.domain.secret.project import Project
from personal_secret.api.domain.secret.field import Field
from personal_secret.api.domain.secret.ciphertext import Ciphertext

from personal_secret.api.domain.setting.setting import Setting
from personal_secret.api.domain.setting.key import Key
from personal_secret.api.domain.setting.value import Value

from personal_secret.api.domain.account.account import Account
from personal_secret.api.domain.account.email import Email
from personal_secret.api.domain.account.personal_lock import PersonalLock
from personal_secret.api.domain.account.personal_locked_key import PersonalLockedKey
from personal_secret.api.domain.account.personal_unlock_salt import PersonalUnlockSalt
from personal_secret.api.domain.account.login_salt import LoginSalt
from personal_secret.api.domain.account.login_verifier import LoginVerifier

from personal_secret.api.domain.team.team import Team
from personal_secret.api.domain.team.team_name import TeamName

from personal_secret.api.domain.team_access.team_access import TeamAccess
from personal_secret.api.domain.team_access.role import Role
from personal_secret.api.domain.team_access.team_locked_key import TeamLockedKey

from personal_secret.api.domain.account_token.account_token import AccountToken
from personal_secret.api.domain.account_token.fingerprint import Fingerprint
from personal_secret.api.domain.account_token.expires_at import ExpiresAt

from personal_secret.api.infrastructure.hash.argon2.client import argon2
from personal_secret.api.infrastructure.hash.sha256.client import sha256


DEFAULT_TEAM_ID = uuid.UUID("00000000-0000-0000-0000-000000000007")


def make_secret(
    *,
    team_id: uuid.UUID = DEFAULT_TEAM_ID,
    domain: str = "ssh",
    service: str = "github",
    project: str = "prod",
    field: str = "password",
    value: bytes = b"blob",
) -> Secret:
    return Secret.new(
        team_id=team_id,
        domain=Domain.from_str(domain),
        service=Service.from_str(service),
        project=Project.from_str(project),
        field=Field.from_str(field),
        value=Ciphertext.from_bytes(value),
    )


def make_setting(*, key: str = "app.theme", value=("dark")) -> Setting:
    return Setting.new(key=Key.from_str(key), value=Value.from_json(value))


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def make_account(*, email: str = "me@example.com", login_proof: str = "proof-xyz") -> Account:
    return Account.new(
        email=Email.from_str(email),
        personal_lock=PersonalLock.from_str(_b64(b"public-key")),
        personal_locked_key=PersonalLockedKey.from_str(_b64(b"locked-private-key")),
        personal_unlock_salt=PersonalUnlockSalt.from_str(_b64(b"unlock-salt")),
        login_salt=LoginSalt.from_str(_b64(b"login-salt")),
        login_verifier=LoginVerifier.from_str(argon2.hash(value=login_proof)),
    )


def make_token(*, account_id, raw: str = "raw-token", expires_at: datetime | None = None) -> AccountToken:
    return AccountToken.new(
        account_id=account_id,
        fingerprint=Fingerprint.from_str(sha256.hash(value=raw)),
        expires_at=ExpiresAt.from_datetime(
            expires_at if expires_at is not None else datetime.now(timezone.utc) + timedelta(hours=1)
        ),
    )


def make_team(*, name: str = "acme") -> Team:
    return Team.new(name=TeamName.from_str(name))


def make_account_team(*, account_id, team_id, role: str = "owner") -> TeamAccess:
    return TeamAccess.new(
        account_id=account_id,
        team_id=team_id,
        role=Role.from_str(role),
        team_locked_key=TeamLockedKey.from_str(_b64(b"team-locked-key")),
    )
