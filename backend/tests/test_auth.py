"""Janua JWT verification tests."""

import base64
import hashlib
import hmac
import json
import time
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

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


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _configure_hs256(monkeypatch: pytest.MonkeyPatch, audience: str = "") -> None:
    monkeypatch.setattr(auth.settings, "JANUA_JWT_ALGORITHM", "HS256")
    monkeypatch.setattr(auth.settings, "JANUA_JWT_SECRET", "dev-secret-that-is-at-least-32-bytes")
    monkeypatch.setattr(auth.settings, "JANUA_JWT_ISSUER", "janua")
    monkeypatch.setattr(auth.settings, "JANUA_JWT_AUDIENCE", audience)


def _hs256_token(**overrides: Any) -> str:
    return jwt.encode(
        _claims(iss="janua", **overrides),
        "dev-secret-that-is-at-least-32-bytes",
        algorithm="HS256",
    )


def test_verify_token_accepts_rs256_without_kid_when_jwks_has_one_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    private_pem, jwk = _rsa_keypair_jwk()
    _configure_rs256(monkeypatch, jwk)
    token = jwt.encode(_claims(), private_pem, algorithm="RS256")

    payload = auth.verify_token(token)

    assert payload is not None
    assert payload.sub == "user_123"


def test_verify_token_rejects_rs256_signed_by_another_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, jwk = _rsa_keypair_jwk(kid="janua-test-key")
    attacker_pem, _ = _rsa_keypair_jwk(kid="janua-test-key")
    _configure_rs256(monkeypatch, jwk)
    token = jwt.encode(_claims(), attacker_pem, algorithm="RS256", headers={"kid": jwk["kid"]})

    assert auth.verify_token(token) is None


def test_verify_token_rejects_rs256_tampered_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    private_pem, jwk = _rsa_keypair_jwk()
    _configure_rs256(monkeypatch, jwk)
    token = jwt.encode(_claims(), private_pem, algorithm="RS256", headers={"kid": jwk["kid"]})
    header, _, signature = token.split(".")
    forged = _b64url(json.dumps(_claims(roles=["admin"])).encode())

    assert auth.verify_token(f"{header}.{forged}.{signature}") is None


def test_verify_token_rejects_alg_none(monkeypatch: pytest.MonkeyPatch) -> None:
    _, jwk = _rsa_keypair_jwk()
    _configure_rs256(monkeypatch, jwk)
    header = _b64url(json.dumps({"alg": "none", "typ": "JWT", "kid": jwk["kid"]}).encode())
    body = _b64url(json.dumps(_claims()).encode())

    assert auth.verify_token(f"{header}.{body}.") is None


