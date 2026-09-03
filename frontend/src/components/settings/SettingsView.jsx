import React from 'react';
import { Settings, Shield, Database, Cpu, Check } from 'lucide-react';
import '../audit/AuditLogs.css';

export default function SettingsView({ onNotify }) {
  const handleSave = () => {
    if (onNotify) onNotify('Preferences saved for current session');
  };

  return (
    <div className="audit-logs-page" role="region" aria-label="Administrative Settings">
      <div className="audit-logs-container">
        
        {/* Page Header */}
        <div className="audit-page-header">
          <div className="audit-title-group">
            <h2 className="audit-page-title">Administrative Settings</h2>
            <p className="audit-page-subtext">Configure OCR extraction and grievance processing parameters.</p>
          </div>

          <div className="audit-header-actions">
            <button 
              type="button" 
              className="clear-filters-btn"
              onClick={handleSave}
              style={{ backgroundColor: 'var(--navy-900)', color: '#FFFFFF', borderColor: 'var(--navy-900)' }}
            >
              Save Settings
            </button>
          </div>
        </div>

        {/* Settings Cards List */}
        <div className="audit-records-section">
          
          <div className="audit-record-card" style={{ cursor: 'default' }}>
            <div className="record-main-col">
              <div className="record-doc-icon-box">
                <Cpu size={18} />
              </div>
              <div className="record-text-details">
                <div className="record-title-row">
                  <span className="record-file-name">Language Recognition Engine</span>
                  <span className="record-id-badge font-mono">Auto-Detect</span>
                </div>
                <div className="record-summary-text">
                  Automatically detects Tamil and English script across Tamil Nadu revenue, land administration, and collectorate grievance petitions.
                </div>
              </div>
            </div>
            <div className="record-right-col">
              <span className="record-status-pill">Tamil + English (Active)</span>
            </div>
          </div>

          <div className="audit-record-card" style={{ cursor: 'default' }}>
            <div className="record-main-col">
              <div className="record-doc-icon-box">
                <Database size={18} />
              </div>
              <div className="record-text-details">
                <div className="record-title-row">
                  <span className="record-file-name">Grievance Portal Target Schema</span>
                  <span className="record-id-badge font-mono">e-District Portal</span>
                </div>
                <div className="record-summary-text">
                  Aligns document understanding and summaries to match official Monday Grievance Day administrative schema for swift portal data entry.
                </div>
              </div>
            </div>
            <div className="record-right-col">
              <span className="record-status-pill">TN e-District / Collectorate Cell</span>
            </div>
          </div>

          <div className="audit-record-card" style={{ cursor: 'default' }}>
            <div className="record-main-col">
              <div className="record-doc-icon-box">
                <Shield size={18} />
              </div>
              <div className="record-text-details">
                <div className="record-title-row">
                  <span className="record-file-name">Verification & Security</span>
                  <span className="record-id-badge font-mono">Session Isolation</span>
                </div>
                <div className="record-summary-text">
                  All uploaded scanned documents remain strictly in local memory and are cleared when a new petition or session ends.
                </div>
              </div>
            </div>
            <div className="record-right-col">
              <span className="record-status-pill">Local Memory Protected</span>
            </div>
          </div>

        </div>

      </div>
    </div>
  );
}
