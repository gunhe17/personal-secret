from __future__ import annotations

import os

from argon2.low_level import Type, hash_secret_raw
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat, PublicFormat


# #
# crypto

# 클라 측 E2EE 경계라 서버는 이 결과의 평문을 절대 못 본다
# Argon2 파라미터는 signup/login 간, 모든 클라 간 일관돼야 해서 고정값이다

class Crypto:
    _ARGON2_TIME = 3
    _ARGON2_MEMORY = 65536
    _ARGON2_PARALLELISM = 4
    _KEY_LEN = 32
    _SALT_LEN = 16
    _NONCE_LEN = 12

    # #
    # key derivation

    def derive_unlock_key(self, *, password: str, salt: bytes) -> bytes:
        # 반환값 = personal_unlock_key, personal_key 를 여닫는 게이트
        return self._argon2(password=password, salt=salt)

    def derive_login_proof(self, *, password: str, salt: bytes) -> bytes:
        # 반환값 = login_proof, 서버로 보낼 로그인 증명. salt 가 달라 unlock_key 와는 무관
        return self._argon2(password=password, salt=salt)

    def _argon2(self, *, password: str, salt: bytes) -> bytes:
        return hash_secret_raw(
            secret=password.encode("utf-8"),
            salt=salt,
            time_cost=self._ARGON2_TIME,
            memory_cost=self._ARGON2_MEMORY,
            parallelism=self._ARGON2_PARALLELISM,
            hash_len=self._KEY_LEN,
            type=Type.ID,
        )

    # #
    # random

    def generate_salt(self) -> bytes:
        return os.urandom(self._SALT_LEN)

    def generate_team_key(self) -> bytes:
        return os.urandom(self._KEY_LEN)

    # #
    # keypair

    # keypair 는 X25519. public 은 personal_lock, private 은 personal_key 로 쓰인다
    def generate_keypair(self) -> tuple[bytes, bytes]:
        private = X25519PrivateKey.generate()
        private_raw = private.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
        public_raw = private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        return private_raw, public_raw

    # #
    # symmetric

    # AES-256-GCM, nonce‖ct 형식. personal_key 잠금과 value 암호화에 쓴다
    def encrypt(self, *, key: bytes, plaintext: bytes) -> bytes:
        nonce = os.urandom(self._NONCE_LEN)
        return nonce + AESGCM(key).encrypt(nonce, plaintext, None)

    def decrypt(self, *, key: bytes, blob: bytes) -> bytes:
        return AESGCM(key).decrypt(blob[: self._NONCE_LEN], blob[self._NONCE_LEN :], None)

    # #
    # anonymous seal

    # 공개키로 봉인하고 개인키로만 개봉하는 방식으로 team_key 전달에 쓴다
    # 포맷은 eph_pub 32바이트, nonce 12바이트, ct 순. libsodium sealed box 와 동등하고 HKDF-SHA256 사용

    def seal(self, *, recipient_public: bytes, plaintext: bytes) -> bytes:
        ephemeral = X25519PrivateKey.generate()
        eph_public = ephemeral.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        shared = ephemeral.exchange(X25519PublicKey.from_public_bytes(recipient_public))
        box_key = self._box_key(eph_public=eph_public, recipient_public=recipient_public, shared=shared)
        nonce = os.urandom(self._NONCE_LEN)
        return eph_public + nonce + AESGCM(box_key).encrypt(nonce, plaintext, None)

    def unseal(self, *, private: bytes, blob: bytes) -> bytes:
        eph_public, nonce, ct = blob[:32], blob[32 : 32 + self._NONCE_LEN], blob[32 + self._NONCE_LEN :]
        receiver = X25519PrivateKey.from_private_bytes(private)
        shared = receiver.exchange(X25519PublicKey.from_public_bytes(eph_public))
        recipient_public = receiver.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        box_key = self._box_key(eph_public=eph_public, recipient_public=recipient_public, shared=shared)
        return AESGCM(box_key).decrypt(nonce, ct, None)

    def _box_key(self, *, eph_public: bytes, recipient_public: bytes, shared: bytes) -> bytes:
        # 봉인키 = HKDF(shared, info = eph_pub ‖ recipient_pub)
        return HKDF(
            algorithm=hashes.SHA256(),
            length=self._KEY_LEN,
            salt=None,
            info=eph_public + recipient_public,
        ).derive(shared)


# #
# Crypto

crypto = Crypto()
