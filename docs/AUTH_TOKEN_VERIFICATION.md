# Janua token verification

Status: current as of 2026-10-02 (after #127, which replaced `python-jose` with
PyJWT, and the verifier hardening that made the audience fail closed and added
the re-fetch on an unknown `kid`). This page describes `backend/app/core/auth.py` on `main`; change it in
the same PR as any change to that module.

Bloom Scroll's API verifies Janua access tokens offline, against Janua's
published JWKS. It never calls Janua on the request path.

## Janua side of the contract

Janua defines the issuer, the JWKS endpoint and the token shape:

- [janua `docs/reference/ISSUER_AND_JWKS.md`](https://github.com/madfam-org/janua/blob/main/docs/reference/ISSUER_AND_JWKS.md):
  one RS256 key with a `kid`, rotation as a hard cut with no overlap, and which
  `aud` each token type carries.

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
   no `kid` is rejected (Janua names its key in every token). The JWK must be an
   RSA key whose `alg` is `RS256` (or absent) and whose `use` is `sig` (or
   absent). No match means rejection.
3. **JWKS cache and rotation.** The JWKS is fetched from `JANUA_JWKS_URI`
   (default `https://auth.madfam.io/.well-known/jwks.json`, 5 s timeout) and
   cached for `JANUA_JWKS_CACHE_SECONDS` (default 300). Janua rotates with a hard
   cut, so a `kid` missing from the cached set forces **one** re-fetch,
   bypassing the cache, before the token is rejected. Forced re-fetches are
   limited to one per 60 s per process
   (`JWKS_FORCED_REFRESH_MIN_INTERVAL_SECONDS`), so forged `kid` values cannot
   turn into a stream of requests to Janua; inside that window an unknown `kid`
   is rejected without a fetch. A failed fetch rejects the token.
4. **Claims.**
   - `exp` is required and verified.
   - `iss` is verified when `JANUA_JWT_ISSUER` is set (default
     `https://auth.madfam.io`).
   - `aud` must contain `JANUA_JWT_AUDIENCE` when it is set. When it is empty
     and `JANUA_JWT_AUDIENCE_REQUIRED` is true (the default), **every** Janua
     token is rejected (fail closed): without an audience, any token Janua
     issues to any client would verify here. `JANUA_JWT_AUDIENCE_REQUIRED=false`
     restores the unchecked behaviour, for local development only.
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
  `X-API-Key` (`require_write_access`), compared in constant time. This path
  does not depend on the audience, so the ingestion CronJob keeps working while
  `JANUA_JWT_AUDIENCE` is unset.

## Configuration

| Variable | Default | Notes |
|---|---|---|
| `JANUA_JWKS_URI` | `https://auth.madfam.io/.well-known/jwks.json` | |
| `JANUA_JWT_ISSUER` | `https://auth.madfam.io` | Empty disables the `iss` check |
| `JANUA_JWT_AUDIENCE` | empty | The `aud` Janua issues for this API; see "Open owner check" |
| `JANUA_JWT_AUDIENCE_REQUIRED` | `true` | With an empty audience, rejects every Janua token. `false` only for local dev |
| `JANUA_JWT_ALGORITHM` | `RS256` | `HS*` only for legacy local dev |
| `JANUA_JWT_SECRET` | dev placeholder | Used only with `HS*` |
| `JANUA_JWKS_CACHE_SECONDS` | `300` | Cache TTL; an unknown `kid` re-fetches early (one per 60 s) |
| `AUTH_ENABLED` | `true` | `false` only for local dev |

## Tests

`backend/tests/test_auth.py` pins every step above: valid RS256 via JWKS,
unknown `kid`, no `kid` with one key and with several keys, a JWK with another
`alg`, `use` or key type, forged signature, tampered payload, `alg: none`,
HS256 key confusion, RS512, expiry and expiry inside the leeway, wrong or
missing issuer, missing `exp`, audience enforced (string and list `aud`, wrong
and missing `aud`), the fail-closed default with no audience configured (also
through `require_write_access`), the explicit opt-out, HS algorithm other than
the configured one, `iat` skew inside and beyond the leeway, missing core
claims, JWKS cache reuse, and the forced re-fetch: a rotated key verifies
inside the cache window, an unknown `kid` re-fetches once and is rejected, a
known `kid` never re-fetches, forged `kid`s are rate-limited, and the re-fetch
is allowed again after the interval.

## Dependencies

- `pyjwt[crypto] >=2.15.1,<3` (`backend/pyproject.toml`, locked in
  `backend/poetry.lock`). `python-jose`, `ecdsa`, `rsa` and `pyasn1` left the
  runtime image with #127.
- `sqlalchemy >=2.0.23,<2.1`: SQLAlchemy 2.1 defaults `postgresql://` to
  psycopg v3 and stops installing `greenlet`.

## Open owner check

No Janua OAuth client for Bloom Scroll is registered or referenced in any
repository: the Flutter frontend has no sign-in, and the ingestion CronJob uses
`X-API-Key`. So the `aud` value this API should accept cannot be derived from
code, and it is not guessed here. Until an owner registers the client (or
names the existing one) and sets `JANUA_JWT_AUDIENCE` in `bloom-scroll-secrets`
to the audience Janua issues to it, every Janua bearer token is rejected with
401. Janua's rule (see `ISSUER_AND_JWKS.md`): an ID token carries the
`client_id`; access and service tokens carry the client's audience, falling
back to Janua's `JWT_AUDIENCE`.

## Known gaps

1. Janua bearer tokens are rejected in production until the audience above is
   set. Service writes through `X-API-Key` are unaffected.
2. A rotated `kid` that arrives within 60 s of the previous forced re-fetch is
   rejected until the next allowed re-fetch or the cache expiry.
