from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_and_verify_password_roundtrip():
    hashed = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", hashed)


def test_verify_rejects_wrong_password():
    hashed = hash_password("correct horse battery staple")
    assert not verify_password("wrong password", hashed)


def test_access_token_roundtrip():
    token = create_access_token(subject="11111111-1111-1111-1111-111111111111",
                                 tenant_id="22222222-2222-2222-2222-222222222222")
    payload = decode_access_token(token)
    assert payload["sub"] == "11111111-1111-1111-1111-111111111111"
    assert payload["tenant_id"] == "22222222-2222-2222-2222-222222222222"


def test_decode_rejects_garbage_token():
    try:
        decode_access_token("not-a-real-token")
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
