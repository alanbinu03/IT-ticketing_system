"""Canonical permission catalog. Ticket codes are seeded now and enforced in Milestone 2."""

from __future__ import annotations

PERMISSIONS: tuple[tuple[str, str, str], ...] = (
    ("ticket.create", "Create tickets", "Submit a new IT ticket."),
    ("ticket.view_own", "View own tickets", "View tickets the user requested."),
    ("ticket.view_team", "View team tickets", "View tickets assigned to the user's IT teams."),
    ("ticket.view_all", "View all tickets", "View every ticket in the organization."),
    ("ticket.update", "Update tickets", "Update ticket fields."),
    ("ticket.assign", "Assign tickets", "Assign a ticket to an admin who will resolve it."),
    ("ticket.reassign", "Reassign tickets", "Change an existing assignment."),
    ("ticket.change_priority", "Change priority", "Change ticket priority."),
    ("ticket.comment", "Comment on tickets", "Add public comments."),
    ("ticket.internal_note", "Internal notes", "Create and read internal notes."),
    ("ticket.resolve", "Resolve tickets", "Mark a ticket resolved."),
    ("ticket.close", "Close tickets", "Close a resolved ticket."),
    ("ticket.reopen", "Reopen tickets", "Reopen an eligible ticket."),
    ("ticket.escalate", "Escalate tickets", "Escalate a ticket."),
    ("user.view", "View users", "List and view user profiles."),
    ("user.create", "Create users", "Create user accounts."),
    ("user.update", "Update users", "Update user profiles."),
    ("user.disable", "Disable users", "Deactivate user accounts."),
    ("user.delete", "Delete users", "Permanently delete user accounts."),
    ("role.manage", "Manage roles", "Create roles and assign permissions."),
    ("team.manage", "Manage teams", "Create IT teams and memberships."),
    ("department.manage", "Manage departments", "Create and update departments."),
    ("category.manage", "Manage categories", "Manage ticket categories."),
    ("sla.manage", "Manage SLA", "Manage SLA policies."),
    ("workflow.manage", "Manage workflows", "Manage status workflows."),
    ("report.view", "View reports", "Access operational reports."),
    ("audit.view", "View audit log", "Read immutable audit records."),
    ("system.manage", "Manage system", "Change system configuration."),
    ("admin.portal.access", "Admin portal", "Sign in to the IT administration portal."),
)

ALL_PERMISSION_CODES: tuple[str, ...] = tuple(code for code, _, _ in PERMISSIONS)

EMPLOYEE_PERMISSIONS: frozenset[str] = frozenset(
    {
        "ticket.create",
        "ticket.view_own",
        "ticket.comment",
        "ticket.reopen",
    }
)

ROLE_EMPLOYEE = "Employee"
ROLE_ADMIN = "Admin"
OBSOLETE_ROLES: tuple[str, ...] = ("IT Agent", "IT Manager")

SYSTEM_ROLES: tuple[str, ...] = (ROLE_EMPLOYEE, ROLE_ADMIN)

ROLE_PERMISSION_MAP: dict[str, frozenset[str]] = {
    ROLE_EMPLOYEE: EMPLOYEE_PERMISSIONS,
    ROLE_ADMIN: frozenset(ALL_PERMISSION_CODES),
}
