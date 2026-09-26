import { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Database,
  Download,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  HardDrive,
  Layers
} from 'lucide-react';
import {
  fetchDatabaseBackups,
  createDatabaseBackup,
  fetchAuditReportData,
  getBackupDownloadUrl,
  downloadServerReport
} from '../../services/apiService';
import GovernmentReportPrintModal from './GovernmentReportPrintModal';
import { getTranslation } from '../../utils/translations';

export default function BackupPage({ currentLanguage = 'en' }) {
  const [backups, setBackups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [reportData, setReportData] = useState(null);
  const [feedback, setFeedback] = useState(null);
  const [isPrintModalOpen, setIsPrintModalOpen] = useState(false);

  // Active Report Generation Config
  const [selectedTemplate, setSelectedTemplate] = useState('officer_performance');
  const [selectedOfficerId, setSelectedOfficerId] = useState('all');
  const [selectedPetitionId, setSelectedPetitionId] = useState('');
  const [exportFormat, setExportFormat] = useState('pdf'); // 'pdf' | 'docx'
  const [petitionSearchQuery, setPetitionSearchQuery] = useState('');

  // Clear feedback after 6 seconds
  useEffect(() => {
    if (feedback) {
      const timer = setTimeout(() => setFeedback(null), 6000);
      return () => clearTimeout(timer);
    }
  }, [feedback]);

  // Load backups and report data
  const loadBackupData = useCallback(async () => {
    setLoading(true);
    try {
      const [backupList, rData] = await Promise.all([
        fetchDatabaseBackups().catch(() => []),
        fetchAuditReportData().catch(() => null)
      ]);
      setBackups(backupList);
      if (rData) {
        setReportData(rData);
        if (rData.petitionProcessingHistory && rData.petitionProcessingHistory.length > 0 && !selectedPetitionId) {
          setSelectedPetitionId(rData.petitionProcessingHistory[0].id || rData.petitionProcessingHistory[0].petitionNumber);
        }
      }
    } catch (err) {
      console.warn('Backup data load warning:', err);
    } finally {
      setLoading(false);
    }
  }, [selectedPetitionId]);

  useEffect(() => {
    loadBackupData();
  }, [loadBackupData]);

  // Create new live database backup snapshot with accidental data loss protection
  const handleCreateBackup = async () => {
    setIsCreating(true);
    setFeedback(null);
    try {
      const newBackup = await createDatabaseBackup();
      setFeedback({
        type: 'success',
        message: `Database backup snapshot "${newBackup.fileName || newBackup.id}" created successfully. Preserved ${newBackup.totalRecords || 0} records across ${newBackup.tables?.length || 0} tables.`
      });
      await loadBackupData();
    } catch (err) {
      setFeedback({
        type: 'error',
        message: err.message || 'Failed to create database backup snapshot.'
      });
    } finally {
      setIsCreating(false);
    }
  };

  // Direct download JSON backup snapshot
  const handleDownloadBackup = (backup) => {
    window.open(getBackupDownloadUrl(backup.fileName || backup.id), '_blank');
  };

  // Execute Official Document Generation (100% Backend Compiled)
  const handleGenerateReport = async () => {
    setIsExporting(true);
    setFeedback(null);

    try {
      const filename = await downloadServerReport({
        template: selectedTemplate,
        format: exportFormat,
        officerId: selectedOfficerId,
        petitionId: selectedPetitionId
      });

      setFeedback({
        type: 'success',
        message: `Official Document "${filename}" generated and downloaded from server successfully.`
      });
    } catch (err) {
      setFeedback({
        type: 'error',
        message: err.message || 'Failed to generate official document from server.'
      });
    } finally {
      setIsExporting(false);
    }
  };


  const meta = reportData?.reportMetadata || {};
  const officers = reportData?.officersDirectory || [];
  const petitions = reportData?.petitionProcessingHistory || [];
  const latestBackup = backups[0];

  const filteredPetitionsForSelect = useMemo(() => {
    if (!petitionSearchQuery.trim()) return petitions;
    const q = petitionSearchQuery.toLowerCase();
    return petitions.filter(p =>
      (p.petitionNumber && p.petitionNumber.toLowerCase().includes(q)) ||
      (p.applicantName && p.applicantName.toLowerCase().includes(q)) ||
      (p.department && p.department.toLowerCase().includes(q)) ||
      (p.mobile && p.mobile.includes(q))
    );
  }, [petitions, petitionSearchQuery]);

  const selectedPetitionObj = useMemo(() => {
    return petitions.find(p => String(p.id) === String(selectedPetitionId) || String(p.petitionNumber) === String(selectedPetitionId)) || petitions[0];
  }, [petitions, selectedPetitionId]);

  return (
    <div className="admin-page backup-management-page" role="region" aria-label="Database Backup and Document Reporting Center">

      {/* 1. PAGE HEADER */}
      <header className="admin-page-header">
        <div>
          <h1>{getTranslation(currentLanguage, 'backupTitle', 'Database Backup & Document Reporting Center')}</h1>
          <p>{getTranslation(currentLanguage, 'backupSubtitle', 'Authoritative database backup snapshots, accidental data loss safeguards, and certified government reports.')}</p>
        </div>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
          <button
            type="button"
            className="admin-button admin-button-secondary"
            onClick={loadBackupData}
            disabled={loading}
            title="Refresh Backups"
            style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
          >
            <RefreshCw size={14} className={loading ? 'spin-icon' : ''} />
            <span>{getTranslation(currentLanguage, 'refresh', 'Refresh')}</span>
          </button>

          <button
            type="button"
            className="admin-button admin-button-secondary"
            onClick={handleCreateBackup}
            disabled={isCreating}
            style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
          >
            {isCreating ? <RefreshCw size={14} className="spin-icon" /> : <HardDrive size={14} />}
            <span>{isCreating ? 'Creating Snapshot…' : 'Create DB Snapshot'}</span>
          </button>
        </div>
      </header>

      {/* FEEDBACK ALERT */}
      {feedback && (
        <div
          role="status"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            padding: '12px 16px',
            borderRadius: '8px',
            marginBottom: '16px',
            fontSize: '0.88rem',
            background: feedback.type === 'success' ? '#F0FDF4' : '#FEF2F2',
            border: `1px solid ${feedback.type === 'success' ? '#BBF7D0' : '#FECACA'}`,
            color: feedback.type === 'success' ? '#166534' : '#991B1B'
          }}
        >
          {feedback.type === 'success' ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
          <span>{feedback.message}</span>
        </div>
      )}

      {/* 2. OVERVIEW KPI CARDS */}
      <section className="admin-panel" style={{ marginBottom: '20px' }}>
        <h2 style={{ fontSize: '1rem', fontWeight: 600, margin: '0 0 14px', color: '#0F172A' }}>
          System Data & Registry Overview
        </h2>
        <dl style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '12px', margin: 0 }}>
          <div style={{ padding: '12px 14px', background: '#F8FAFC', borderRadius: '6px', border: '1px solid #E2E8F0' }}>
            <dt style={{ fontSize: '0.8rem', color: '#64748B', margin: 0 }}>Available DB Backups</dt>
            <dd style={{ fontSize: '1.25rem', fontWeight: 700, color: '#102C57', margin: '4px 0 0' }}>
              {backups.length}
            </dd>
          </div>

          <div style={{ padding: '12px 14px', background: '#F8FAFC', borderRadius: '6px', border: '1px solid #E2E8F0' }}>
            <dt style={{ fontSize: '0.8rem', color: '#64748B', margin: 0 }}>Latest Snapshot</dt>
            <dd style={{ fontSize: '0.88rem', fontWeight: 600, color: '#334155', margin: '6px 0 0' }}>
              {latestBackup ? new Date(latestBackup.createdAt).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' }) : 'None on record'}
            </dd>
          </div>

          <div style={{ padding: '12px 14px', background: '#F8FAFC', borderRadius: '6px', border: '1px solid #E2E8F0' }}>
            <dt style={{ fontSize: '0.8rem', color: '#64748B', margin: 0 }}>Registered Officials</dt>
            <dd style={{ fontSize: '1.25rem', fontWeight: 700, color: '#102C57', margin: '4px 0 0' }}>
              {meta.totalOfficers ?? officers.length} Officers
            </dd>
          </div>

          <div style={{ padding: '12px 14px', background: '#F8FAFC', borderRadius: '6px', border: '1px solid #E2E8F0' }}>
            <dt style={{ fontSize: '0.8rem', color: '#64748B', margin: 0 }}>Petitions in Registry</dt>
            <dd style={{ fontSize: '1.25rem', fontWeight: 700, color: '#102C57', margin: '4px 0 0' }}>
              {meta.totalPetitions ?? petitions.length} Petitions
            </dd>
          </div>
        </dl>
      </section>

      {/* 3. OFFICIAL GOVERNMENT DOCUMENT REPORTING STUDIO */}
      <section className="admin-panel" style={{ marginBottom: '20px' }}>
        <h2 style={{ fontSize: '1rem', fontWeight: 600, margin: '0 0 12px', color: '#0F172A' }}>
          Official Government Document & Report Generator
        </h2>

        {/* TEMPLATE SELECTOR TABS (CLEAN SEGMENTED CONTROL) */}
        <div
          role="tablist"
          aria-label="Report Templates"
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
            gap: '8px',
            marginBottom: '14px'
          }}
        >
          {[
            { id: 'officer_performance', label: '1. Officer Performance & Counts' },
            { id: 'audit_logs', label: '2. Audit Log History Trail' },
            { id: 'single_petition', label: '3. Petition Full Form Dossier' },
            { id: 'intake_report', label: '4. Total Petitions Received Report' }
          ].map((item) => {
            const isSelected = selectedTemplate === item.id;
            return (
              <button
                key={item.id}
                type="button"
                role="tab"
                aria-selected={isSelected}
                onClick={() => setSelectedTemplate(item.id)}
                style={{
                  padding: '9px 12px',
                  borderRadius: '6px',
                  border: isSelected ? '1px solid #102C57' : '1px solid #CBD5E1',
                  background: isSelected ? '#102C57' : '#FFFFFF',
                  color: isSelected ? '#FFFFFF' : '#334155',
                  fontSize: '0.82rem',
                  fontWeight: isSelected ? 600 : 500,
                  cursor: 'pointer',
                  textAlign: 'center',
                  transition: 'background 0.15s ease, color 0.15s ease, border-color 0.15s ease'
                }}
              >
                {item.label}
              </button>
            );
          })}
        </div>

        {/* TEMPLATE SPECIFIC FILTERS & CONTROLS */}
        <div style={{ background: '#F8FAFC', padding: '14px 16px', borderRadius: '6px', border: '1px solid #E2E8F0' }}>

          {/* Officer Filter (For Templates 1 and 2) */}
          {(selectedTemplate === 'officer_performance' || selectedTemplate === 'audit_logs') && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
              <label htmlFor="officer-select-filter" style={{ fontSize: '0.82rem', fontWeight: 600, color: '#334155', whiteSpace: 'nowrap' }}>
                Filter by Officer:
              </label>
              <select
                id="officer-select-filter"
                value={selectedOfficerId}
                onChange={(e) => setSelectedOfficerId(e.target.value)}
                style={{
                  height: '36px',
                  padding: '0 10px',
                  borderRadius: '6px',
                  border: '1px solid #CBD5E1',
                  background: '#FFFFFF',
                  fontSize: '0.82rem',
                  maxWidth: '380px'
                }}
              >
                <option value="all">All Officers & System Events</option>
                {officers.map(off => (
                  <option key={off.id} value={off.id}>
                    {off.id} — {off.name} ({off.department})
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Petition Selector (For Template 3: Single Petition Dossier) */}
          {selectedTemplate === 'single_petition' && (
            <div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <label htmlFor="petition-select-dropdown" style={{ fontSize: '0.82rem', fontWeight: 600, color: '#334155' }}>
                  Select Grievance Petition:
                </label>
                <div style={{ display: 'grid', gridTemplateColumns: 'minmax(180px, 240px) 1fr', gap: '8px', alignItems: 'center' }}>
                  <input
                    id="petition-search-input"
                    type="text"
                    placeholder="Search applicant / ID…"
                    value={petitionSearchQuery}
                    onChange={(e) => setPetitionSearchQuery(e.target.value)}
                    style={{
                      height: '36px',
                      padding: '0 10px',
                      fontSize: '0.82rem',
                      borderRadius: '6px',
                      border: '1px solid #CBD5E1',
                      background: '#FFFFFF'
                    }}
                  />
                  <select
                    id="petition-select-dropdown"
                    value={selectedPetitionId}
                    onChange={(e) => setSelectedPetitionId(e.target.value)}
                    style={{
                      height: '36px',
                      padding: '0 10px',
                      borderRadius: '6px',
                      border: '1px solid #CBD5E1',
                      background: '#FFFFFF',
                      fontSize: '0.82rem',
                      width: '100%'
                    }}
                  >
                    {filteredPetitionsForSelect.map(p => (
                      <option key={p.id || p.petitionNumber} value={p.id || p.petitionNumber}>
                        {p.petitionNumber} — {p.applicantName} ({p.department} · {p.category}) [{p.status}]
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Selected Petition Summary Block */}
              {selectedPetitionObj && (
                <div
                  style={{
                    marginTop: '10px',
                    padding: '8px 12px',
                    background: '#FFFFFF',
                    borderRadius: '6px',
                    border: '1px solid #E2E8F0',
                    fontSize: '0.8rem',
                    color: '#475569',
                    display: 'flex',
                    gap: '16px',
                    flexWrap: 'wrap',
                    alignItems: 'center'
                  }}
                >
                  <span style={{ fontWeight: 600, color: '#0F172A' }}>
                    {selectedPetitionObj.petitionNumber} — {selectedPetitionObj.applicantName}
                  </span>
                  <span>Mobile: {selectedPetitionObj.mobile || '—'}</span>
                  <span>Taluk: {selectedPetitionObj.taluk || '—'}</span>
                  <span>Department: {selectedPetitionObj.department || '—'}</span>
                  <span>Category: {selectedPetitionObj.category || '—'}</span>
                  <span style={{ marginLeft: 'auto', fontWeight: 600, color: '#0F172A' }}>
                    Status: {selectedPetitionObj.status || '—'}
                  </span>
                </div>
              )}
            </div>
          )}

          {/* Template 4: Total Petitions Info */}
          {selectedTemplate === 'intake_report' && (
            <p style={{ margin: 0, fontSize: '0.82rem', color: '#475569' }}>
              <strong>Aggregation Scope:</strong> All 21 intake channels across 10 taluks of Erode District.
            </p>
          )}

          {/* Export Format Selector & Action Buttons */}
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginTop: '14px',
              paddingTop: '12px',
              borderTop: '1px solid #E2E8F0',
              flexWrap: 'wrap',
              gap: '12px'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
              <span style={{ fontSize: '0.82rem', fontWeight: 600, color: '#334155' }}>Export Format:</span>

              <label style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', cursor: 'pointer', fontSize: '0.82rem', color: '#334155' }}>
                <input
                  type="radio"
                  name="exportFormat"
                  value="pdf"
                  checked={exportFormat === 'pdf'}
                  onChange={() => setExportFormat('pdf')}
                  style={{ width: '15px', height: '15px', margin: 0 }}
                />
                <span>PDF Document (.pdf)</span>
              </label>

              <label style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', cursor: 'pointer', fontSize: '0.82rem', color: '#334155' }}>
                <input
                  type="radio"
                  name="exportFormat"
                  value="docx"
                  checked={exportFormat === 'docx'}
                  onChange={() => setExportFormat('docx')}
                  style={{ width: '15px', height: '15px', margin: 0 }}
                />
                <span>Word Document (.docx)</span>
              </label>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <button
                type="button"
                className="admin-button admin-button-secondary"
                onClick={() => setIsPrintModalOpen(true)}
                disabled={loading || !reportData}
                style={{
                  height: '36px',
                  padding: '0 14px',
                  fontSize: '0.82rem',
                  fontWeight: 600
                }}
              >
                Preview / Print PDF
              </button>

              <button
                type="button"
                className="admin-button"
                onClick={handleGenerateReport}
                disabled={isExporting || loading}
                style={{
                  height: '36px',
                  padding: '0 16px',
                  fontSize: '0.82rem',
                  fontWeight: 600
                }}
              >
                {isExporting ? 'Generating Document…' : `Download ${exportFormat.toUpperCase()} Document`}
              </button>
            </div>
          </div>

        </div>
      </section>

      {/* 4. RECENT DATABASE SNAPSHOTS TABLE */}
      <section className="admin-panel admin-backup-table">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
          <h2 style={{ margin: 0, fontSize: '1.05rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Layers size={18} style={{ color: '#102C57' }} />
            <span>Authoritative Database Backups</span>
          </h2>
          <span style={{ fontSize: '0.82rem', color: '#64748B' }}>
            {backups.length} snapshot{backups.length === 1 ? '' : 's'} recorded on server
          </span>
        </div>

        <div className="admin-table-scroll" tabIndex={0} role="region" aria-label="Recent database backups table">
          <table className="admin-table">
            <thead>
              <tr>
                <th scope="col" style={{ width: '260px' }}>Backup Snapshot File</th>
                <th scope="col" style={{ width: '180px' }}>Created Date & Time</th>
                <th scope="col" style={{ width: '120px' }}>Total Records</th>
                <th scope="col" style={{ width: '110px' }}>File Size</th>
                <th scope="col" style={{ width: '120px' }}>Status</th>
                <th scope="col" style={{ textAlign: 'right', paddingRight: '20px' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {backups.map((backup) => (
                <tr key={backup.id}>
                  <td style={{ fontWeight: 600, color: '#102C57' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <Database size={15} style={{ color: '#64748B', flexShrink: 0 }} />
                      <span style={{ fontFamily: 'monospace', fontSize: '0.82rem' }}>{backup.fileName || backup.id}</span>
                    </div>
                  </td>
                  <td className="admin-date">
                    {new Date(backup.createdAt).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'medium' })}
                  </td>
                  <td>
                    <strong>{backup.totalRecords || 0}</strong> records
                  </td>
                  <td>
                    {backup.sizeFormatted || `${backup.sizeBytes} B`}
                  </td>
                  <td>
                    <span className="admin-status is-success" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                      <CheckCircle2 size={11} /> {backup.status || 'Completed'}
                    </span>
                  </td>
                  <td style={{ textAlign: 'right', paddingRight: '16px' }}>
                    <button
                      type="button"
                      className="admin-button admin-button-secondary"
                      style={{ padding: '4px 12px', fontSize: '0.78rem', display: 'inline-flex', alignItems: 'center', gap: '5px' }}
                      onClick={() => handleDownloadBackup(backup)}
                      title={`Download snapshot ${backup.fileName || backup.id}`}
                    >
                      <Download size={13} /> Download Snapshot
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {!loading && !backups.length && (
            <div className="admin-empty" style={{ padding: '32px 16px', textAlign: 'center' }}>
              <HardDrive size={32} style={{ margin: '0 auto 8px', color: '#94A3B8' }} />
              <p style={{ fontWeight: 600, color: '#334155', margin: 0 }}>No database backups created yet.</p>
              <p style={{ fontSize: '0.82rem', color: '#64748B', margin: '4px 0 12px' }}>
                Click &quot;Create DB Snapshot&quot; above to capture a full database backup of all tables.
              </p>
              <button
                type="button"
                className="admin-button"
                onClick={handleCreateBackup}
                disabled={isCreating}
              >
                Create First Database Backup
              </button>
            </div>
          )}

          {loading && (
            <div className="admin-empty" style={{ padding: '32px 16px', textAlign: 'center' }}>
              <RefreshCw size={24} className="spin-icon" style={{ margin: '0 auto 8px', color: '#102C57' }} />
              <p>Loading database backups and report metadata…</p>
            </div>
          )}
        </div>
      </section>

      {/* 5. OFFICIAL GOVERNMENT PRINT & PDF PREVIEW MODAL */}
      <GovernmentReportPrintModal
        isOpen={isPrintModalOpen}
        onClose={() => setIsPrintModalOpen(false)}
        template={selectedTemplate}
        reportData={reportData}
        selectedOfficerId={selectedOfficerId}
        selectedPetition={selectedPetitionObj}
      />

    </div>
  );
}
