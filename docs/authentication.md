# Authentication

Password login is the only identity provider in Milestone 1. The auth module is isolated so Microsoft Entra ID, LDAP, or OIDC can be added later without rewriting tickets or RBAC.

## Flow

```text
email + password
      → verify Argon2 hash
      → reject if is_active is false
      → short-lived access JWT
      + opaque refresh token (raw value once; SHA-256 stored)
```

| Token | Lifetime (default) | Format | Storage |
| --- | --- | --- | --- |
| Access | 15 minutes | JWT (`sub`, `typ=access`, `jti`, `iat`, `exp`) | Client memory / memory-safe storage |
| Refresh | 7 days | Opaque `urlsafe` secret | HTTP client storage; server stores hash only |

Access tokens do **not** embed the full permission list. Permissions are loaded from PostgreSQL (optionally cached in Redis by user id) on each authenticated request so role changes apply quickly.

## Endpoints

- `POST /api/v1/auth/login` — body `{ "email", "password" }`. Rate limited per email + IP via Redis.
- `POST /api/v1/auth/refresh` — body `{ "refresh_token" }`. Rotates the refresh token.
- `POST /api/v1/auth/logout` — body `{ "refresh_token" }`. Revokes that token.
- `GET /api/v1/users/me` — current user, roles, and permission codes.

## Refresh rotation and reuse detection

Each refresh token belongs to a `family_id`. On successful refresh:

1. Hash the presented token and look it up.
2. If missing, expired, or revoked: `401 INVALID_REFRESH_TOKEN`.
3. If revoked **and** the family still has live tokens: treat as reuse (possible theft) and revoke the entire family.
4. Otherwise revoke the presented token, insert a new hashed token in the same family, return a new access JWT and new refresh secret.

Logout sets `revoked_at`. Disabling a user revokes all of that user’s refresh tokens.

## Password hashing

Argon2id via `argon2-cffi`. Hashes are never logged. Login responses never echo the password or the hash.

## Secrets

`JWT_SECRET` comes from the environment. It must be at least 32 characters. `.env` is gitignored. Development values in `.env.example` are not production secrets.

## Future SSO

A later `IdentityProvider` interface can issue the same internal user id and refresh-token rows after an OIDC callback. Local password users keep `password_hash`; SSO-only users can use a random unusable hash and `is_verified=true`.

## What is not stored in the API process

- Sessions
- Permission source of truth (DB is source of truth; Redis is a cache)
- Refresh tokens in plaintext
