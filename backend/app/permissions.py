"""
Central roles/permissions table.

Routes should never check `role == "librarian"` directly -- they ask for a
permission ("books:delete"), and this file is the only place that decides
which roles grant it. Add a role or change what Staff can touch here, and
every route that uses @permission_required(...) picks it up automatically.
"""

SUPER_ADMIN = "super_admin"
LIBRARIAN = "librarian"
STAFF = "staff"

ALL_ROLES = (SUPER_ADMIN, LIBRARIAN, STAFF)

PERMISSIONS = {
    # "*" = every permission, including settings/user management that no
    # other role gets.
    SUPER_ADMIN: {"*"},

    LIBRARIAN: {
        "books:read", "books:create", "books:update", "books:delete",
        "members:read", "members:create", "members:update", "members:delete",
        "circulation:issue", "circulation:return", "circulation:renew",
        "circulation:reserve", "circulation:cancel_reservation",
        "reports:view", "reports:export",
    },

    STAFF: {
        "books:read",
        "members:read",
        "circulation:issue",
        "circulation:return",
    },

    # Legacy self-registered patron accounts (see auth register route).
    # Deliberately granted nothing here -- self-service patrons are a
    # separate concern from staff RBAC and shouldn't silently inherit
    # access just by existing.
    "member": set(),
}


def role_has_permission(role, permission):
    granted = PERMISSIONS.get(role, set())
    return "*" in granted or permission in granted
