from __future__ import annotations

import os
import sys
import traceback

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))

from personal_secret.cli.infrastructure.crypto.client import crypto


# #
# harness

def expect_raises(exc_type, fn):
    try:
        fn()
    except exc_type:
        return
    except Exception as e:
        raise AssertionError(f"expected {exc_type.__name__}, got {type(e).__name__}: {e}")
    raise AssertionError(f"expected {exc_type.__name__}, nothing raised")


def run_all(tests) -> int:
    passed, failed = 0, []
    for fn in tests:
        try:
            fn()
            print(f"  PASS  {fn.__name__}")
            passed += 1
        except Exception as e:
            print(f"  FAIL  {fn.__name__}  →  {type(e).__name__}: {e}")
            failed.append((fn.__name__, traceback.format_exc()))
    print(f"\n총 {passed + len(failed)}개 · 통과 {passed} · 실패 {len(failed)}")
    for name, tb in failed:
        print(f"\n--- {name} ---\n{tb}")
    return 1 if failed else 0


# #
# derivation

def derive_unlock_key_is_deterministic():
    salt = crypto.generate_salt()
    a = crypto.derive_unlock_key(password="correct horse", salt=salt)
    b = crypto.derive_unlock_key(password="correct horse", salt=salt)
    assert a == b and len(a) == 32


def derive_differs_by_password_and_salt():
    salt = crypto.generate_salt()
    base = crypto.derive_unlock_key(password="pw", salt=salt)
    assert crypto.derive_unlock_key(password="other", salt=salt) != base   # 비번 다르면
    assert crypto.derive_unlock_key(password="pw", salt=crypto.generate_salt()) != base  # salt 다르면


def unlock_and_login_keys_independent():
    # 같은 비번이라도 salt 가 다르면 두 키가 무관 (login_proof 새도 unlock_key 안 샘)
    unlock_salt, login_salt = crypto.generate_salt(), crypto.generate_salt()
    uk = crypto.derive_unlock_key(password="pw", salt=unlock_salt)
    lp = crypto.derive_login_proof(password="pw", salt=login_salt)
    assert uk != lp


# #
# symmetric (personal_key 잠금 / value 암호화)

def aes_roundtrip_and_tamper():
    key = crypto.generate_team_key()
    blob = crypto.encrypt(key=key, plaintext=b"super-secret")
    assert crypto.decrypt(key=key, blob=blob) == b"super-secret"
    # 변조 감지
    bad = bytearray(blob); bad[-1] ^= 0x01
    expect_raises(Exception, lambda: crypto.decrypt(key=key, blob=bytes(bad)))
    # 다른 키로 복호 실패
    expect_raises(Exception, lambda: crypto.decrypt(key=crypto.generate_team_key(), blob=blob))


def wrap_unwrap_personal_key():
    # personal_key 를 personal_unlock_key 로 잠갔다 푼다
    unlock_key = crypto.derive_unlock_key(password="pw", salt=crypto.generate_salt())
    private, _public = crypto.generate_keypair()
    locked = crypto.encrypt(key=unlock_key, plaintext=private)
    assert crypto.decrypt(key=unlock_key, blob=locked) == private


# #
# anonymous seal (team_key 전달)

def seal_unseal_team_key():
    private, public = crypto.generate_keypair()
    team_key = crypto.generate_team_key()
    sealed = crypto.seal(recipient_public=public, plaintext=team_key)
    assert crypto.unseal(private=private, blob=sealed) == team_key


def seal_only_recipient_can_open():
    _p1, public = crypto.generate_keypair()
    other_private, _p2 = crypto.generate_keypair()
    sealed = crypto.seal(recipient_public=public, plaintext=b"team-key")
    # 다른 개인키로는 못 엶
    expect_raises(Exception, lambda: crypto.unseal(private=other_private, blob=sealed))


# #
# 전체 사슬 (가입 → 로그인 → 팀 접근 → 시크릿)

def full_chain_password_to_secret():
    password = "correct horse battery staple"
    secret_plain = b"db-password=hunter2"

    # 가입: 키쌍 + 비번으로 키 도출 + 개인키 잠금
    unlock_salt, login_salt = crypto.generate_salt(), crypto.generate_salt()
    unlock_key = crypto.derive_unlock_key(password=password, salt=unlock_salt)
    private, public = crypto.generate_keypair()
    personal_locked_key = crypto.encrypt(key=unlock_key, plaintext=private)
    login_proof = crypto.derive_login_proof(password=password, salt=login_salt)

    # 팀 생성: team_key 만들어 내 공개키로 봉인
    team_key = crypto.generate_team_key()
    team_locked_key = crypto.seal(recipient_public=public, plaintext=team_key)

    # 시크릿 저장: value 를 team_key 로 암호화
    value_blob = crypto.encrypt(key=team_key, plaintext=secret_plain)

    # --- 다른 기기에서 로그인부터 복원 ---
    unlock_key2 = crypto.derive_unlock_key(password=password, salt=unlock_salt)
    private2 = crypto.decrypt(key=unlock_key2, blob=personal_locked_key)
    team_key2 = crypto.unseal(private=private2, blob=team_locked_key)
    recovered = crypto.decrypt(key=team_key2, blob=value_blob)

    assert recovered == secret_plain
    assert crypto.derive_login_proof(password=password, salt=login_salt) == login_proof


TESTS = [
    derive_unlock_key_is_deterministic,
    derive_differs_by_password_and_salt,
    unlock_and_login_keys_independent,
    aes_roundtrip_and_tamper,
    wrap_unwrap_personal_key,
    seal_unseal_team_key,
    seal_only_recipient_can_open,
    full_chain_password_to_secret,
]


if __name__ == "__main__":
    sys.exit(run_all(TESTS))
