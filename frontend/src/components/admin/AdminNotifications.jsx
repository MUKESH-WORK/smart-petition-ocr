import { useEffect, useId, useMemo, useRef, useState } from 'react';
import { Bell, X } from 'lucide-react';
import { formatDate } from './adminModel';
import { getOfficerId } from '../../services/apiService';
import './AdminNotifications.css';

const ACTION_LABELS = {
  UPLOAD_PETITION: 'Uploaded a petition',
  EXTRACT_ENTITIES: 'Extracted petition details',
  AI_ANALYZE: 'Analysed a petition',
  UPDATE_DRAFT: 'Updated a petition draft',
  APPROVE_DRAFT: 'Approved a petition draft',
  APPROVE_AND_SUBMIT_PETITION: 'Approved and submitted a petition'
};

function auditNotification(record) {
  const action = ACTION_LABELS[record.action] || String(record.action || 'Activity recorded').replaceAll('_', ' ').toLowerCase();
  return {
    id: `server:${record.id}:${record.timestamp}`,
    detail: action,
    actor: record.officer_id || 'Petition processing',
    date: record.timestamp
  };
}

export default function AdminNotifications({ activity, petitionActivity }) {
  const [open, setOpen] = useState(false);
  const [serverActivity, setServerActivity] = useState([]);
  const [connection, setConnection] = useState('loading');
  const [readKey] = useState(() => {
    try { return `tn_admin_notifications_read:${getOfficerId()}`; }
    catch { return 'tn_admin_notifications_read:session'; }
  });
  const [readIds, setReadIds] = useState(() => {
    try {
      const saved = JSON.parse(sessionStorage.getItem(readKey) || '[]');
      return new Set(Array.isArray(saved) ? saved : []);
    } catch { return new Set(); }
  });
  const container = useRef(null);
  const trigger = useRef(null);
  const closeButton = useRef(null);
  const panelId = useId();

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
          headers: { 'X-Officer-Id': getOfficerId() }, signal: controller.signal
        });
        if (!response.ok) throw new Error('Activity unavailable');
        const records = await response.json();
        if (!Array.isArray(records)) throw new Error('Invalid activity');
        if (active) {
          setServerActivity(previous => [...new Map([...records.map(auditNotification), ...previous].map(item => [item.id, item])).values()]
            .sort((a, b) => new Date(b.date) - new Date(a.date)).slice(0, 100));
          setConnection('connected');
        }
      } catch {
        if (active) setConnection('unavailable');
      } finally { clearTimeout(timeout); inFlight = false; }
    }
    refresh();
    const interval = setInterval(refresh, 30000);
    document.addEventListener('visibilitychange', refresh);
    window.addEventListener('focus', refresh);
    return () => {
      active = false; controller?.abort(); clearInterval(interval);
      document.removeEventListener('visibilitychange', refresh);
      window.removeEventListener('focus', refresh);
    };
  }, []);

  const notifications = useMemo(() => {
    const local = activity.map(item => ({ ...item, id: `local:${item.id}`, actor: 'Admin · Local preview' }));
    // Session GDP events are immediately available; historical server actions come
    // from the audit endpoint, rather than treating petition history as new actions.
    const session = petitionActivity.filter(item => /^AUD-\d+$/.test(item.id)).map(item => ({
      id: `session:${item.id}`, detail: item.details, actor: 'GDP Assistant', date: item.timestamp
    }));
    return [...local, ...session, ...serverActivity].sort((a, b) => new Date(b.date) - new Date(a.date)).slice(0, 100);
  }, [activity, petitionActivity, serverActivity]);
  const unread = notifications.filter(item => !readIds.has(item.id)).length;
  function markRead(ids) {
    const next = new Set([...readIds, ...ids]);
    // Keep a bounded read history without dropping acknowledgements on each poll.
    const saved = [...next].slice(-500);
    setReadIds(new Set(saved));
    try { sessionStorage.setItem(readKey, JSON.stringify(saved)); } catch { /* In-memory read state still works. */ }
  }

  useEffect(() => {
    if (!open) return;
    closeButton.current?.focus();
    const outside = event => { if (!container.current?.contains(event.target)) setOpen(false); };
    const escape = event => {
      if (event.key === 'Escape') { setOpen(false); trigger.current?.focus(); }
    };
    document.addEventListener('pointerdown', outside);
    document.addEventListener('keydown', escape);
    return () => {
      document.removeEventListener('pointerdown', outside);
      document.removeEventListener('keydown', escape);
    };
  }, [open]);

  return <div className="admin-notifications" ref={container} onBlur={event => {
    if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false);
  }}>
    <button ref={trigger} className="admin-notification-bell" type="button" title="Notifications"
      aria-label={`Notifications${unread ? `, ${unread} unread` : ''}`} aria-expanded={open} aria-controls={open ? panelId : undefined}
      onClick={() => setOpen(!open)}>
      <Bell size={19} aria-hidden="true" />
      {unread > 0 && <span className="admin-notification-badge" aria-hidden="true">{unread > 99 ? '99+' : unread}</span>}
    </button>
    <span className="visually-hidden" role="status">{unread ? `${unread} unread notifications` : 'No unread notifications'}</span>
    {open && <section id={panelId} className="admin-notification-panel" aria-label="Notifications">
      <header><h2>Notifications</h2><button ref={closeButton} className="admin-notification-close" type="button" aria-label="Close notifications" onClick={() => { setOpen(false); trigger.current?.focus(); }}><X size={17} /></button></header>
      <div className="admin-notification-toolbar"><span>{unread} unread</span><button type="button" aria-disabled={!unread} onClick={() => { if (unread) markRead(notifications.map(item => item.id)); }}>Mark all as read</button></div>
      <ul>{notifications.map(item => <li key={item.id}>
        <button type="button" className={!readIds.has(item.id) ? 'is-unread' : ''} onClick={() => markRead([item.id])}
          aria-label={`${item.detail}. ${readIds.has(item.id) ? 'Read' : 'Unread, mark as read'}`}>
          <span className="admin-notification-dot" aria-hidden="true" />
          <span><strong>{item.detail}</strong><small>{item.actor}</small><time dateTime={item.date}>{formatDate(item.date)}</time></span>
        </button>
      </li>)}</ul>
      {!notifications.length && <p className="admin-notification-empty">{connection === 'loading' ? 'Loading activity…' : 'No notifications yet.'}</p>}
      <footer>{connection === 'unavailable' ? 'Live activity is unavailable. Local activity still appears here.' : 'Recent recorded activity · Refreshes every 30 seconds'}</footer>
    </section>}
  </div>;
}
