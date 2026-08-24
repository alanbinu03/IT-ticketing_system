# SLA

Implemented in Milestone 4. Calculations belong in the SLA service, never in ticket route handlers.

## V1 policies (seed later)

| Priority | First response | Resolution |
| --- | --- | --- |
| P1 `CRITICAL` | 15 minutes | 2 hours |
| P2 `HIGH` | 30 minutes | 4 hours |
| P3 `MEDIUM` | 2 hours | 1 business day (treated as 8 elapsed hours in V1) |
| P4 `LOW` | 4 hours | 3 business days (treated as 24 elapsed hours in V1) |

V1 uses elapsed wall-clock minutes so the first version stays testable. Business hours, weekends, holidays, department-specific policies, and escalation schedules are extension points on `sla_policies`, not separate systems.

## Data

- `sla_policies` — named policy, priority, `first_response_minutes`, `resolution_minutes`, `pause_on_statuses` (later JSON or related table)
- `sla_events` — append-only: `STARTED`, `PAUSED`, `RESUMED`, `FIRST_RESPONSE_MET`, `FIRST_RESPONSE_BREACHED`, `RESOLUTION_WARNING`, `RESOLUTION_BREACHED`, `COMPLETED`

`WAITING_FOR_USER` (and optionally `ON_HOLD` / `WAITING_FOR_VENDOR`) may pause the resolution timer when the policy says so.

## Runtime

A Redis-backed worker periodically evaluates open tickets (Milestone 3 worker + Milestone 4 jobs). HTTP ticket create/update only writes `STARTED` / pause / first-response timestamps inside the transaction and enqueues a check; it does not wait for email or heavy SLA fan-out.

Warning threshold: default 80% of the resolution window (`ticket.sla_warning`). Breach emits `ticket.sla_breached` for escalation handlers.

## Escalation abstraction

Escalation is not a pile of `if priority == P1` inside `TicketService`. A later rules table binds event + condition → notify role / reassign. Domain event names stay as listed in `docs/architecture.md`.
