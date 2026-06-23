from __future__ import annotations

import os
from abc import ABC, abstractmethod
from enum import StrEnum


# #
# environment

class Env(StrEnum):
    DEVELOP = "develop"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


class AppConfig(ABC):
    @property
    @abstractmethod
    def APPLICATION_ENVIRONMENT(self) -> Env: ...


class DefaultAppConfig(AppConfig):
    @property
    def APPLICATION_ENVIRONMENT(self) -> Env:
        raw = os.environ.get("APP_ENV", Env.DEVELOP.value)
        return Env(raw)


def get_app_config() -> AppConfig:
    config = DefaultAppConfig()
    return config

def get_app_environment() -> Env:
    return get_app_config().APPLICATION_ENVIRONMENT

def is_develop() -> bool:
    return (
        DefaultAppConfig().APPLICATION_ENVIRONMENT == Env("develop")
    )

# #
# worker

class WorkerConfig(ABC):
    @property
    @abstractmethod
    def CONCURRENCY(self) -> int: ...


class DevelopWorkerConfig(WorkerConfig):
    @property
    def CONCURRENCY(self) -> int:
        return int(os.environ["DEVELOP_WORKER_CONCURRENCY"])


class ProductionWorkerConfig(WorkerConfig):
    @property
    def CONCURRENCY(self) -> int:
        return int(os.environ["PRODUCTION_WORKER_CONCURRENCY"])


def get_worker_config() -> WorkerConfig:
    env = get_app_config().APPLICATION_ENVIRONMENT
    if env == Env.DEVELOP:
        config = DevelopWorkerConfig()
    elif env == Env.PRODUCTION:
        config = ProductionWorkerConfig()
    else:
        raise NotImplementedError(f"worker config not implemented for env={env}")
    return config


# #
# email

class EmailConfig(ABC):
    @property
    @abstractmethod
    def SMTP_HOST(self) -> str: ...

    @property
    @abstractmethod
    def SMTP_PORT(self) -> int: ...

    @property
    @abstractmethod
    def SMTP_USER(self) -> str: ...

    @property
    @abstractmethod
    def SMTP_PASSWORD(self) -> str: ...

    @property
    @abstractmethod
    def SMTP_FROM(self) -> str: ...


class DevelopEmailConfig(EmailConfig):
    @property
    def SMTP_HOST(self) -> str:
        return os.environ["DEVELOP_SMTP_HOST"]

    @property
    def SMTP_PORT(self) -> int:
        return int(os.environ["DEVELOP_SMTP_PORT"])

    @property
    def SMTP_USER(self) -> str:
        return os.environ["DEVELOP_SMTP_USER"]

    @property
    def SMTP_PASSWORD(self) -> str:
        return os.environ["DEVELOP_SMTP_PASSWORD"]

    @property
    def SMTP_FROM(self) -> str:
        return os.environ["DEVELOP_SMTP_FROM"]


class ProductionEmailConfig(EmailConfig):
    @property
    def SMTP_HOST(self) -> str:
        return os.environ["PRODUCTION_SMTP_HOST"]

    @property
    def SMTP_PORT(self) -> int:
        return int(os.environ["PRODUCTION_SMTP_PORT"])

    @property
    def SMTP_USER(self) -> str:
        return os.environ["PRODUCTION_SMTP_USER"]

    @property
    def SMTP_PASSWORD(self) -> str:
        return os.environ["PRODUCTION_SMTP_PASSWORD"]

    @property
    def SMTP_FROM(self) -> str:
        return os.environ["PRODUCTION_SMTP_FROM"]


def get_email_config() -> EmailConfig:
    env = get_app_config().APPLICATION_ENVIRONMENT
    if env == Env.DEVELOP:
        config = DevelopEmailConfig()
    elif env == Env.PRODUCTION:
        config = ProductionEmailConfig()
    else:
        raise NotImplementedError(f"email config not implemented for env={env}")
    return config


# #
# postgres

