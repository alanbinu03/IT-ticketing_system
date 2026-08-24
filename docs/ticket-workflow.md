# Ticket workflow

Implemented in Milestone 2. The rules below are the default V1 matrix and must live in one workflow service, not in ticket route handlers.

## Statuses

`NEW`, `OPEN`, `ASSIGNED`, `IN_PROGRESS`, `WAITING_FOR_USER`, `WAITING_FOR_VENDOR`, `ON_HOLD`, `RESOLVED`, `CLOSED`, `CANCELLED`, `REJECTED`, `REOPENED`

## Default transitions

| From | To |
| --- | --- |
| NEW | OPEN, ASSIGNED, CANCELLED, REJECTED |
| OPEN | ASSIGNED, IN_PROGRESS, CANCELLED, REJECTED |
| ASSIGNED | IN_PROGRESS, OPEN, CANCELLED |
| IN_PROGRESS | WAITING_FOR_USER, WAITING_FOR_VENDOR, ON_HOLD, RESOLVED |
| WAITING_FOR_USER | IN_PROGRESS, ON_HOLD, RESOLVED |
| WAITING_FOR_VENDOR | IN_PROGRESS, ON_HOLD |
| ON_HOLD | IN_PROGRESS |
| RESOLVED | CLOSED, REOPENED |
| REOPENED | ASSIGNED, IN_PROGRESS |
| CLOSED | — |
| CANCELLED | — |
| REJECTED | — |

Core happy path from the product brief:

```text
NEW → ASSIGNED → IN_PROGRESS → RESOLVED → CLOSED
                         ↘ WAITING_FOR_USER → IN_PROGRESS
                         ↘ WAITING_FOR_VENDOR
                         ↘ ON_HOLD
RESOLVED → REOPENED
```

Invalid attempts return:

```json
{
  "error": {
    "code": "INVALID_STATUS_TRANSITION",
    "message": "Ticket cannot move from CLOSED to IN_PROGRESS."
  }
}
```

HTTP status: `409 Conflict`.

## History

Each successful transition inserts `ticket_status_history` in the same transaction as the ticket row update. Assignment changes insert `ticket_assignments` in the same way.

Optional `version` on `tickets` is incremented on these updates so concurrent PATCH/assign operations cannot silently overwrite each other (`409 CONCURRENT_UPDATE`).

## Later configuration

Replace the in-code matrix with `workflow_definitions` / `workflow_transitions` without changing ticket HTTP paths. Domain events (`ticket.status_changed`) stay stable for automation.
