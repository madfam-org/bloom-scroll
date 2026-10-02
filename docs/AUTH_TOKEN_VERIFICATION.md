# Janua token verification

Status: current as of 2026-10-01 (after #127, which replaced `python-jose` with
PyJWT). This page describes `backend/app/core/auth.py` on `main`; change it in
the same PR as any change to that module.

Bloom Scroll's API verifies Janua access tokens offline, against Janua's
published JWKS. It never calls Janua on the request path.

## Janua side of the contract

Janua defines the issuer, the JWKS endpoint and the token shape:

- [janua `docs/service-tokens.md`](https://github.com/madfam-org/janua/blob/main/docs/service-tokens.md),
  sections "Endpoints" (issuer `https://auth.madfam.io`, JWKS at
  `/.well-known/jwks.json`) and "Token shape" (RS256, `kid` in the header).
- [janua `ECOSYSTEM.md`](https://github.com/madfam-org/janua/blob/main/ECOSYSTEM.md),
  section "Cross-repo conventions": Janua tokens are RS256 only.

## Verification steps

`verify_token(token)` returns a `TokenPayload` or `None`; it never raises.
`get_current_user` turns `None` into HTTP 401.

1. **Algorithm.** The header `alg` must equal `JANUA_JWT_ALGORITHM` (default
   `RS256`). The algorithm passed to PyJWT comes from configuration, never from
   the token: `algorithms=["RS256"]`, and the JWK is loaded with
   `PyJWK(jwk, algorithm="RS256")`. `alg: none`, HS256 signed with the RSA
   public key, and any other algorithm fail.
2. **Key selection.** The JWK whose `kid` equals the header `kid`. A token with
   no `kid` is accepted only when the JWKS holds exactly one key. No match means
   rejection.
3. **JWKS cache.** The JWKS is fetched from `JANUA_JWKS_URI` (default
   `https://auth.madfam.io/.well-known/jwks.json`, 5 s timeout) and cached for
   `JANUA_JWKS_CACHE_SECONDS` (default 300). An unknown `kid` does **not** force
   a re-fetch, so after a Janua key rotation tokens signed with the new key are
   rejected until the cache expires (at most 300 s by default). A failed fetch
   rejects the token.
4. **Claims.**
   - `exp` is verified.
   - `iss` is verified when `JANUA_JWT_ISSUER` is set (default
     `https://auth.madfam.io`).
   - `aud` is verified only when `JANUA_JWT_AUDIENCE` is set. The default is
     empty, so the audience is **not** checked unless the deployment sets it.
   - `sub`, `email`, `exp` and `iat` must be present (`_payload_from_claims`).
5. **Leeway.** 30 s (`JWT_LEEWAY_SECONDS`) on `exp`, `nbf` and `iat`. PyJWT
   rejects an `iat` in the future, and a token is verified moments after Janua
   mints it.

### Other modes

- `JANUA_JWT_ALGORITHM=HS256` (or another `HS*`) verifies with
  `JANUA_JWT_SECRET`. It exists for legacy local development only; production
  uses RS256.
- `AUTH_ENABLED=false` (default `true`) skips verification and returns a fixed
  development user. Local development only.
- Mutating endpoints also accept the `INGEST_API_KEY` service key in
  `X-API-Key` (`require_write_access`), compared in constant time.

## Configuration

| Variable | Default | Notes |
|---|---|---|
| `JANUA_JWKS_URI` | `https://auth.madfam.io/.well-known/jwks.json` | |
| `JANUA_JWT_ISSUER` | `https://auth.madfam.io` | Empty disables the `iss` check |
| `JANUA_JWT_AUDIENCE` | empty | Set it to enforce `aud` |
| `JANUA_JWT_ALGORITHM` | `RS256` | `HS*` only for legacy local dev |
| `JANUA_JWT_SECRET` | dev placeholder | Used only with `HS*` |
| `JANUA_JWKS_CACHE_SECONDS` | `300` | Upper bound on key-rotation lag |
| `AUTH_ENABLED` | `true` | `false` only for local dev |

## Tests

`backend/tests/test_auth.py` pins every step above: valid RS256 via JWKS,
unknown `kid`, no-`kid` with one key and with several keys, forged signature,
tampered payload, `alg: none`, HS256 key confusion, expiry, wrong issuer,
audience enforced and ignored, HS algorithm other than the configured one,
`iat` skew inside and beyond the leeway, missing core claims, JWKS cache reuse,
key rotation after cache expiry, and JWKS fetch failure.

## Dependencies

- `pyjwt[crypto] >=2.15.1,<3` (`backend/pyproject.toml`, locked in
  `backend/poetry.lock`). `python-jose`, `ecdsa`, `rsa` and `pyasn1` left the
  runtime image with #127.
- `sqlalchemy >=2.0.23,<2.1`: SQLAlchemy 2.1 defaults `postgresql://` to
  psycopg v3 and stops installing `greenlet`.

## Known gaps

1. `aud` is not enforced unless `JANUA_JWT_AUDIENCE` is set; no tracked
   manifest sets it.
2. An unknown `kid` does not trigger a JWKS refresh, so key rotation can reject
   valid tokens for up to `JANUA_JWKS_CACHE_SECONDS`.
