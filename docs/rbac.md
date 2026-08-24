# RBAC

Every protected resource is authorized by **permission codes**, not by hardcoded role names in services.

## Tables

- `permissions` — stable codes such as `ticket.view_own`
- `roles` — named bundles (`Employee`, `Admin`)
- `role_permissions` — M2M
- `user_roles` — M2M; a user may have several roles

Effective permissions = union of all codes from the user’s roles.

## Enforcement

FastAPI dependencies:

- `get_current_user` — valid access JWT, user exists, `is_active`
- `require_permission("user.create")` — 403 `FORBIDDEN` if the code is absent

Frontend hiding of buttons is cosmetic. The API is the security boundary.

Self-service exception: `GET /api/v1/users/{id}` is allowed when `{id}` is the current user, without `user.view`.

## Seeded roles

See the matrix in `docs/architecture.md`. System roles (`is_system=true`) cannot be deleted. Admin receives every permission code.

V1 uses two roles only: employees open and track their own tickets; admins see every ticket and assign work to Hardik, Ronald, or Sanjay.

## Cache

Optional Redis key `rbac:user:{id}` with a short TTL (60s). Invalidated when `user_roles` or `role_permissions` change for that user or role.

## Internal notes (Milestone 2)

`ticket.internal_note` is required to create or **read** internal notes. Listing comments for a caller without that permission must omit `INTERNAL_NOTE` in the service layer.