def test_verify_token_rejects_hs256_signed_with_rs256_public_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Key confusion: an HS256 token keyed with the public key must not verify."""
    private_pem, jwk = _rsa_keypair_jwk()
    _configure_rs256(monkeypatch, jwk)
    private_key = serialization.load_pem_private_key(private_pem, password=None)
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT", "kid": jwk["kid"]}).encode())
    body = _b64url(json.dumps(_claims()).encode())
    signature = _b64url(
        hmac.new(public_pem, f"{header}.{body}".encode(), hashlib.sha256).digest()
    )

    assert auth.verify_token(f"{header}.{body}.{signature}") is None


def test_verify_token_rejects_rs256_expired(monkeypatch: pytest.MonkeyPatch) -> None:
    private_pem, jwk = _rsa_keypair_jwk()
    _configure_rs256(monkeypatch, jwk)
    now = int(time.time())
    token = jwt.encode(
        _claims(iat=now - 3600, exp=now - 120),
        private_pem,
        algorithm="RS256",
        headers={"kid": jwk["kid"]},
    )

    assert auth.verify_token(token) is None


def test_verify_token_rejects_rs256_wrong_issuer(monkeypatch: pytest.MonkeyPatch) -> None:
    private_pem, jwk = _rsa_keypair_jwk()
    _configure_rs256(monkeypatch, jwk)
    token = jwt.encode(
        _claims(iss="https://evil.example"),
        private_pem,
        algorithm="RS256",
        headers={"kid": jwk["kid"]},
    )

    assert auth.verify_token(token) is None


def test_verify_token_enforces_configured_audience(monkeypatch: pytest.MonkeyPatch) -> None:
    _configure_hs256(monkeypatch, audience="bloom-scroll")

    assert auth.verify_token(_hs256_token(aud="bloom-scroll")) is not None
    assert auth.verify_token(_hs256_token(aud="another-app")) is None
    assert auth.verify_token(_hs256_token()) is None


def test_verify_token_ignores_audience_when_not_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_hs256(monkeypatch)

    assert auth.verify_token(_hs256_token(aud="any-app")) is not None


def test_verify_token_rejects_hs256_wrong_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    _configure_hs256(monkeypatch)
    token = jwt.encode(
        _claims(iss="janua"), "another-secret-that-is-at-least-32-bytes", algorithm="HS256"
    )

    assert auth.verify_token(token) is None


@pytest.mark.filterwarnings("ignore::UserWarning")
def test_verify_token_rejects_hs_algorithm_other_than_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_hs256(monkeypatch)
    token = jwt.encode(
        _claims(iss="janua"), "dev-secret-that-is-at-least-32-bytes", algorithm="HS512"
    )

    assert auth.verify_token(token) is None


def test_verify_token_tolerates_small_clock_skew_on_iat(monkeypatch: pytest.MonkeyPatch) -> None:
    _configure_hs256(monkeypatch)
    now = int(time.time())

    assert auth.verify_token(_hs256_token(iat=now + 10)) is not None


def test_verify_token_rejects_iat_beyond_leeway(monkeypatch: pytest.MonkeyPatch) -> None:
    _configure_hs256(monkeypatch)
    now = int(time.time())

    assert auth.verify_token(_hs256_token(iat=now + 600, exp=now + 900)) is None


def test_verify_token_rejects_garbage(monkeypatch: pytest.MonkeyPatch) -> None:
    _configure_hs256(monkeypatch)

    assert auth.verify_token("not-a-jwt") is None


# --------------------------------------------------------------------------
# JWKS cache, key rotation and required claims. Contract:
# docs/AUTH_TOKEN_VERIFICATION.md.
# --------------------------------------------------------------------------


def _serve_jwks(monkeypatch: pytest.MonkeyPatch, key_sets: list[list[dict[str, Any]]]) -> list[int]:
    """Serve successive JWKS documents, one per fetch; return the fetch counter."""
    calls = [0]

    class FakeJWKSResponse:
        def __init__(self, keys: list[dict[str, Any]]) -> None:
            self._keys = keys

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {"keys": self._keys}

    def fake_get(*args: Any, **kwargs: Any) -> FakeJWKSResponse:
        keys = key_sets[min(calls[0], len(key_sets) - 1)]
        calls[0] += 1
        return FakeJWKSResponse(keys)

    monkeypatch.setattr(auth.httpx, "get", fake_get)
    return calls


def test_jwks_is_fetched_once_within_cache_window(monkeypatch: pytest.MonkeyPatch) -> None:
    private_pem, jwk = _rsa_keypair_jwk()
    _configure_rs256(monkeypatch, jwk)
    calls = _serve_jwks(monkeypatch, [[jwk]])
    token = jwt.encode(_claims(), private_pem, algorithm="RS256", headers={"kid": jwk["kid"]})

    assert auth.verify_token(token) is not None
    assert auth.verify_token(token) is not None
    assert calls[0] == 1


def test_rotated_key_is_accepted_once_the_jwks_cache_expires(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    old_pem, old_jwk = _rsa_keypair_jwk(kid="key-2026-09")
    new_pem, new_jwk = _rsa_keypair_jwk(kid="key-2026-10")
    _configure_rs256(monkeypatch, old_jwk)
    calls = _serve_jwks(monkeypatch, [[old_jwk], [old_jwk, new_jwk]])

    old_token = jwt.encode(_claims(), old_pem, algorithm="RS256", headers={"kid": "key-2026-09"})
    new_token = jwt.encode(_claims(), new_pem, algorithm="RS256", headers={"kid": "key-2026-10"})

    assert auth.verify_token(old_token) is not None
    # An unknown kid does not force a re-fetch: until the cache expires
    # (JANUA_JWKS_CACHE_SECONDS) a token signed by a freshly rotated key fails.
    assert auth.verify_token(new_token) is None
    assert calls[0] == 1

    monkeypatch.setattr(auth, "_jwks_cache_expires_at", 0.0)
    assert auth.verify_token(new_token) is not None
    assert calls[0] == 2


def test_rs256_token_without_kid_is_rejected_when_jwks_has_several_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    private_pem, jwk = _rsa_keypair_jwk(kid="a")
    _, other_jwk = _rsa_keypair_jwk(kid="b")
    _configure_rs256(monkeypatch, jwk)
    _serve_jwks(monkeypatch, [[jwk, other_jwk]])
    token = jwt.encode(_claims(), private_pem, algorithm="RS256")

    assert auth.verify_token(token) is None


def test_jwks_fetch_failure_rejects_instead_of_raising(monkeypatch: pytest.MonkeyPatch) -> None:
    private_pem, jwk = _rsa_keypair_jwk()
    _configure_rs256(monkeypatch, jwk)

    def failing_get(*args: Any, **kwargs: Any) -> Any:
        raise auth.httpx.ConnectError("janua unreachable")

    monkeypatch.setattr(auth.httpx, "get", failing_get)
    token = jwt.encode(_claims(), private_pem, algorithm="RS256", headers={"kid": jwk["kid"]})

    assert auth.verify_token(token) is None


@pytest.mark.parametrize("missing", ["sub", "email", "exp", "iat"])
def test_verify_token_requires_core_claims(
    monkeypatch: pytest.MonkeyPatch, missing: str
) -> None:
    _configure_hs256(monkeypatch)
    claims = _claims(iss="janua")
    del claims[missing]
    token = jwt.encode(claims, "dev-secret-that-is-at-least-32-bytes", algorithm="HS256")

    assert auth.verify_token(token) is None
