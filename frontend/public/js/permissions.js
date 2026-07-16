/**
 * Mirrors backend/permissions.py. Kept in sync manually for now (there's
 * no shared package between the Flask backend and this plain-JS frontend).
 * If you add/change a permission on the backend, update it here too --
 * otherwise the UI and API will disagree about who can do what.
 */

const PERMISSIONS = {
  super_admin: new Set(['*']),
  librarian: new Set([
    'books:read', 'books:create', 'books:update', 'books:delete',
    'members:read', 'members:create', 'members:update', 'members:delete',
    'circulation:issue', 'circulation:return', 'circulation:renew',
    'circulation:reserve', 'circulation:cancel_reservation',
    'reports:view', 'reports:export',
  ]),
  staff: new Set([
    'books:read',
    'members:read',
    'circulation:issue',
    'circulation:return',
  ]),
  member: new Set(),
};

function hasPermission(role, permission) {
  const granted = PERMISSIONS[role] || new Set();
  return granted.has('*') || granted.has(permission);
}

const ROLE_LABELS = {
  super_admin: 'Super Admin',
  librarian: 'Librarian',
  staff: 'Library Staff',
  member: 'Member',
};

function roleLabel(role) {
  return ROLE_LABELS[role] || role;
}
