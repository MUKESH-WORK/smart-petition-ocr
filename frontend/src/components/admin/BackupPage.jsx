import { useState } from 'react';
import AdminDialog, { DialogActions } from './AdminDialog';
import { createBackup, formatDate, restoreBackup, withActivity } from './adminModel';

export default function BackupPage({ state, commit }) {
  const [confirmation, setConfirmation] = useState(null);
  const [restoreText, setRestoreText] = useState('');
  const [error, setError] = useState('');
  const latest = state.backups[0];
  const restoring = Boolean(confirmation?.backup);
  function confirm(event) {
    event.preventDefault();
    if (restoring && restoreText !== 'RESTORE') return;
    const saved = restoring
      ? commit(previous => restoreBackup(previous, confirmation.backup))
      : commit(previous => withActivity({ ...previous, backups: [createBackup(previous), ...previous.backups] }, 'CREATE', 'Created a local admin backup.'));
    if (saved) { setConfirmation(null); setRestoreText(''); }
    else setError('Could not save this change. Browser storage is unavailable or full.');
  }
  function download(backup) {
    const blob = new Blob([JSON.stringify({ format: 'tn-admin-preview', version: 1, createdAt: backup.date, scope: 'Local admin accounts and configuration only; excludes passwords, petitions and server data.', ...backup.snapshot }, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url; link.download = `admin-preview-${backup.date.replaceAll(':', '-')}.json`;
    document.body.appendChild(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    commit(previous => withActivity(previous, 'DOWNLOAD', `Downloaded local backup from ${formatDate(backup.date)}.`));
  }
  return <>
    <header className="admin-page-header"><div><h1>Backup</h1><p>Manage system backups and restore points.</p></div></header>
    <p className="admin-note">Local preview · Backups contain only this tab’s admin accounts and configuration, excluding passwords. Server data and petitions are not included.</p>
    <section className="admin-panel">
      <h2>Backup Overview</h2>
      <dl className="admin-backup-overview">
        <div><dt>Last Backup</dt><dd>{latest ? formatDate(latest.date) : 'No backups yet'}</dd></div>
        <div><dt>Backup Status</dt><dd>{latest ? <span className="admin-status is-success">Completed</span> : 'Not created'}</dd></div>
        <div><dt>Backup Type</dt><dd>{latest?.type || '—'}</dd></div>
      </dl>
      <button type="button" className="admin-button" onClick={() => { setError(''); setConfirmation({}); }}>Create Backup</button>
    </section>
    <section className="admin-panel admin-backup-table"><h2>Recent Backups</h2>
      <div className="admin-table-scroll" tabIndex={0} role="region" aria-label="Recent backups table">
        <table className="admin-table"><thead><tr><th scope="col">Date / Time</th><th scope="col">Type</th><th scope="col">Status</th><th scope="col">Action</th></tr></thead>
          <tbody>{state.backups.map(backup => <tr key={backup.id}><td className="admin-date">{formatDate(backup.date)}</td><td>{backup.type}</td><td><span className="admin-status is-success">{backup.status}</span></td><td><div className="admin-inline-actions">
            <button type="button" className="admin-text-button" onClick={() => download(backup)}>Download</button>
            <button type="button" className="admin-text-button" onClick={() => { setError(''); setRestoreText(''); setConfirmation({ backup }); }}>Restore</button>
          </div></td></tr>)}</tbody>
        </table>
        {!state.backups.length && <p className="admin-empty">No backups yet. Create a backup to save a restore point.</p>}
      </div>
    </section>
    {confirmation && <AdminDialog title={restoring ? 'Restore Backup' : 'Create Backup'} onClose={() => setConfirmation(null)}>
      <form onSubmit={confirm}>
        <p className="admin-confirm-copy">{restoring ? `Replace all local admin accounts and configuration with the backup from ${formatDate(confirmation.backup.date)}? Changes made since that backup will be lost.` : 'Create a backup of the current local admin accounts and configuration?'}</p>
        <p className="admin-note">This affects only the preview in this browser tab. Server accounts, passwords and petitions are unaffected.</p>
        {restoring && <label className="admin-field">Type RESTORE to confirm<input autoComplete="off" value={restoreText} onChange={event => setRestoreText(event.target.value)} required /></label>}
        {error && <p className="admin-error" role="alert">{error}</p>}
        <DialogActions onClose={() => setConfirmation(null)} submitLabel={restoring ? 'Restore Backup' : 'Create Backup'} disabled={restoring && restoreText !== 'RESTORE'} />
      </form>
    </AdminDialog>}
  </>;
}
