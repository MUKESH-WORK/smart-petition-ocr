import { useState } from 'react';
import { Eye, EyeOff, Plus, Search, Trash2, AlertTriangle, RefreshCw, Key, UserCheck, ShieldCheck } from 'lucide-react';
import AdminDialog from './AdminDialog';
import { createAdminUser, updateAdminUser, deleteAdminUser, updateUserPassword } from '../../services/apiService';
import { getTranslation } from '../../utils/translations';

function PasswordField({ label, value, onChange, required, placeholder = '' }) {
  const [visible, setVisible] = useState(false);
  const id = label.toLowerCase().replaceAll(' ', '-');
  return (
    <div className="admin-field">
      <label htmlFor={id}>{label}</label>
      <div className="admin-password">
        <input
          id={id}
          type={visible ? 'text' : 'password'}
          value={value}
          onChange={onChange}
          autoComplete="new-password"
          required={required}
          minLength={8}
          placeholder={placeholder}
        />
        <button
          type="button"
          className="admin-icon-button"
          aria-label={`${visible ? 'Hide' : 'Show'} ${label.toLowerCase()}`}
          aria-pressed={visible}
          onClick={() => setVisible(!visible)}
        >
          {visible ? <EyeOff size={17} /> : <Eye size={17} />}
        </button>
      </div>
    </div>
  );
}

/**
 * Dedicated Password Dialog for District Admin to update an official's password
 */
