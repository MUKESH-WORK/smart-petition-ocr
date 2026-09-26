import React, { useState, useMemo, useRef } from 'react';
import {
  RefreshCw,
  BarChart2,
  FileCheck,
  Search,
  X,
  Calendar,
  RotateCcw,
  Inbox,
  MessageSquareText,
  Users,
  ShieldCheck,
  Database,
  Layers,
  UserCheck
} from 'lucide-react';
import './AuditLogs.css';

// Helper to format date cleanly
function formatDate(timestampStr) {
  if (!timestampStr) return 'N/A';
  try {
    const d = new Date(timestampStr);
    if (isNaN(d.getTime())) return timestampStr;
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    const hours = String(d.getHours()).padStart(2, '0');
    const mins = String(d.getMinutes()).padStart(2, '0');
    const secs = String(d.getSeconds()).padStart(2, '0');
    return `${year}-${month}-${day} ${hours}:${mins}:${secs}`;
  } catch (e) {
    return timestampStr;
  }
}

// Helper to parse date parts
function parseDateParts(timestampStr) {
  if (!timestampStr) return { dateStr: '' };
  try {
    const d = new Date(timestampStr);
    if (isNaN(d.getTime())) return { dateStr: '' };
    const year = String(d.getFullYear());
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return {
      dateStr: `${year}-${month}-${day}`
    };
  } catch (e) {
    return { dateStr: '' };
  }
}

