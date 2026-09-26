import { useEffect, useId, useMemo, useRef, useState, useCallback } from 'react';
import { Bell, X, CheckCheck } from 'lucide-react';
import { formatDate } from './adminModel';
import { getOfficerId } from '../../services/apiService';
import './AdminNotifications.css';

const ACTION_LABELS = {
  UPLOAD_PETITION: 'Uploaded a petition',
  EXTRACT_ENTITIES: 'Extracted petition details',
  AI_ANALYZE: 'Analysed a petition',
  UPDATE_DRAFT: 'Updated a petition draft',
  APPROVE_DRAFT: 'Approved a petition draft',
  APPROVE_AND_SUBMIT_PETITION: 'Approved and submitted a petition',
  SECURITY_AUTH: 'Security & Authentication update',
  DATABASE_BACKUP: 'Database backup created',
  USER_STATUS_UPDATE: 'User account status updated'
};

function auditNotification(record) {
  const action = ACTION_LABELS[record.action] || String(record.action || 'Activity recorded').replaceAll('_', ' ').toLowerCase();
  return {
    id: `server:${record.id}:${record.timestamp}`,
    detail: action,
    actor: record.officer_id || 'System / Officer',
    date: record.timestamp
  };
}

export default function AdminNotifications({ activity = [], petitionActivity = [] }) {
  const [open, setOpen] = useState(false);
  const [serverActivity, setServerActivity] = useState([]);
  const [connection, setConnection] = useState('loading');
  
  const officerId = useMemo(() => {
    try {
      return getOfficerId() || 'admin_default';
    } catch {
      return 'admin_default';
    }
  }, []);

  const readStorageKey = `tn_admin_notifs_read_${officerId}`;
  const watermarkStorageKey = `tn_admin_notifs_watermark_${officerId}`;

  // 1. Persistent Set of Read IDs
  const [readIds, setReadIds] = useState(() => {
    try {
      // Check localStorage first
      let saved = localStorage.getItem(readStorageKey);
      if (!saved) {
        // Fallback / migrate from legacy sessionStorage
        saved = sessionStorage.getItem(`tn_admin_notifications_read:${officerId}`) || sessionStorage.getItem('tn_admin_notifications_read:session');
      }
      const parsed = JSON.parse(saved || '[]');
      return new Set(Array.isArray(parsed) ? parsed : []);
    } catch {
      return new Set();
    }
  });

  // 2. Persistent Watermark (Timestamp ms) - past events before this timestamp are considered already acknowledged
  const [watermark, setWatermark] = useState(() => {
    try {
      const saved = localStorage.getItem(watermarkStorageKey);
      if (saved) {
        const num = Number(saved);
        if (!isNaN(num) && num > 0) return num;
      }
      // On brand new session with no existing watermark, establish baseline as Date.now()
      const now = Date.now();
      localStorage.setItem(watermarkStorageKey, String(now));
      return now;
    } catch {
      return Date.now();
    }
  });

  const container = useRef(null);
  const trigger = useRef(null);
  const closeButton = useRef(null);
  const panelId = useId();

  // Polling server audit logs
  useEffect(() => {
    let active = true;
    let inFlight = false;
    let controller;

    async function refresh() {
      if (inFlight || document.hidden) return;
      inFlight = true;
      controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 10000);
      try {
        const response = await fetch('/api/v1/admin/audit-logs?limit=100', {
          headers: { 'X-Officer-Id': getOfficerId() },
          signal: controller.signal
        });
        if (!response.ok) throw new Error('Activity unavailable');
        const records = await response.json();
        if (!Array.isArray(records)) throw new Error('Invalid activity');
        if (active) {
          setServerActivity(previous => {
            const merged = new Map([...records.map(auditNotification), ...previous].map(item => [item.id, item]));
            return [...merged.values()]
              .sort((a, b) => new Date(b.date) - new Date(a.date))
              .slice(0, 100);
          });
          setConnection('connected');
        }
      } catch {
        if (active) setConnection('unavailable');
      } finally {
        clearTimeout(timeout);
        inFlight = false;
      }
    }

    refresh();
    const interval = setInterval(refresh, 30000);
    document.addEventListener('visibilitychange', refresh);
    window.addEventListener('focus', refresh);
    return () => {
      active = false;
      controller?.abort();
      clearInterval(interval);
      document.removeEventListener('visibilitychange', refresh);
      window.removeEventListener('focus', refresh);
    };
  }, []);

  // Consolidate notifications from local actions, GDP workspace actions, and server audit records
  const notifications = useMemo(() => {
    const local = (activity || []).map(item => ({ ...item, id: `local:${item.id}`, actor: 'Admin · Local action' }));
    const session = (petitionActivity || []).filter(item => /^AUD-\d+$/.test(item.id)).map(item => ({
      id: `session:${item.id}`, detail: item.details, actor: 'GDP Assistant', date: item.timestamp
    }));
    return [...local, ...session, ...serverActivity]
      .sort((a, b) => new Date(b.date) - new Date(a.date))
      .slice(0, 100);
  }, [activity, petitionActivity, serverActivity]);

  // Determine whether an item is unread
  const isUnread = useCallback((item) => {
    if (readIds.has(item.id)) return false;
    if (!item.date) return false;
    const itemTime = new Date(item.date).getTime();
    if (isNaN(itemTime)) return false;
    // An item is unread ONLY if it occurred AFTER the last acknowledged watermark AND is not in readIds
    return itemTime > watermark;
  }, [readIds, watermark]);

  const unreadCount = useMemo(() => {
    return notifications.filter(isUnread).length;
  }, [notifications, isUnread]);

  const markRead = useCallback((ids) => {
    setReadIds(prev => {
      const next = new Set([...prev, ...ids]);
      const saved = [...next].slice(-1000);
      try {
        localStorage.setItem(readStorageKey, JSON.stringify(saved));
      } catch (err) {
        console.warn('Could not save read notifications to localStorage:', err);
      }
      return new Set(saved);
    });
  }, [readStorageKey]);

  const markAllAsRead = useCallback(() => {
    const now = Date.now();
    setWatermark(now);
    try {
      localStorage.setItem(watermarkStorageKey, String(now));
    } catch (err) {
      console.warn('Could not update notification watermark in localStorage:', err);
    }
    const allIds = notifications.map(item => item.id);
    markRead(allIds);
  }, [notifications, markRead, watermarkStorageKey]);

  useEffect(() => {
    if (!open) return;
    closeButton.current?.focus();
    const outside = event => {
      if (!container.current?.contains(event.target)) setOpen(false);
    };
    const escape = event => {
      if (event.key === 'Escape') {
        setOpen(false);
        trigger.current?.focus();
      }
    };
    document.addEventListener('pointerdown', outside);
    document.addEventListener('keydown', escape);
    return () => {
      document.removeEventListener('pointerdown', outside);
      document.removeEventListener('keydown', escape);
    };
  }, [open]);

  return (
    <div
      className="admin-notifications"
      ref={container}
      onBlur={event => {
        if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false);
      }}
    >
      <button
        ref={trigger}
        className="admin-notification-bell"
        type="button"
        title="Notifications"
        aria-label={`Notifications${unreadCount ? `, ${unreadCount} unread` : ''}`}
        aria-expanded={open}
        aria-controls={open ? panelId : undefined}
        onClick={() => setOpen(!open)}
      >
        <Bell size={19} aria-hidden="true" />
        {unreadCount > 0 && (
          <span className="admin-notification-badge" aria-hidden="true">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      <span className="visually-hidden" role="status">
        {unreadCount ? `${unreadCount} unread notifications` : 'No unread notifications'}
      </span>

      {open && (
        <section id={panelId} className="admin-notification-panel" aria-label="Notifications">
          <header>
            <h2>Notifications</h2>
            <button
              ref={closeButton}
              className="admin-notification-close"
              type="button"
              aria-label="Close notifications"
              onClick={() => {
                setOpen(false);
                trigger.current?.focus();
              }}
            >
              <X size={17} />
            </button>
          </header>

          <div className="admin-notification-toolbar">
            <span>{unreadCount} unread</span>
            <button
              type="button"
              aria-disabled={!unreadCount}
              onClick={() => {
                if (unreadCount || notifications.length > 0) markAllAsRead();
              }}
              style={{ cursor: unreadCount ? 'pointer' : 'default' }}
            >
              Mark all as read
            </button>
          </div>

          <ul>
            {notifications.map(item => {
              const unread = isUnread(item);
              return (
                <li key={item.id}>
                  <button
                    type="button"
                    className={unread ? 'is-unread' : ''}
                    onClick={() => markRead([item.id])}
                    aria-label={`${item.detail}. ${unread ? 'Unread, click to mark read' : 'Read'}`}
                  >
                    <span className="admin-notification-dot" aria-hidden="true" />
                    <span>
                      <strong>{item.detail}</strong>
                      <small>{item.actor}</small>
                      <time dateTime={item.date}>{formatDate(item.date)}</time>
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>

          {!notifications.length && (
            <p className="admin-notification-empty">
              {connection === 'loading' ? 'Loading activity…' : 'No notifications yet.'}
            </p>
          )}

          <footer>
            {connection === 'unavailable'
              ? 'Live activity is unavailable. Local activity still appears here.'
              : 'Recent recorded activity · Refreshes every 30 seconds'}
          </footer>
        </section>
      )}
    </div>
  );
}