function PasswordDialog({ user, onSuccess, onClose }) {
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [successMsg, setSuccessMsg] = useState('');

  async function handleSubmit(event) {
    if (event) event.preventDefault();
    setError('');
    setSuccessMsg('');

    if (!password || password.length < 8) {
      setError('Password must be at least 8 characters long.');
      return;
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match. Please verify.');
      return;
    }

    setSubmitting(true);
    try {
      await updateUserPassword(user.id, password.trim());
      setSuccessMsg(`Password for ${user.name} updated successfully.`);
      if (onSuccess) await onSuccess();
      setTimeout(() => {
        onClose();
      }, 1200);
    } catch (err) {
      setError(err.message || 'Failed to update official password.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AdminDialog title={`Edit Password: ${user.name}`} onClose={onClose}>
      <form onSubmit={handleSubmit}>
        <div style={{ background: 'var(--bg-canvas)', padding: '12px 16px', borderRadius: 'var(--radius-md)', marginBottom: '16px', border: '1px solid var(--border-subtle)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 600, color: 'var(--text-primary)' }}>
            <Key size={16} style={{ color: 'var(--primary-brand)' }} />
            <span>{user.name} ({user.id})</span>
          </div>
          <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginTop: '4px' }}>
            {user.email} • {user.department || 'District Administration'}
          </div>
        </div>

        <fieldset className="admin-fieldset" style={{ marginTop: 0 }}>
          <legend>Set New Password</legend>
          <div className="admin-form-grid">
            <PasswordField
              label="New Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="Minimum 8 characters"
            />
            <PasswordField
              label="Confirm New Password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              placeholder="Re-enter password"
            />
          </div>
        </fieldset>

        {error && (
          <p role="alert" className="admin-error">
            {error}
          </p>
        )}

        {successMsg && (
          <div style={{ color: '#15803d', background: '#dcfce7', border: '1px solid #86efac', padding: '10px 12px', fontSize: '.84rem', borderRadius: 'var(--radius-md)', marginTop: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <ShieldCheck size={16} />
            {successMsg}
          </div>
        )}

        <div className="admin-dialog-actions" style={{ justifyContent: 'flex-end', gap: '8px' }}>
          <button type="button" className="admin-button admin-button-secondary" onClick={onClose} disabled={submitting}>
            Cancel
          </button>
          <button type="submit" className="admin-button" disabled={submitting}>
            {submitting ? 'Updating Password…' : 'Save Password'}
          </button>
        </div>
      </form>
    </AdminDialog>
  );
}

function UserDialog({ user, users, sections, onSaveSuccess, onDeleteSuccess, onOpenPasswordDialog, onClose }) {
  const edit = Boolean(user);
  const [form, setForm] = useState({
    name: user?.name || '',
    nameTamil: user?.nameTamil || '',
    mobile: user?.mobile || '',
    email: user?.email || '',
    department: user?.department || 'Revenue Administration',
    role: user?.role || 'Department User',
    status: user?.status === 'Suspended' ? 'Inactive' : (user?.status || 'Active'),
    password: '',
    confirmPassword: ''
  });
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const currentOfficerId = typeof localStorage !== 'undefined' ? (localStorage.getItem('officer_id') || '') : '';
  const currentOfficerEmail = typeof localStorage !== 'undefined' ? (localStorage.getItem('officer_email') || '') : '';
  const isCurrentUser = Boolean(user && (user.id === currentOfficerId || (currentOfficerEmail && user.email?.toLowerCase() === currentOfficerEmail.toLowerCase())));

  const field = (key) => ({
    value: form[key],
    onChange: (event) => setForm({ ...form, [key]: event.target.value })
  });

  async function submit(event) {
    if (event) event.preventDefault();
    setError('');

    // Form validations
    if (!edit && !form.name.trim()) {
      setError('Please enter a full name.');
      return;
    }
    if (!form.department.trim()) {
      setError('Please specify a department/section.');
      return;
    }
    if (!edit && (!form.email.trim() || !form.email.includes('@'))) {
      setError('Please enter a valid official email address.');
      return;
    }
    if (!edit && (!form.password || form.password.length < 8)) {
      setError('Initial password must be at least 8 characters long.');
      return;
    }
    if (!edit && form.password !== form.confirmPassword) {
      setError('Passwords do not match. Please verify.');
      return;
    }

    setSubmitting(true);
    try {
      if (edit) {
        const updatePayload = {
          name: form.name.trim(),
          name_tamil: form.nameTamil.trim() || null,
          mobile: form.mobile.trim(),
          email: form.email.trim().toLowerCase(),
          department: form.department.trim(),
          status: form.status
        };
        await updateAdminUser(user.id, updatePayload);
      } else {
        const createPayload = {
          name: form.name.trim(),
          name_tamil: form.nameTamil.trim() || null,
          mobile: form.mobile.trim(),
          email: form.email.trim().toLowerCase(),
          department: form.department.trim(),
          role: form.role || 'Department User',
          status: form.status,
          password: form.password ? form.password.trim() : 'Govt@2024'
        };
        await createAdminUser(createPayload);
      }

      await onSaveSuccess();
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to save user account to database.');
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete() {
    if (isCurrentUser) {
      setError('You cannot delete your own active administrator account.');
      return;
    }
    setSubmitting(true);
    try {
      await deleteAdminUser(user.id);
      await onDeleteSuccess();
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to delete user account.');
      setConfirmDelete(false);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AdminDialog title={edit ? `Edit User: ${user.name}` : 'Add Official Account'} onClose={onClose}>
      <form onSubmit={submit}>
        <fieldset className="admin-fieldset">
          <legend>Official Identity & Contact</legend>
          <div className="admin-form-grid">
            <label className="admin-field admin-span-2">
              Full Name (English)
              <input
                {...field('name')}
                autoComplete="name"
                required
                maxLength={100}
                placeholder="e.g. S. Ramanathan"
              />
            </label>
            <label className="admin-field admin-span-2">
              Full Name (Tamil - optional)
              <input
                {...field('nameTamil')}
                maxLength={100}
                placeholder="எ.கா. சு. இராமநாதன்"
              />
            </label>
            <label className="admin-field">
              Mobile Number
              <input
                {...field('mobile')}
                type="tel"
                autoComplete="tel"
                required
                maxLength={20}
                placeholder="9842011001"
              />
            </label>
            <label className="admin-field">
              Official Email
              <input
                {...field('email')}
                type="email"
                autoComplete="email"
                required
                maxLength={254}
                placeholder="officer@tn.gov.in"
              />
            </label>
            <label className="admin-field admin-span-2">
              Department / Section
              <input {...field('department')} list="admin-sections-list" required maxLength={100} placeholder="e.g. Revenue Administration" />
            </label>
            <datalist id="admin-sections-list">
              {sections.map((sec) => (
                <option key={sec} value={sec} />
              ))}
            </datalist>
          </div>
        </fieldset>

        {!edit ? (
          <fieldset className="admin-fieldset">
            <legend>Initial Password</legend>
            <div className="admin-form-grid">
              <PasswordField label="Password" {...field('password')} required />
              <PasswordField
                label="Confirm Password"
                {...field('confirmPassword')}
                required
              />
            </div>
          </fieldset>
        ) : (
          <div style={{ marginTop: '16px', padding: '12px 16px', background: 'var(--bg-canvas)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <div style={{ fontWeight: 600, fontSize: '0.86rem', color: 'var(--text-primary)' }}>Account Security</div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Need to reset or change this official's credentials?</div>
            </div>
            <button
              type="button"
              className="admin-button admin-button-secondary"
              style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '0.82rem', padding: '6px 12px' }}
              onClick={() => {
                onClose();
                onOpenPasswordDialog(user);
              }}
            >
              <Key size={14} /> Edit Password
            </button>
          </div>
        )}

        {error && (
          <p role="alert" className="admin-error">
            {error}
          </p>
        )}

        {confirmDelete && (
          <div className="admin-db-banner is-disconnected" style={{ marginTop: '12px' }}>
            <span>Permanently delete user <strong>{user.name}</strong> ({user.id}) from the database?</span>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                type="button"
                className="admin-reconnect-btn"
                onClick={handleDelete}
                disabled={submitting}
              >
                Yes, Delete
              </button>
              <button
                type="button"
                className="admin-button admin-button-secondary"
                style={{ padding: '4px 10px', fontSize: '0.8rem' }}
                onClick={() => setConfirmDelete(false)}
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        <div className="admin-dialog-actions" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            {edit && !confirmDelete && !isCurrentUser && (
              <button
                type="button"
                className="admin-button admin-button-danger"
                style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                onClick={() => setConfirmDelete(true)}
                disabled={submitting}
              >
                <Trash2 size={16} /> Delete User
              </button>
            )}
            {isCurrentUser && (
              <span className="admin-note" style={{ color: '#047857', fontWeight: 600 }}>
                Active Session Account
              </span>
            )}
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button type="button" className="admin-button admin-button-secondary" onClick={onClose} disabled={submitting}>
              Cancel
            </button>
            <button type="submit" className="admin-button" disabled={submitting}>
              {submitting ? 'Saving…' : edit ? 'Save Profile' : 'Create Account'}
            </button>
          </div>
        </div>
      </form>
    </AdminDialog>
  );
}

export default function UserManagement({
  users = [],
  loading = false,
  dbHealth = null,
  onRefreshUsers,
  onReconnectDb,
  currentLanguage = 'en'
}) {
  const [filters, setFilters] = useState({ search: '', department: '', status: '' });
  const [dialog, setDialog] = useState(null);
  const [passwordDialogUser, setPasswordDialogUser] = useState(null);

  // Common official sections
  const defaultSections = [
    'District Administration / Collectorate',
    'Revenue Administration',
    'Civil Supplies & Consumer Protection',
    'Land Administration & Survey',
    'Municipal Administration & Water Supply',
    'Rural Development & Panchayat Raj',
    'TANGEDCO / Electricity Distribution',
    'School Education & Literacy',
    'Public Health & Family Welfare',
    'Agriculture & Farmers Welfare'
  ];
  const dynamicSections = [...new Set([...defaultSections, ...users.map((u) => u.department)])].filter(Boolean).sort();

  // Determine current active officer from session storage
  let currentOfficerId = '';
  try {
    const raw = sessionStorage.getItem('gdp_officer_session') || localStorage.getItem('gdp_officer_session');
    if (raw) {
      const parsed = JSON.parse(raw);
      currentOfficerId = parsed?.id || parsed?.officerId || '';
    }
  } catch { }
  if (!currentOfficerId) {
    currentOfficerId = localStorage.getItem('officer_id') || '';
  }

  const onlineCount = users.filter((u) => u.isOnline || (currentOfficerId && u.id === currentOfficerId)).length;
  const offlineCount = Math.max(0, users.length - onlineCount);

  const query = filters.search.trim().toLowerCase();
  const filteredUsers = users.filter((u) => {
    const isUserOnline = Boolean(u.isOnline || (currentOfficerId && u.id === currentOfficerId));
    const matchQuery =
      !query ||
      (u.name && u.name.toLowerCase().includes(query)) ||
      (u.email && u.email.toLowerCase().includes(query)) ||
      (u.mobile && u.mobile.includes(query)) ||
      (u.id && u.id.toLowerCase().includes(query));
    const matchDept = !filters.department || u.department === filters.department;
    let matchStatus = true;
    if (filters.status === 'Online') {
      matchStatus = isUserOnline;
    } else if (filters.status === 'Offline') {
      matchStatus = !isUserOnline;
    } else if (filters.status === 'Active') {
      matchStatus = u.status === 'Active';
    } else if (filters.status === 'Inactive') {
      matchStatus = u.status === 'Inactive';
    }
    return matchQuery && matchDept && matchStatus;
  });

  const filter = (key) => ({
    value: filters[key],
    onChange: (event) => setFilters({ ...filters, [key]: event.target.value })
  });

  const isDbDisconnected = dbHealth?.status === 'disconnected' || dbHealth?.admin_db?.status === 'disconnected';

  return (
    <>
      <header className="admin-page-header">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <h1>{getTranslation(currentLanguage, 'allUsers', 'All Users')}</h1>
          </div>
          <div className="admin-stat-summary-pill" aria-live="polite">
            {loading ? (
              <span>Refreshing user accounts…</span>
            ) : (
              <>
                <span className="online-badge">
                  <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#22c55e', display: 'inline-block' }}></span>
                  {onlineCount} {currentLanguage === 'ta' ? 'ஆன்லைனில்' : 'Currently Online'}
                </span>
                <span className="offline-badge">
                  <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#94a3b8', display: 'inline-block' }}></span>
                  {offlineCount} {currentLanguage === 'ta' ? 'ஆஃப்லைனில்' : 'Offline'}
                </span>
                <span>({users.length} {currentLanguage === 'ta' ? 'மொத்த அரசு கணக்குகள்' : 'Total Accounts'})</span>
              </>
            )}
          </div>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            type="button"
            className="admin-button admin-button-secondary"
            onClick={onRefreshUsers}
            disabled={loading}
            title="Refresh accounts from database"
          >
            <RefreshCw size={16} className={loading ? 'spin-icon' : ''} /> {getTranslation(currentLanguage, 'refresh', 'Refresh')}
          </button>
          <button
            type="button"
            className="admin-button"
            onClick={() => setDialog({})}
            disabled={isDbDisconnected}
          >
            <Plus size={17} /> {getTranslation(currentLanguage, 'addUser', 'Add User')}
          </button>
        </div>
      </header>



      <div className="admin-user-filters">
        <label className="admin-search">
          <Search size={17} aria-hidden="true" />
          <input
            type="search"
            aria-label="Search users by name, email, mobile, or ID"
            placeholder="Search by name, email, or ID…"
            {...filter('search')}
          />
        </label>
        <select aria-label="Filter by department" {...filter('department')}>
          <option value="">All Departments</option>
          {dynamicSections.map((sec) => (
            <option key={sec} value={sec}>{sec}</option>
          ))}
        </select>
        <select aria-label="Filter by status" {...filter('status')}>
          <option value="">All Presence & Status</option>
          <option value="Active">Account: Active</option>
          <option value="Inactive">Account: Inactive</option>
        </select>
      </div>

      <div className="admin-table-scroll" tabIndex={0} role="region" aria-label="Users table">
        <table className="admin-table admin-users-table">
          <thead>
            <tr>
              <th scope="col">{getTranslation(currentLanguage, 'officialAccount', 'Official Account')}</th>
              <th scope="col">{getTranslation(currentLanguage, 'departmentSection', 'Department / Section')}</th>
              <th scope="col">{getTranslation(currentLanguage, 'status', 'Status')}</th>
              <th scope="col">{getTranslation(currentLanguage, 'lastLogin', 'Last Login')}</th>
              <th scope="col" style={{ textAlign: 'right', paddingRight: '20px' }}>{getTranslation(currentLanguage, 'actions', 'Actions')}</th>
            </tr>
          </thead>
          <tbody>
            {filteredUsers.map((user) => {
              const displayName = (currentLanguage === 'ta' && user.nameTamil) ? user.nameTamil : user.name;
              const isUserOnline = Boolean(user.isOnline || (currentOfficerId && user.id === currentOfficerId));
              const isYou = Boolean(user.isCurrent || (currentOfficerId && user.id === currentOfficerId));
              const initials = (displayName || 'User')
                .split(/\s+/)
                .filter(Boolean)
                .slice(0, 2)
                .map((part) => part[0])
                .join('')
                .toUpperCase();

              return (
                <tr key={user.id}>
                  <td onClick={() => setDialog({ user })}>
                    <div className="admin-user-name">
                      <div className="admin-avatar-wrap">
                        <span className="admin-avatar" aria-hidden="true">
                          {initials}
                        </span>
                        {isUserOnline && <span className="admin-avatar-online-dot" title="Currently Online" />}
                      </div>
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center' }}>
                          <button
                            type="button"
                            className="admin-name-button"
                            onClick={(event) => {
                              event.stopPropagation();
                              setDialog({ user });
                            }}
                          >
                            {displayName}
                          </button>
                          <span className="admin-id-badge">{user.id}</span>

                        </div>
                        <span className="admin-email">{user.email}</span>
                      </div>
                    </div>
                  </td>
                  <td onClick={() => setDialog({ user })}>{user.department || '—'}</td>
                  <td onClick={() => setDialog({ user })}>
                    {isUserOnline ? (
                      <span className="admin-status is-online">
                        {isYou ? 'Online (You)' : 'Online'}
                      </span>
                    ) : user.status === 'Inactive' ? (
                      <span className="admin-status is-inactive">
                        Inactive
                      </span>
                    ) : (
                      <span className="admin-status is-offline">
                        Offline
                      </span>
                    )}
                  </td>
                  <td className="admin-date" onClick={() => setDialog({ user })}>
                    {isYou ? (
                      <span style={{ color: '#15803d', fontWeight: 600 }}>Active Now</span>
                    ) : user.lastLogin ? (
                      new Date(user.lastLogin).toLocaleString('en-IN', { dateStyle: 'short', timeStyle: 'short' })
                    ) : (
                      <span style={{ color: '#94a3b8' }}>Never</span>
                    )}
                  </td>
                  <td style={{ textAlign: 'right', paddingRight: '16px' }}>
                    <button
                      type="button"
                      className="admin-button admin-button-secondary"
                      style={{ padding: '4px 12px', fontSize: '0.78rem' }}
                      onClick={(e) => {
                        e.stopPropagation();
                        setDialog({ user });
                      }}
                    >
                      {getTranslation(currentLanguage, 'editProfile', 'Edit Profile')}
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {loading && (
          <div className="admin-empty">
            <RefreshCw size={24} className="spin-icon" style={{ margin: '0 auto 8px' }} />
            <p>Loading authoritative user accounts from database…</p>
          </div>
        )}

        {!loading && !filteredUsers.length && (
          <div className="admin-empty">
            {users.length ? 'No official accounts match the current filter criteria.' : 'No users found in database. Click "Add User" to create one.'}
          </div>
        )}
      </div>

      {dialog && (
        <UserDialog
          user={dialog.user}
          users={users}
          sections={dynamicSections}
          onSaveSuccess={onRefreshUsers}
          onDeleteSuccess={onRefreshUsers}
          onOpenPasswordDialog={(targetUser) => setPasswordDialogUser(targetUser)}
          onClose={() => setDialog(null)}
        />
      )}

      {passwordDialogUser && (
        <PasswordDialog
          user={passwordDialogUser}
          onSuccess={onRefreshUsers}
          onClose={() => setPasswordDialogUser(null)}
        />
      )}
    </>
  );
}
