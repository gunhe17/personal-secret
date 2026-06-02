from __future__ import annotations

import os

from argon2.low_level import Type, hash_secret_raw
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from personal_secret.api.config import CryptoConfig
from personal_secret.api.config import get_crypto_config
from personal_secret.api.infrastructure.common.exception import CryptoError


# #
# crypto

class Crypto:
    def __init__(self, *, config: CryptoConfig):
        self._config = config

    # #
    # key derivation

    def generate_salt(self) -> bytes:
        salt = os.urandom(self._config.SALT_LENGTH)
        return salt

    def generate_dek(self) -> bytes:
        dek = os.urandom(self._config.DEK_LENGTH)
        return dek

    def derive_kek(self, *, password: str, salt: bytes) -> bytes:
        try:
            kek = hash_secret_raw(
                secret=password.encode("utf-8"),
                salt=salt,
                time_cost=self._config.ARGON2_TIME_COST,
                memory_cost=self._config.ARGON2_MEMORY_COST,
                parallelism=self._config.ARGON2_PARALLELISM,
                hash_len=self._config.KEK_LENGTH,
                type=Type.ID,
            )
        except Exception as exc:
            raise CryptoError(operation="derive_kek", reason=str(exc))
        return kek

    # #
    # aead

    def encrypt(self, *, key: bytes, plaintext: bytes) -> bytes:
        # nonce(12) + ciphertext를 한 blob으로 (nonce 포맷은 crypto가 소유)
        try:
            nonce = os.urandom(12)
            ciphertext = AESGCM(key).encrypt(nonce, plaintext, None)
        except Exception as exc:
            raise CryptoError(operation="encrypt", reason=str(exc))
        return nonce + ciphertext

    def decrypt(self, *, key: bytes, data: bytes) -> bytes:
        try:
            nonce, ciphertext = data[:12], data[12:]
            plaintext = AESGCM(key).decrypt(nonce, ciphertext, None)
        except Exception as exc:
            raise CryptoError(operation="decrypt", reason=str(exc))
        return plaintext


# #
# Crypto

crypto = Crypto(config=get_crypto_config())
