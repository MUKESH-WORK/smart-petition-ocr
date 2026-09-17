import { useState } from 'react';
import { Eye, EyeOff, Plus, Search } from 'lucide-react';
import AdminDialog, { DialogActions } from './AdminDialog';
import { filterUsers, ROLES, userRecord, validateUser, withActivity } from './adminModel';

function PasswordField({ label, value, onChange, required }) {
  const [visible, setVisible] = useState(false);
  const id = label.toLowerCase().replaceAll(' ', '-');
  return <div className="admin-field">
    <label htmlFor={id}>{label}</label>
    <div className="admin-password">
      <input id={id} type={visible ? 'text' : 'password'} value={value} onChange={onChange} autoComplete="new-password" required={required} minLength={8} />
      <button type="button" className="admin-icon-button" aria-label={`${visible ? 'Hide' : 'Show'} ${label.toLowerCase()}`} aria-pressed={visible} onClick={() => setVisible(!visible)}>
        {visible ? <EyeOff size={17} /> : <Eye size={17} />}
      </button>
    </div>
  </div>;
}

function UserDialog({ user, users, sections, commit, onClose }) {
  const [form, setForm] = useState({ name: '', mobile: '', email: '', department: '', role: 'Department User', status: 'Active', ...user, password: '', confirmPassword: '' });
  const [error, setError] = useState('');
  const field = key => ({ value: form[key], onChange: event => setForm({ ...form, [key]: event.target.value }) });
  const edit = Boolean(user);
  function submit(event) {
    event.preventDefault();
    const validation = validateUser(form, users);
    if (validation) { setError(validation); return; }
    const record = userRecord(form);
    if (commit(state => withActivity({ ...state, users: edit ? state.users.map(item => item.id === user.id ? record : item) : [...state.users, record] }, edit ? 'UPDATE' : 'CREATE', `${edit ? 'Updated' : 'Added'} user ${record.name}.`))) onClose();
    else setError('Could not save this change. Browser storage is unavailable or full.');
  }
  return <AdminDialog title={edit ? 'User Details' : 'Add User'} onClose={onClose}>
    <p className="admin-note">Local preview only. Account access and passwords are not changed or saved.</p>
    <form onSubmit={submit}>
      <fieldset className="admin-fieldset"><legend>Basic Details</legend>
        <div className="admin-form-grid">
          <label className="admin-field admin-span-2">{edit ? 'Name' : 'Full Name'}<input {...field('name')} autoComplete="name" required maxLength={100} /></label>
          <label className="admin-field">Mobile Number<input {...field('mobile')} type="tel" autoComplete="tel" required maxLength={22} /></label>
          <label className="admin-field">Email<input {...field('email')} type="email" autoComplete="email" required maxLength={254} /></label>
          <label className="admin-field admin-span-2">Section<input {...field('department')} list="admin-sections" required maxLength={100} /></label>
          <datalist id="admin-sections">{sections.map(value => <option key={value} value={value} />)}</datalist>
          <label className="admin-field">Role<select {...field('role')}>{ROLES.map(role => <option key={role}>{role}</option>)}</select></label>
          <label className="admin-field">Status<select {...field('status')}><option>Active</option><option>Inactive</option></select></label>
        </div>
      </fieldset>
      <fieldset className="admin-fieldset"><legend>{edit ? 'Password' : 'Account'}</legend>
        {edit && <p className="admin-note">Leave blank to keep the current password.</p>}
        <div className="admin-form-grid">
          <PasswordField label={edit ? 'New Password' : 'Password'} {...field('password')} required={!edit} />
          <PasswordField label={edit ? 'Confirm New Password' : 'Confirm Password'} {...field('confirmPassword')} required={!edit || Boolean(form.password)} />
        </div>
      </fieldset>
      {error && <p role="alert" className="admin-error">{error}</p>}
      <DialogActions onClose={onClose} submitLabel={edit ? 'Save Changes' : 'Add User'} />
    </form>
  </AdminDialog>;
}

export default function UserManagement({ state, commit }) {
  const [filters, setFilters] = useState({ search: '', department: '', role: '', status: '' });
  const [dialog, setDialog] = useState(null);
  // Keep the stored field name for compatibility with existing user records and backups.
  const sections = [...new Set(state.users.map(user => user.department))].filter(Boolean).sort();
  const users = filterUsers(state.users, filters);
  const filter = key => ({ value: filters[key], onChange: event => setFilters({ ...filters, [key]: event.target.value }) });
  return <>
    <header className="admin-page-header">
      <div><h1>All Users</h1><p aria-live="polite">{users.length} {users.length === 1 ? 'user' : 'users'} found</p></div>
      <button type="button" className="admin-button" onClick={() => setDialog({})}><Plus size={17} /> Add User</button>
    </header>
    <p className="admin-note">Local preview · Changes apply only in this browser tab.</p>
    <div className="admin-user-filters">
      <label className="admin-search"><Search size={17} aria-hidden="true" /><input type="search" aria-label="Search users" placeholder="Search…" {...filter('search')} /></label>
      <select aria-label="Filter by section" {...filter('department')}><option value="">All Sections</option>{sections.map(section => <option key={section}>{section}</option>)}</select>
      <select aria-label="Filter by role" {...filter('role')}><option value="">All Roles</option>{ROLES.map(role => <option key={role}>{role}</option>)}</select>
      <select aria-label="Filter by status" {...filter('status')}><option value="">All Status</option><option>Active</option><option>Inactive</option></select>
    </div>
    <div className="admin-table-scroll" tabIndex={0} role="region" aria-label="Users table">
      <table className="admin-table admin-users-table">
        <thead><tr>{['Name', 'Section', 'Role', 'Status'].map(label => <th scope="col" key={label}>{label}</th>)}</tr></thead>
        <tbody>{users.map(user => <tr key={user.id} onClick={() => setDialog({ user })}>
          <td><div className="admin-user-name"><span className="admin-avatar" aria-hidden="true">{user.name.split(/\s+/).filter(Boolean).slice(0, 2).map(part => part[0]).join('').toUpperCase()}</span><div><button type="button" className="admin-name-button" onClick={event => { event.stopPropagation(); setDialog({ user }); }}>{user.name}</button><span className="admin-email">{user.email}</span></div></div></td>
          <td>{user.department}</td><td>{user.role}</td><td><span className={`admin-status ${user.status === 'Active' ? 'is-success' : ''}`}>{user.status}</span></td>
        </tr>)}</tbody>
      </table>
      {!users.length && <div className="admin-empty">{state.users.length ? 'No users match these filters.' : 'No users yet. Add a user to begin.'}</div>}
    </div>
    {dialog && <UserDialog user={dialog.user} users={state.users} sections={sections} commit={commit} onClose={() => setDialog(null)} />}
  </>;
}
