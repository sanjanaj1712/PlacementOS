import time
import uuid
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec

import app as app_module
from conftest import make_token

PROTECTED_ENDPOINTS = [
    ("GET", "/me"),
    ("GET", "/profile"),
    ("PATCH", "/profile"),
    ("GET", "/goals"),
    ("POST", "/goals"),
    ("PATCH", f"/goals/{uuid.uuid4()}"),
    ("DELETE", f"/goals/{uuid.uuid4()}"),
    ("GET", "/learning-paths"),
    ("GET", "/learning-paths/1/topics"),
    ("GET", "/progress"),
    ("POST", "/progress"),
    ("PATCH", f"/progress/{uuid.uuid4()}"),
    ("DELETE", f"/progress/{uuid.uuid4()}"),
    ("GET", "/applications"),
    ("POST", "/applications"),
    ("PATCH", f"/applications/{uuid.uuid4()}"),
    ("DELETE", f"/applications/{uuid.uuid4()}"),
    ("GET", "/dashboard"),
]


@pytest.mark.parametrize("method,path", PROTECTED_ENDPOINTS)
def test_protected_endpoints_reject_missing_token(client, method, path):
    response = client.open(path, method=method, json={})
    assert response.status_code == 401


@pytest.mark.parametrize("method,path", PROTECTED_ENDPOINTS)
def test_protected_endpoints_reject_invalid_token(client, method, path):
    response = client.open(
        path,
        method=method,
        json={},
        headers={"Authorization": "Bearer not-a-jwt"}
    )
    assert response.status_code == 401


def auth_status(client, token, scheme="Bearer"):
    response = client.get(
        "/me",
        headers={"Authorization": f"{scheme} {token}"}
    )
    return response.status_code


def test_valid_token_is_accepted(client, user_a):
    response = user_a.get("/me")
    assert response.status_code == 200
    assert response.get_json() == {
        "user_id": user_a.id,
        "email": user_a.email
    }


def test_expired_token_is_rejected(client):
    token = make_token(str(uuid.uuid4()), exp=int(time.time()) - 60)
    assert auth_status(client, token) == 401


def test_token_signed_with_wrong_secret_is_rejected(client):
    token = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "aud": "authenticated",
            "role": "authenticated",
            "iss": "http://supabase.test/auth/v1",
            "exp": int(time.time()) + 3600,
        },
        "some-other-secret-that-is-at-least-32-bytes",
        algorithm="HS256"
    )
    assert auth_status(client, token) == 401


def test_unsigned_token_is_rejected(client):
    token = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "aud": "authenticated",
            "role": "authenticated",
            "iss": "http://supabase.test/auth/v1",
            "exp": int(time.time()) + 3600,
        },
        None,
        algorithm="none"
    )
    assert auth_status(client, token) == 401


@pytest.mark.parametrize("overrides", [
    {"aud": "anon"},
    {"iss": "https://evil.example/auth/v1"},
    {"role": "anon"},
    {"role": "service_role"},
    {"sub": "not-a-uuid"},
    {"exp": None},
])
def test_tokens_with_bad_claims_are_rejected(client, overrides):
    token = make_token(str(uuid.uuid4()), **overrides)
    assert auth_status(client, token) == 401


def test_non_bearer_scheme_is_rejected(client):
    token = make_token(str(uuid.uuid4()))
    assert auth_status(client, token, scheme="Basic") == 401


def test_hs256_rejected_when_no_secret_configured(client, monkeypatch):
    monkeypatch.setattr(app_module, "SUPABASE_JWT_SECRET", None)
    token = make_token(str(uuid.uuid4()))
    assert auth_status(client, token) == 401


def test_asymmetric_token_verified_with_jwks(client, monkeypatch):
    private_key = ec.generate_private_key(ec.SECP256R1())
    user_id = str(uuid.uuid4())
    claims = {
        "sub": user_id,
        "email": "jwks@example.com",
        "aud": "authenticated",
        "role": "authenticated",
        "iss": "http://supabase.test/auth/v1",
        "exp": int(time.time()) + 3600,
    }
    token = jwt.encode(claims, private_key, algorithm="ES256")

    monkeypatch.setattr(
        app_module.jwks_client,
        "get_signing_key_from_jwt",
        lambda _token: SimpleNamespace(key=private_key.public_key())
    )

    response = client.get(
        "/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.get_json()["user_id"] == user_id

    other_key = ec.generate_private_key(ec.SECP256R1())
    forged = jwt.encode(claims, other_key, algorithm="ES256")
    assert auth_status(client, forged) == 401
