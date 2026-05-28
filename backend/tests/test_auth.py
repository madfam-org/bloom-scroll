"""Janua JWT verification tests."""

import base64
import time
from typing import Any

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwt

from app.core import auth


def _b64url_uint(value: int) -> str:
    raw = value.to_bytes((value.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _rsa_keypair_jwk(kid: str = "janua-test-key") -> tuple[bytes, dict[str, Any]]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_numbers = private_key.public_key().public_numbers()
    jwk = {
        "kty": "RSA",
        "use": "sig",
        "kid": kid,
        "alg": "RS256",
        "n": _b64url_uint(public_numbers.n),
        "e": _b64url_uint(public_numbers.e),
    }
    return private_pem, jwk


def _claims(**overrides: Any) -> dict[str, Any]:
    now = int(time.time())
    claims: dict[str, Any] = {
        "sub": "user_123",
        "email": "user@madfam.io",
        "roles": ["user"],
        "permissions": ["read"],
        "org_id": "org_123",
        "iat": now,
        "exp": now + 300,
        "iss": "https://auth.madfam.io",
    }
    claims.update(overrides)
    return claims


def _configure_rs256(monkeypatch: pytest.MonkeyPatch, jwk: dict[str, Any]) -> None:
    class FakeJWKSResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {"keys": [jwk]}

    monkeypatch.setattr(auth.settings, "JANUA_JWT_ALGORITHM", "RS256")
    monkeypatch.setattr(auth.settings, "JANUA_JWKS_URI", "https://auth.madfam.io/.well-known/jwks.json")
    monkeypatch.setattr(auth.settings, "JANUA_JWT_ISSUER", "https://auth.madfam.io")
    monkeypatch.setattr(auth.settings, "JANUA_JWT_AUDIENCE", "")
    monkeypatch.setattr(auth.settings, "JANUA_JWKS_CACHE_SECONDS", 300)
    monkeypatch.setattr(auth, "_jwks_cache", None)
    monkeypatch.setattr(auth, "_jwks_cache_expires_at", 0.0)
    monkeypatch.setattr(auth.httpx, "get", lambda *args, **kwargs: FakeJWKSResponse())


def test_verify_token_accepts_janua_rs256_jwks(monkeypatch: pytest.MonkeyPatch) -> None:
    private_pem, jwk = _rsa_keypair_jwk()
    _configure_rs256(monkeypatch, jwk)
    token = jwt.encode(
        _claims(),
        private_pem,
        algorithm="RS256",
        headers={"kid": jwk["kid"]},
    )

    payload = auth.verify_token(token)

    assert payload is not None
    assert payload.sub == "user_123"
    assert payload.email == "user@madfam.io"
    assert payload.roles == ["user"]


def test_verify_token_rejects_rs256_unknown_kid(monkeypatch: pytest.MonkeyPatch) -> None:
    private_pem, jwk = _rsa_keypair_jwk(kid="known-key")
    _configure_rs256(monkeypatch, jwk)
    token = jwt.encode(
        _claims(),
        private_pem,
        algorithm="RS256",
        headers={"kid": "other-key"},
    )

    assert auth.verify_token(token) is None


def test_verify_token_supports_explicit_legacy_hs256(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth.settings, "JANUA_JWT_ALGORITHM", "HS256")
    monkeypatch.setattr(auth.settings, "JANUA_JWT_SECRET", "dev-secret")
    monkeypatch.setattr(auth.settings, "JANUA_JWT_ISSUER", "janua")
    monkeypatch.setattr(auth.settings, "JANUA_JWT_AUDIENCE", "")
    token = jwt.encode(
        _claims(iss="janua"),
        "dev-secret",
        algorithm="HS256",
    )

    payload = auth.verify_token(token)

    assert payload is not None
    assert payload.sub == "user_123"