export default function AuditLogsView({
  auditRecords = [],
  isAdmin = false,
  officers = [],
  onRefreshAudit,
  currentPetitionId,
  onSelectPetition,
  onNavigateToGDP
}) {
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [selectedOfficer, setSelectedOfficer] = useState('all');
  const [selectedDate, setSelectedDate] = useState('');
  const [isDateFocused, setIsDateFocused] = useState(false);
  const dateInputRef = useRef(null);

  // Standardize real audit records passed into component
  const realLogs = useMemo(() => {
    return (auditRecords || []).map((rec) => {
      const catLower = (rec.category || '').toLowerCase();
      const typeUpper = String(rec.type || '').toUpperCase();
      const isSecurityOrSystem = 
        catLower.includes('security') ||
        catLower.includes('session') ||
        catLower.includes('auth') ||
        catLower.includes('hierarchy') ||
        catLower.includes('taxonomy') ||
        catLower.includes('master data') ||
        catLower.includes('user') ||
        ['LOGIN', 'LOGOUT', 'CONFIG', 'USER_CREATE', 'USER_UPDATE', 'USER_DELETE'].includes(typeUpper);

      const hasPetitionData = Boolean(
        rec.rawPetition?.petition_number ||
        rec.rawPetition?.grievance_text ||
        rec.rawPetition?.applicant_name ||
        rec.petition_number ||
        rec.applicant_name ||
        (rec.rawPetition && (String(rec.rawPetition.id || '').startsWith('PET-') || String(rec.rawPetition.id || '').startsWith('petition-')))
      );

      const isGdpAssistantRecord = !isSecurityOrSystem && (
        hasPetitionData ||
        catLower.includes('gdp') ||
        catLower.includes('petition') ||
        catLower.includes('grievance') ||
        ['UPLOAD', 'OCR', 'ANALYZE', 'PROCESS', 'APPROVE', 'INTEGRATE'].includes(typeUpper)
      );

      return {
        id: rec.id || `AUD-${Math.floor(Math.random() * 100000)}`,
        timestamp: rec.timestamp || rec.uploadedAt || rec.date || new Date().toISOString(),
        category: rec.category || (isGdpAssistantRecord ? 'GDP Assistant' : 'Security & Session'),
        categoryLabel: rec.categoryLabel || rec.category || (isGdpAssistantRecord ? 'GDP Assistant' : 'Security & Session'),
        type: rec.type || 'EVENT',
        officer: rec.officer || rec.officer_id || 'SYSTEM',
        officer_id: rec.officer_id || rec.officer || 'SYSTEM',
        source_id: rec.source_id || rec.id || 'N/A',
        details: rec.details || rec.summary || rec.fileName || '',
        rawPetition: isGdpAssistantRecord ? (rec.rawPetition || rec) : null,
        isClickable: isGdpAssistantRecord
      };
    });
  }, [auditRecords]);

  // Derived available officers list for filtering
  const availableOfficers = useMemo(() => {
    const officerMap = new Map();
    // 1. Add registered users / officers
    (officers || []).forEach((u) => {
      const id = u.id || u.officer_id || u.officerId || u.email;
      const name = u.name || u.fullName || u.email || id;
      const role = u.role ? ` (${u.role})` : '';
      if (id) {
        officerMap.set(String(id), `${name}${role}`);
      }
    });
    // 2. Incorporate officers from audit records
    realLogs.forEach((log) => {
      const off = log.officer || log.officer_id;
      if (off && !officerMap.has(String(off))) {
        officerMap.set(String(off), String(off));
      }
    });
    return Array.from(officerMap.entries()).map(([id, label]) => ({ id, label }));
  }, [officers, realLogs]);

  // Reset all active filters
  const handleResetFilters = () => {
    setSelectedCategory('all');
    setSelectedOfficer('all');
    setSelectedDate('');
    setSearchQuery('');
  };

  const hasActiveFilters =
    selectedCategory !== 'all' ||
    selectedOfficer !== 'all' ||
    selectedDate !== '' ||
    searchQuery.trim() !== '';

  // Manual Refresh Handler
  const handleRefresh = () => {
    setIsRefreshing(true);
    if (onRefreshAudit) {
      onRefreshAudit(selectedOfficer !== 'all' ? selectedOfficer : null);
    }
    setTimeout(() => {
      setIsRefreshing(false);
    }, 600);
  };

  // Derived Filtered Logs
  const filteredLogs = useMemo(() => {
    return realLogs.filter((log) => {
      // 1. Officer Filter
      if (selectedOfficer !== 'all') {
        const offLower = (log.officer || '').toLowerCase();
        const offIdLower = (log.officer_id || '').toLowerCase();
        const selLower = selectedOfficer.toLowerCase();
        const matchesOfficer = (
          offLower === selLower ||
          offIdLower === selLower ||
          offLower.includes(selLower) ||
          offIdLower.includes(selLower)
        );
        if (!matchesOfficer) return false;
      }

      // 2. Category Filter
      if (selectedCategory !== 'all') {
        const catLower = (log.category || '').toLowerCase();
        const selLower = selectedCategory.toLowerCase();
        if (!catLower.includes(selLower)) return false;
      }

      // 3. Search Query Filter
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        const matchesQ =
          log.id.toLowerCase().includes(q) ||
          log.source_id.toLowerCase().includes(q) ||
          log.officer.toLowerCase().includes(q) ||
          (log.officer_id && log.officer_id.toLowerCase().includes(q)) ||
          log.details.toLowerCase().includes(q) ||
          log.category.toLowerCase().includes(q);
        if (!matchesQ) return false;
      }

      // 4. Date Filter
      if (selectedDate) {
        const dateParts = parseDateParts(log.timestamp);
        if (dateParts.dateStr !== selectedDate) return false;
      }

      return true;
    });
  }, [realLogs, selectedOfficer, selectedCategory, searchQuery, selectedDate]);

  // Get Badge Icon & Class for Category and Action Type
  const getCategoryBadgeInfo = (catName, actionType) => {
    const name = (catName || '').toLowerCase();
    const type = (actionType || '').toLowerCase();

    if (name.includes('taxonomy') || name.includes('master') || type.includes('taxonomy') || type.includes('ingest')) {
      return { icon: Database, styleClass: 'cat-badge-purple', label: 'Master Data' };
    }
    if (name.includes('hierarchy') || name.includes('taluk') || name.includes('village') || name.includes('block')) {
      return { icon: Layers, styleClass: 'cat-badge-blue', label: 'Hierarchy' };
    }
    if (name.includes('user') || type.includes('user') || type.includes('password') || type.includes('credential')) {
      return { icon: Users, styleClass: 'cat-badge-purple', label: 'User Management' };
    }
    if (name.includes('security') || name.includes('session') || type.includes('login') || type.includes('logout') || type.includes('auth')) {
      return { icon: ShieldCheck, styleClass: 'cat-badge-amber', label: 'Security & Auth' };
    }
    if (name.includes('data') || name.includes('visualization')) {
      return { icon: BarChart2, styleClass: 'cat-badge-blue', label: 'Data & Analytics' };
    }
    if (name.includes('gdp') || type.includes('upload') || type.includes('process') || type.includes('approve') || type.includes('integrate') || type.includes('petition')) {
      return { icon: MessageSquareText, styleClass: 'cat-badge-blue', label: 'GDP Assistant' };
    }
    return { icon: FileCheck, styleClass: 'cat-badge-green', label: catName || 'Audit Entry' };
  };

  return (
    <div className="audit-logs-page" role="region" aria-label="Audit Logs">
      <div className="audit-logs-container">

        {/* 1. PAGE HEADER */}
        <div className="audit-page-header">
          <div className="audit-title-group">
            <h2 className="audit-page-title">Audit Logs</h2>
            <p className="audit-page-subtext">
              Real-time audit trail of user queries, administrative actions, and system operations.
            </p>
          </div>

          <div className="audit-header-actions">
            <button
              type="button"
              className={`refresh-logs-btn ${isRefreshing ? 'refreshing' : ''}`}
              onClick={handleRefresh}
              disabled={isRefreshing}
              title="Refresh Audit Data"
            >
              <RefreshCw size={14} className={`refresh-icon ${isRefreshing ? 'spin-anim' : ''}`} />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {/* 2. FILTER CARD (Single Clean Horizontal Row) */}
        <div className="audit-filter-card">
          <div className="audit-filter-controls-row">

            {/* Search Box */}
            <div className="audit-search-box">
              <Search size={15} className="audit-search-icon search-icon" />
              <input
                type="text"
                className="audit-search-input"
                placeholder="Search logs by keyword, action, or ID..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
              {searchQuery && (
                <button
                  type="button"
                  className="search-clear-btn"
                  onClick={() => setSearchQuery('')}
                  aria-label="Clear search query"
                  title="Clear search"
                >
                  <X size={13} />
                </button>
              )}
            </div>

            {/* Officer Filter Dropdown (Admin only) */}
            {isAdmin && (
              <div className="date-select-wrapper officer-select-wrapper">
                <UserCheck size={14} className="filter-inner-icon" />
                <select
                  className="date-select officer-select"
                  value={selectedOfficer}
                  onChange={(e) => setSelectedOfficer(e.target.value)}
                  title="Filter by Officer"
                >
                  <option value="all">All Officers ({availableOfficers.length})</option>
                  {availableOfficers.map((off) => (
                    <option key={off.id} value={off.id}>
                      {off.label}
                    </option>
                  ))}
                </select>
              </div>
            )}
            {isAdmin && (
              <div className="date-select-wrapper category-select-wrapper">
                <select
                  className="date-select"
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                  title="Filter by Category"
                >
                  <option value="all">All Categories</option>
                  <option value="GDP Assistant">GDP Assistant & Petitions</option>
                  <option value="Master Data">Master Data & Taxonomy</option>
                  <option value="Administrative Hierarchy">Administrative Hierarchy</option>
                  <option value="User Management">User Management</option>
                  <option value="Security & Session">Security & Auth</option>
                </select>
              </div>
            )}

            {/* Date Picker */}
            <div
              className={`date-input-wrapper ${selectedDate ? 'has-date' : ''}`}
              onClick={() => {
                dateInputRef.current?.focus();
                try {
                  dateInputRef.current?.showPicker();
                } catch { }
              }}
            >
              <Calendar size={14} className="date-field-icon" />
              <input
                ref={dateInputRef}
                type={isDateFocused || selectedDate ? 'date' : 'text'}
                className="date-picker-input"
                placeholder="Select date"
                value={selectedDate}
                onClick={() => {
                  try {
                    dateInputRef.current?.showPicker();
                  } catch { }
                }}
                onFocus={() => {
                  setIsDateFocused(true);
                  try {
                    dateInputRef.current?.showPicker();
                  } catch { }
                }}
                onBlur={() => {
                  if (!selectedDate) {
                    setIsDateFocused(false);
                  }
                }}
                onChange={(e) => setSelectedDate(e.target.value)}
                title="Select date"
              />
              {selectedDate && (
                <button
                  type="button"
                  className="date-clear-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    setSelectedDate('');
                    setIsDateFocused(false);
                  }}
                  aria-label="Clear date filter"
                  title="Clear date"
                >
                  <X size={12} />
                </button>
              )}
            </div>

            {/* Reset Filters Button */}
            {hasActiveFilters && (
              <button
                type="button"
                className="reset-filters-btn"
                onClick={handleResetFilters}
                title="Reset all active filters"
              >
                <RotateCcw size={13} />
                <span>Reset</span>
              </button>
            )}

          </div>
        </div>

        {/* 3. ENTRY COUNT & SUMMARY */}
        <div className="audit-results-summary">
          <div className="results-count-text">
            <span>Showing </span>
            <strong>{filteredLogs.length}</strong>
            <span> {filteredLogs.length === 1 ? 'audit entry' : 'audit entries'}</span>
            {hasActiveFilters && <span className="active-filter-tag">(Filtered)</span>}
          </div>
        </div>

        {/* 4. AUDIT LOG TABLE / LOADING / EMPTY STATE */}
        <div className="audit-records-wrapper">
          {isRefreshing ? (
            /* Loading State */
            <div className="audit-loading-card">
              <RefreshCw size={28} className="spin-anim loading-spinner-icon" />
              <p className="loading-text">Loading audit log entries...</p>
            </div>
          ) : filteredLogs.length > 0 ? (
            /* Scrollable Audit Log Table */
            <div className="audit-table-container">
              <table className="audit-table">
                <thead>
                  <tr>
                    <th style={{ width: '180px' }}>Date & Time</th>
                    <th style={{ width: '190px' }}>Category</th>
                    {isAdmin && <th style={{ width: '170px' }}>Officer</th>}
                    <th>Details</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredLogs.map((log) => {
                    const categoryInfo = getCategoryBadgeInfo(log.category, log.type);
                    const CatIcon = categoryInfo.icon;

                    return (
                      <tr
                        key={log.id}
                        className={`audit-table-row ${log.isClickable ? 'clickable-row' : 'non-clickable-row'}`}
                        style={{ cursor: log.isClickable ? 'pointer' : 'default' }}
                        title={log.isClickable ? 'Click to inspect petition record' : undefined}
                        onClick={() => {
                          if (log.isClickable && log.rawPetition && onSelectPetition) {
                            onSelectPetition(log.rawPetition);
                          }
                        }}
                      >
                        {/* 1. Date & Time */}
                        <td className="cell-datetime">
                          {formatDate(log.timestamp)}
                        </td>

                        {/* 2. Category Badge */}
                        <td className="cell-category">
                          <span className={`cat-badge ${categoryInfo.styleClass}`}>
                            <CatIcon size={12} />
                            <span>{categoryInfo.label}</span>
                          </span>
                        </td>

                        {/* 3. Officer (Admin only) */}
                        {isAdmin && (
                          <td className="cell-officer" title={log.officer}>
                            <span className="officer-name-label">{log.officer}</span>
                          </td>
                        )}

                        {/* 4. Details */}
                        <td className="cell-details">
                          <p className="details-text">{log.details}</p>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            /* Empty State */
            <div className="audit-empty-card">
              <div className="audit-empty-icon-box">
                <Inbox size={32} />
              </div>
              <h3 className="audit-empty-title">No Audit Log entries found</h3>
              <p className="audit-empty-subtext">
                {hasActiveFilters
                  ? 'No entries match the currently selected category, officer, date, or search filters.'
                  : 'System activity and processed petitions will appear here in real time.'}
              </p>

              {hasActiveFilters ? (
                <button
                  type="button"
                  className="audit-reset-btn"
                  onClick={handleResetFilters}
                >
                  Reset All Filters
                </button>
              ) : (
                <button
                  type="button"
                  className="audit-reset-btn"
                  onClick={onNavigateToGDP}
                >
                  Go to GDP Assistant
                </button>
              )}
            </div>
          )}
        </div>

      </div>
    </div>
  );
}

