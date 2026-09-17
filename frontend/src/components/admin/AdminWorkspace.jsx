import { useEffect, useRef, useState } from 'react';
import AdminDashboard from './AdminDashboard';
import UserManagement from './UserManagement';
import BackupPage from './BackupPage';
import { emptyAdminState, loadAdminState, STORAGE_KEY } from './adminModel';
import './AdminWorkspace.css';

export default function AdminWorkspace({ activeModule, onNavigate, onActivityChange }) {
  const [initial] = useState(() => {
    try { return { state: loadAdminState(sessionStorage), error: '' }; }
    catch { return { state: emptyAdminState(), error: 'Saved preview data is unavailable. Changes cannot be saved in this tab.', blocked: true }; }
  });
  const [state, setState] = useState(initial.state);
  const stateRef = useRef(state);
  const [error, setError] = useState(initial.error);
  useEffect(() => { onActivityChange?.(state.activity); }, [state.activity, onActivityChange]);
  function commit(update) {
    if (initial.blocked) return false;
    try {
      const next = update(stateRef.current);
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      stateRef.current = next;
      setState(next); setError('');
      return true;
    } catch {
      setError('Could not save this change. Browser storage may be full or unavailable. Your previous data is unchanged.');
      return false;
    }
  }
  if (!['dashboard', 'users', 'backup'].includes(activeModule)) return null;
  return <div className="admin-scroll"><div className="admin-page">
    {error && <p className="admin-error" role="alert">{error}</p>}
    {activeModule === 'dashboard' && <AdminDashboard state={state} commit={commit} onNavigate={onNavigate} />}
    {activeModule === 'users' && <UserManagement state={state} commit={commit} />}
    {activeModule === 'backup' && <BackupPage state={state} commit={commit} />}
  </div></div>;
}