class PostgresConfig(ABC):
    @property
    @abstractmethod
    def POSTGRES_HOST(self) -> str: ...

    @property
    @abstractmethod
    def POSTGRES_PORT(self) -> int: ...

    @property
    @abstractmethod
    def POSTGRES_USER(self) -> str: ...

    @property
    @abstractmethod
    def POSTGRES_PASSWORD(self) -> str: ...

    @property
    @abstractmethod
    def POSTGRES_DB(self) -> str: ...

    def async_database_url(self) -> str:
        return (
            f"postgresql+asyncpg://"
            f"{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}"
            f"/{self.POSTGRES_DB}"
        )
    
    def database_url(self) -> str:
        return (
            f"postgresql://"
            f"{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}"
            f"/{self.POSTGRES_DB}"
        )


class DevelopPostgresConfig(PostgresConfig):
    @property
    def POSTGRES_HOST(self) -> str:
        return os.environ["DEVELOP_POSTGRES_HOST"]

    @property
    def POSTGRES_PORT(self) -> int:
        return int(os.environ["DEVELOP_POSTGRES_CONTAINER_PORT"])

    @property
    def POSTGRES_USER(self) -> str:
        return os.environ["DEVELOP_POSTGRES_USER"]

    @property
    def POSTGRES_PASSWORD(self) -> str:
        return os.environ["DEVELOP_POSTGRES_PASSWORD"]

    @property
    def POSTGRES_DB(self) -> str:
        return os.environ["DEVELOP_POSTGRES_DB"]


class ProductionPostgresConfig(PostgresConfig):
    @property
    def POSTGRES_HOST(self) -> str:
        return os.environ["PRODUCTION_POSTGRES_HOST"]

    @property
    def POSTGRES_PORT(self) -> int:
        return int(os.environ["PRODUCTION_POSTGRES_CONTAINER_PORT"])

    @property
    def POSTGRES_USER(self) -> str:
        return os.environ["PRODUCTION_POSTGRES_USER"]

    @property
    def POSTGRES_PASSWORD(self) -> str:
        return os.environ["PRODUCTION_POSTGRES_PASSWORD"]

    @property
    def POSTGRES_DB(self) -> str:
        return os.environ["PRODUCTION_POSTGRES_DB"]


def get_postgres_config() -> PostgresConfig:
    env = get_app_config().APPLICATION_ENVIRONMENT
    if env == Env.DEVELOP:
        config = DevelopPostgresConfig()
    elif env == Env.TEST:
        config = TestPostgresConfig()
    elif env == Env.PRODUCTION:
        config = ProductionPostgresConfig()
    else:
        raise NotImplementedError(f"postgres config not implemented for env={env}")
    return config


# #
# test postgres

class TestPostgresConfig(PostgresConfig):
    @property
    def POSTGRES_HOST(self) -> str:
        return os.environ["TEST_POSTGRES_HOST"]

    @property
    def POSTGRES_PORT(self) -> int:
        return int(os.environ["TEST_POSTGRES_CONTAINER_PORT"])

    @property
    def POSTGRES_USER(self) -> str:
        return os.environ["TEST_POSTGRES_USER"]

    @property
    def POSTGRES_PASSWORD(self) -> str:
        return os.environ["TEST_POSTGRES_PASSWORD"]

    @property
    def POSTGRES_DB(self) -> str:
        return os.environ["TEST_POSTGRES_DB"]


def get_test_postgres_config() -> PostgresConfig:
    config = TestPostgresConfig()
    return config


# #
# auth

class AuthConfig(ABC):
    @property
    @abstractmethod
    def TOKEN_TTL_SEC(self) -> int: ...


class DefaultAuthConfig(AuthConfig):
    @property
    def TOKEN_TTL_SEC(self) -> int:
        return int(os.environ.get("AUTH_TOKEN_TTL_SEC", "2592000"))  # 30d


def get_auth_config() -> AuthConfig:
    config = DefaultAuthConfig()
    return config