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

    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://"
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
# crypto

class CryptoConfig(ABC):
    @property
    @abstractmethod
    def ARGON2_TIME_COST(self) -> int: ...

    @property
    @abstractmethod
    def ARGON2_MEMORY_COST(self) -> int: ...

    @property
    @abstractmethod
    def ARGON2_PARALLELISM(self) -> int: ...

    @property
    @abstractmethod
    def KEK_LENGTH(self) -> int: ...

    @property
    @abstractmethod
    def DEK_LENGTH(self) -> int: ...

    @property
    @abstractmethod
    def SALT_LENGTH(self) -> int: ...

    @property
    @abstractmethod
    def SESSION_TTL_SEC(self) -> int: ...


class DevelopCryptoConfig(CryptoConfig):
    @property
    def ARGON2_TIME_COST(self) -> int:
        return int(os.environ.get("DEVELOP_ARGON2_TIME_COST", "3"))

    @property
    def ARGON2_MEMORY_COST(self) -> int:
        return int(os.environ.get("DEVELOP_ARGON2_MEMORY_COST", "65536"))

    @property
    def ARGON2_PARALLELISM(self) -> int:
        return int(os.environ.get("DEVELOP_ARGON2_PARALLELISM", "4"))

    @property
    def KEK_LENGTH(self) -> int:
        return 32

    @property
    def DEK_LENGTH(self) -> int:
        return 32

    @property
    def SALT_LENGTH(self) -> int:
        return 16

    @property
    def SESSION_TTL_SEC(self) -> int:
        return int(os.environ.get("DEVELOP_SESSION_TTL_SEC", "900"))


class ProductionCryptoConfig(CryptoConfig):
    @property
    def ARGON2_TIME_COST(self) -> int:
        return int(os.environ.get("PRODUCTION_ARGON2_TIME_COST", "3"))

    @property
    def ARGON2_MEMORY_COST(self) -> int:
        return int(os.environ.get("PRODUCTION_ARGON2_MEMORY_COST", "65536"))

    @property
    def ARGON2_PARALLELISM(self) -> int:
        return int(os.environ.get("PRODUCTION_ARGON2_PARALLELISM", "4"))

    @property
    def KEK_LENGTH(self) -> int:
        return 32

    @property
    def DEK_LENGTH(self) -> int:
        return 32

    @property
    def SALT_LENGTH(self) -> int:
        return 16

    @property
    def SESSION_TTL_SEC(self) -> int:
        return int(os.environ.get("PRODUCTION_SESSION_TTL_SEC", "900"))


def get_crypto_config() -> CryptoConfig:
    env = get_app_config().APPLICATION_ENVIRONMENT
    if env == Env.DEVELOP or env == Env.TEST:
        config = DevelopCryptoConfig()
    elif env == Env.PRODUCTION:
        config = ProductionCryptoConfig()
    else:
        raise NotImplementedError(f"crypto config not implemented for env={env}")
    return config
