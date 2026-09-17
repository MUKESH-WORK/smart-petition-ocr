import { useEffect, useId, useRef } from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';

export default function AdminDialog({ title, onClose, children }) {
  const ref = useRef(null);
  const titleId = useId();
  useEffect(() => {
    const opener = document.activeElement;
    const dialog = ref.current;
    dialog.showModal();
    return () => {
      dialog.close();
      if (opener?.isConnected) opener.focus();
    };
  }, []);

  return createPortal(
    <dialog ref={ref} className="admin-dialog" aria-labelledby={titleId}
      onCancel={event => { event.preventDefault(); onClose(); }}>
      <header className="admin-dialog-header">
        <h2 id={titleId}>{title}</h2>
        <button type="button" className="admin-icon-button" aria-label="Close dialog" onClick={onClose}><X size={19} /></button>
      </header>
      <div className="admin-dialog-body">{children}</div>
    </dialog>, document.body
  );
}

export function DialogActions({ onClose, submitLabel, disabled = false }) {
  return <footer className="admin-dialog-actions">
    <button type="button" className="admin-button admin-button-secondary" onClick={onClose}>Cancel</button>
    <button type="submit" className="admin-button" disabled={disabled}>{submitLabel}</button>
  </footer>;
}
