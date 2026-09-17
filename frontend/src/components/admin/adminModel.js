// Frontend preview only. These records do not grant access to the application.
export const STORAGE_KEY = 'tn_admin_preview_v1';
export const ROLES = ['Department User', 'Admin', 'Viewer', 'Website Manager'];
export const LOCATION_TYPES = ['Zones', 'Taluks', 'Firkas', 'Municipalities', 'Villages', 'Wards'];
export const PARENT_TYPES = { Taluks: 'Zones', Firkas: 'Taluks', Municipalities: 'Zones', Villages: 'Firkas', Wards: 'Municipalities' };
export const emptyAdminState = () => ({ users: [], locations: [], mappings: [], activity: [], backups: [] });
export const makeId = () => crypto.randomUUID();
export const formatDate = value => value ? new Date(value).toLocaleString('en-IN', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : 'Never';

export function loadAdminState(storage) {
  const saved = storage.getItem(STORAGE_KEY);
  if (!saved) return emptyAdminState();
  const parsed = JSON.parse(saved);
  if (!['users', 'locations', 'mappings', 'activity', 'backups'].every(key => Array.isArray(parsed[key]))) {
    throw new Error('Saved preview data could not be read.');
  }
  return parsed;
}

export function withActivity(state, type, detail) {
  return { ...state, activity: [{ id: makeId(), type, detail, date: new Date().toISOString() }, ...state.activity].slice(0, 50) };
}

export function validateUser(form, users) {
  if (!form.name.trim()) return 'Enter a full name.';
  if (!form.department.trim()) return 'Enter a section.';
  if (!/^[+\d\s()-]+$/.test(form.mobile) || form.mobile.replace(/\D/g, '').length < 10 || form.mobile.replace(/\D/g, '').length > 15) return 'Enter a valid mobile number (10–15 digits).';
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) return 'Enter a valid email address.';
  if (users.some(user => user.id !== form.id && user.email.toLowerCase() === form.email.trim().toLowerCase())) return 'This email address is already in use.';
  if ((!form.id || form.password) && form.password.length < 8) return 'Use at least 8 characters for the password.';
  if (form.password !== form.confirmPassword) return 'The passwords do not match.';
  return '';
}

export function userRecord(form) {
  // Deliberately allowlist fields: passwords must never enter browser storage or backups.
  return { id: form.id || makeId(), name: form.name.trim(), mobile: form.mobile.trim(), email: form.email.trim().toLowerCase(), department: form.department.trim(), role: form.role, status: form.status, lastLogin: form.lastLogin || null };
}

export function createBackup(state) {
  return { id: makeId(), date: new Date().toISOString(), type: 'Manual', status: 'Completed', snapshot: structuredClone({ users: state.users, locations: state.locations, mappings: state.mappings }) };
}

export function restoreBackup(state, backup) {
  // Keep the backup catalogue and activity trail; restore only preview configuration.
  return withActivity({ ...state, ...structuredClone(backup.snapshot) }, 'UPDATE', `Restored local backup from ${formatDate(backup.date)}.`);
}

export function filterUsers(users, { search, department, role, status }) {
  const query = search.trim().toLowerCase();
  return users.filter(user => (!query || [user.name, user.email, user.mobile].some(value => value.toLowerCase().includes(query))) && (!department || user.department === department) && (!role || user.role === role) && (!status || user.status === status));
}
