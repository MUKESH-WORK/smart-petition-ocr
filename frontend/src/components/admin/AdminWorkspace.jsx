import { useEffect, useRef, useState, useCallback } from 'react';
import { AlertTriangle, RefreshCw, CheckCircle2 } from 'lucide-react';
import AdminDashboard from './AdminDashboard';
import UserManagement from './UserManagement';
import BackupPage from './BackupPage';
import { emptyAdminState, loadAdminState, STORAGE_KEY } from './adminModel';
import { fetchAdminUsers, fetchAdminActivity, checkDbHealth } from '../../services/apiService';
import './AdminWorkspace.css';

export default function AdminWorkspace({ activeModule, onNavigate, onActivityChange, currentLanguage = 'en' }) {
  const [initial] = useState(() => {
    try {
      return { state: loadAdminState(sessionStorage), error: '' };
    } catch {
      return { state: emptyAdminState(), error: '' };
    }
  });

  const [state, setState] = useState(initial.state);
  const stateRef = useRef(state);
  const [error, setError] = useState('');

  // Live Database State
  const [dbUsers, setDbUsers] = useState([]);
  const [loadingUsers, setLoadingUsers] = useState(true);
  const [dbActivity, setDbActivity] = useState([]);
  const [dbHealth, setDbHealth] = useState(null);
  const [reconnecting, setReconnecting] = useState(false);

  // Synchronize users and activity from backend DB
  const refreshUsers = useCallback(async () => {
    setLoadingUsers(true);
    try {
      const data = await fetchAdminUsers();
      const userList = Array.isArray(data) ? data : (data?.users || []);
      setDbUsers(userList);
      setState(prev => ({ ...prev, users: userList }));
      stateRef.current = { ...stateRef.current, users: userList };
      setError('');
    } catch (err) {
      console.warn('Could not load users from database:', err);
      setError('Database error: Unable to load official user accounts.');
    } finally {
      setLoadingUsers(false);
    }
  }, []);

  const refreshActivity = useCallback(async () => {
    try {
      const logs = await fetchAdminActivity(50);
      if (Array.isArray(logs) && logs.length > 0) {
        setDbActivity(logs);
        setState(prev => ({ ...prev, activity: logs }));
        stateRef.current = { ...stateRef.current, activity: logs };
      }
    } catch (err) {
      console.debug('Activity refresh note:', err);
    }
  }, []);

  const checkHealth = useCallback(async () => {
    try {
      const health = await checkDbHealth();
      setDbHealth(health);
      return health;
    } catch (err) {
      setDbHealth({
        status: 'disconnected',
        user_db: { status: 'disconnected', error: err.message },
        admin_db: { status: 'disconnected', error: err.message }
      });
      return null;
    }
  }, []);

  const reconnectDb = useCallback(async () => {
    setReconnecting(true);
    const health = await checkHealth();
    if (health?.status !== 'disconnected') {
      await refreshUsers();
      await refreshActivity();
    }
    setReconnecting(false);
  }, [checkHealth, refreshUsers, refreshActivity]);

  // Initial load and periodic health monitoring
  useEffect(() => {
    refreshUsers();
    refreshActivity();
    checkHealth();

    const healthInterval = setInterval(() => {
      checkHealth();
    }, 25000);

    return () => clearInterval(healthInterval);
  }, [refreshUsers, refreshActivity, checkHealth]);

  useEffect(() => {
    onActivityChange?.(state.activity);
  }, [state.activity, onActivityChange]);

  function commit(update) {
    try {
      const next = update(stateRef.current);
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      stateRef.current = next;
      setState(next);
      return true;
    } catch {
      setError('Could not save this local setting. Browser storage may be full or unavailable.');
      return false;
    }
  }

  if (!['dashboard', 'users', 'backup'].includes(activeModule)) return null;

  const isDbDisconnected = dbHealth?.status === 'disconnected' || dbHealth?.admin_db?.status === 'disconnected';

  return (
    <div className="admin-scroll">
      <div className="admin-page">
        {/* Persistent Database Health Alert Banner */}
        {isDbDisconnected && (
          <div className="admin-db-banner is-disconnected" role="alert">
            <div className="admin-db-banner-left">
              <AlertTriangle size={20} />
              <div>
                <strong>Database Disconnected:</strong> Live connection to Government Database is currently unavailable.
                {dbHealth?.admin_db?.error && <span style={{ opacity: 0.8, display: 'block', fontSize: '0.8rem' }}>Error: {dbHealth.admin_db.error}</span>}
              </div>
            </div>
            <button
              type="button"
              className="admin-reconnect-btn"
              onClick={reconnectDb}
              disabled={reconnecting}
            >
              {reconnecting ? 'Reconnecting…' : 'Reconnect Now'}
            </button>
          </div>
        )}

        {error && <p className="admin-error" role="alert">{error}</p>}

        {activeModule === 'dashboard' && (
          <AdminDashboard
            state={{ ...state, users: dbUsers, activity: dbActivity.length ? dbActivity : state.activity }}
            dbHealth={dbHealth}
            commit={commit}
            onNavigate={onNavigate}
            currentLanguage={currentLanguage}
          />
        )}

        {activeModule === 'users' && (
          <UserManagement
            users={dbUsers}
            loading={loadingUsers}
            dbHealth={dbHealth}
            onRefreshUsers={refreshUsers}
            onReconnectDb={reconnectDb}
            currentLanguage={currentLanguage}
          />
        )}

        {activeModule === 'backup' && (
          <BackupPage
            state={{ ...state, users: dbUsers, activity: dbActivity }}
            commit={commit}
            currentLanguage={currentLanguage}
          />
        )}
      </div>
    </div>
  );
}
