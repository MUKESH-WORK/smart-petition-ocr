import React from 'react';
import { Settings, X, Sliders, Shield, Database, Cpu, Check } from 'lucide-react';
import './HistoryModal.css';

export default function SettingsModal({ isOpen, onClose, onNotify }) {
  if (!isOpen) return null;

  const handleSave = () => {
    if (onNotify) onNotify('Preferences saved for current session');
    onClose();
  };

  return (
    <div className="modal-backdrop" onClick={onClose} role="dialog" aria-modal="true">
      <div className="modal-card history-modal-card" onClick={(e) => e.stopPropagation()}>
        
        <div className="modal-header">
          <div className="modal-title-group">
            <div className="modal-icon-badge navy-badge">
              <Settings size={18} />
            </div>
            <div>
              <h3 className="modal-title">Assistant Settings</h3>
              <p className="modal-subtitle">Configure OCR extraction and grievance mapping parameters</p>
            </div>
          </div>

          <button 
            type="button" 
            className="modal-close-btn" 
            onClick={onClose}
            aria-label="Close modal"
          >
            <X size={18} />
          </button>
        </div>

        <div className="modal-body-scroll">
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            
            {/* Setting Item 1 */}
            <div style={{ padding: '12px 14px', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-lg)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                <span style={{ fontSize: '0.88rem', fontWeight: 600, color: 'var(--text-primary)' }}>Language Recognition Engine</span>
                <span style={{ fontSize: '0.72rem', background: 'var(--bg-subtle)', color: '#102C57', padding: '2px 8px', borderRadius: '4px', fontWeight: 600, border: '1px solid var(--border-subtle)' }}>Tamil + English (Auto)</span>
              </div>
              <p style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>Automatically detects script and dialect used across Tamil Nadu revenue and grievance petitions.</p>
            </div>

            {/* Setting Item 2 */}
            <div style={{ padding: '12px 14px', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-lg)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                <span style={{ fontSize: '0.88rem', fontWeight: 600, color: 'var(--text-primary)' }}>Grievance Portal Target</span>
                <span style={{ fontSize: '0.72rem', background: '#F5EDE2', color: '#102C57', border: '1px solid #DAC0A3', padding: '2px 8px', borderRadius: '4px', fontWeight: 700 }}>TN e-District / Collectorate Cell</span>
              </div>
              <p style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>Orders extracted fields to match the official Monday Grievance Day portal entry schema.</p>
            </div>

            {/* Setting Item 3 */}
            <div style={{ padding: '12px 14px', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-lg)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                <span style={{ fontSize: '0.88rem', fontWeight: 600, color: '#102C57' }}>Confidence Highlighting</span>
                <span style={{ fontSize: '0.72rem', background: '#ECFDF5', color: '#047857', padding: '2px 8px', borderRadius: '4px', fontWeight: 600 }}>Active (&lt;95% highlighted)</span>
              </div>
              <p style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>Displays AI confidence chips only for fields requiring extra officer scrutiny.</p>
            </div>

          </div>
        </div>

        <div className="modal-footer">
          <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>Version 1.0 (UI Prototype)</span>
          <button type="button" className="primary-modal-btn" onClick={handleSave}>
            <Check size={14} />
            <span>Save Settings</span>
          </button>
        </div>

      </div>
    </div>
  );
}
