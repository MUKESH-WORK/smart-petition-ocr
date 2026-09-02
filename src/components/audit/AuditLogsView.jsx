import React, { useState, useMemo } from 'react';
import {
  RefreshCw,
  Bot,
  BarChart2,
  FileText,
  FileCheck,
  Search,
  X,
  Calendar,
  RotateCcw,
  Inbox,
  MessageSquareText
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
  if (!timestampStr) return { year: '', month: '', day: '', dateStr: '' };
  try {
    const d = new Date(timestampStr);
    if (isNaN(d.getTime())) return { year: '', month: '', day: '', dateStr: '' };
    const year = String(d.getFullYear());
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return {
      year,
      month,
      day,
      dateStr: `${year}-${month}-${day}`
    };
  } catch (e) {
    return { year: '', month: '', day: '', dateStr: '' };
  }
}

const MONTH_OPTIONS = [
  { value: '01', label: 'January' },
  { value: '02', label: 'February' },
  { value: '03', label: 'March' },
  { value: '04', label: 'April' },
  { value: '05', label: 'May' },
  { value: '06', label: 'June' },
  { value: '07', label: 'July' },
  { value: '08', label: 'August' },
  { value: '09', label: 'September' },
  { value: '10', label: 'October' },
  { value: '11', label: 'November' },
  { value: '12', label: 'December' }
];

export default function AuditLogsView({
  auditRecords = [],
  currentPetitionId,
  onSelectPetition,
  onNavigateToGDP
}) {
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  // Date Filter States
  const [selectedDate, setSelectedDate] = useState('');
  const [selectedYear, setSelectedYear] = useState('');
  const [selectedMonth, setSelectedMonth] = useState('');
  const [selectedDay, setSelectedDay] = useState('');

  // Standardize real audit records passed into component
  const realLogs = useMemo(() => {
    return (auditRecords || []).map((rec) => ({
      id: rec.id || `AUD-${Math.floor(Math.random() * 100000)}`,
      timestamp: rec.timestamp || rec.uploadedAt || new Date().toISOString(),
      category: rec.category || 'GDP Assistant',
      categoryLabel: rec.categoryLabel || rec.category || 'GDP Assistant',
      officer: rec.officer || rec.officer_id || 'USER',
      source_id: rec.source_id || rec.id || 'N/A',
      details: rec.details || rec.summary || rec.fileName || '',
      rawPetition: rec.rawPetition || rec
    }));
  }, [auditRecords]);

  // Derived available years
  const availableYears = useMemo(() => {
    const currentYr = String(new Date().getFullYear());
    const yearsSet = new Set([currentYr]);
    realLogs.forEach((log) => {
      const parts = parseDateParts(log.timestamp);
      if (parts.year) yearsSet.add(parts.year);
    });
    return Array.from(yearsSet).sort((a, b) => b.localeCompare(a));
  }, [realLogs]);

  // Derived days (1-31)
  const availableDays = useMemo(() => {
    return Array.from({ length: 31 }, (_, i) => String(i + 1).padStart(2, '0'));
  }, []);

  // Sync Date Picker -> Year, Month, Day
  const handleFullDateChange = (e) => {
    const dateVal = e.target.value;
    setSelectedDate(dateVal);
    if (dateVal) {
      const [y, m, d] = dateVal.split('-');
      setSelectedYear(y || '');
      setSelectedMonth(m || '');
      setSelectedDay(d || '');
    } else {
      setSelectedYear('');
      setSelectedMonth('');
      setSelectedDay('');
    }
  };

  // Changing Individual Dropdowns clears Full Date Picker
  const handleYearChange = (e) => {
    setSelectedYear(e.target.value);
    setSelectedDate('');
  };

  const handleMonthChange = (e) => {
    setSelectedMonth(e.target.value);
    setSelectedDate('');
  };

  const handleDayChange = (e) => {
    setSelectedDay(e.target.value);
    setSelectedDate('');
  };

  // Reset all active date and search filters
  const handleResetFilters = () => {
    setSelectedDate('');
    setSelectedYear('');
    setSelectedMonth('');
    setSelectedDay('');
    setSearchQuery('');
  };

  const hasActiveFilters =
    selectedDate !== '' ||
    selectedYear !== '' ||
    selectedMonth !== '' ||
    selectedDay !== '' ||
    searchQuery.trim() !== '';

  // Manual Refresh Handler
  const handleRefresh = () => {
    setIsRefreshing(true);
    setTimeout(() => {
      setIsRefreshing(false);
    }, 600);
  };

  // Derived Filtered Logs
  const filteredLogs = useMemo(() => {
    return realLogs.filter((log) => {
      // 1. Search Query Filter
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        const matchesQ =
          log.id.toLowerCase().includes(q) ||
          log.source_id.toLowerCase().includes(q) ||
          log.officer.toLowerCase().includes(q) ||
          log.details.toLowerCase().includes(q) ||
          log.category.toLowerCase().includes(q);
        if (!matchesQ) return false;
      }

      // 2. Date Filters
      const dateParts = parseDateParts(log.timestamp);

      if (selectedDate) {
        if (dateParts.dateStr !== selectedDate) return false;
      } else {
        if (selectedYear && dateParts.year !== selectedYear) return false;
        if (selectedMonth && dateParts.month !== selectedMonth) return false;
        if (selectedDay && dateParts.day !== selectedDay) return false;
      }

      return true;
    });
  }, [realLogs, searchQuery, selectedDate, selectedYear, selectedMonth, selectedDay]);

  // Get Badge Icon & Class for Category
  const getCategoryBadgeInfo = (catName) => {
    const name = (catName || '').toLowerCase();
    if (name.includes('gdp')) {
      return { icon: MessageSquareText, styleClass: 'cat-badge-blue', label: 'GDP Assistant' };
    }
    if (name.includes('data') || name.includes('visualization')) {
      return { icon: BarChart2, styleClass: 'cat-badge-blue', label: 'Data & Visualization' };
    }
    if (name.includes('official') || name.includes('content')) {
      return { icon: FileText, styleClass: 'cat-badge-purple', label: 'Official Content' };
    }
    if (name.includes('bulk') || name.includes('workflow')) {
      return { icon: FileCheck, styleClass: 'cat-badge-green', label: 'Bulk Workflow' };
    }
    return { icon: Bot, styleClass: 'cat-badge-amber', label: 'General' };
  };

  return (
    <div className="audit-logs-page" role="region" aria-label="Audit Logs">
      <div className="audit-logs-container">

        {/* 1. PAGE HEADER */}
        <div className="audit-page-header">
          <div className="audit-title-group">
            <h2 className="audit-page-title">Audit Logs</h2>
            <p className="audit-page-subtext">
              Real-time audit trail of user queries and message activity in GDP Assistant.
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
              <RefreshCw size={15} className={`refresh-icon ${isRefreshing ? 'spin-anim' : ''}`} />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {/* 2. FILTER CARD (Date Controls + Search) */}
        <div className="audit-filter-card">

          {/* Top Bar: Search Input & Reset Button */}
          <div className="filter-card-top-row">
            <div className="audit-search-box">
              <Search size={16} className="search-icon" />
              <input
                type="text"
                className="audit-search-input"
                placeholder="Filter by officer, source ID, or message prompt..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
              {searchQuery && (
                <button
                  type="button"
                  className="search-clear-btn"
                  onClick={() => setSearchQuery('')}
                  aria-label="Clear search query"
                >
                  <X size={14} />
                </button>
              )}
            </div>

            {hasActiveFilters && (
              <button
                type="button"
                className="reset-filters-btn"
                onClick={handleResetFilters}
              >
                <RotateCcw size={13} />
                <span>Reset Filters</span>
              </button>
            )}
          </div>

          {/* Date Controls Section */}
          <div className="filter-section-group">
            <label className="filter-section-label">Date Range & Breakdown</label>
            <div className="date-controls-grid">

              {/* Native HTML Date Picker */}
              <div className="date-input-wrapper">
                <Calendar size={15} className="date-field-icon" />
                <input
                  type="date"
                  className="date-picker-input"
                  value={selectedDate}
                  onChange={handleFullDateChange}
                  title="Select full date"
                />
              </div>

              {/* Year Dropdown */}
              <div className="date-select-wrapper">
                <select
                  className="date-select"
                  value={selectedYear}
                  onChange={handleYearChange}
                >
                  <option value="">All Years</option>
                  {availableYears.map((yr) => (
                    <option key={yr} value={yr}>{yr}</option>
                  ))}
                </select>
              </div>

              {/* Month Dropdown */}
              <div className="date-select-wrapper">
                <select
                  className="date-select"
                  value={selectedMonth}
                  onChange={handleMonthChange}
                >
                  <option value="">All Months</option>
                  {MONTH_OPTIONS.map((m) => (
                    <option key={m.value} value={m.value}>{m.label}</option>
                  ))}
                </select>
              </div>

              {/* Day Dropdown */}
              <div className="date-select-wrapper">
                <select
                  className="date-select"
                  value={selectedDay}
                  onChange={handleDayChange}
                >
                  <option value="">All Days</option>
                  {availableDays.map((d) => (
                    <option key={d} value={d}>Day {parseInt(d, 10)}</option>
                  ))}
                </select>
              </div>

            </div>
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
            /* Scrollable Audit Log Table (5 Columns: Date & Time, Category, Officer, Source ID, Details) */
            <div className="audit-table-container">
              <table className="audit-table">
                <thead>
                  <tr>
                    <th style={{ width: '180px' }}>Date & Time</th>
                    <th style={{ width: '190px' }}>Category</th>
                    <th style={{ width: '130px' }}>Officer</th>
                    <th style={{ width: '160px' }}>Source ID</th>
                    <th>Details</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredLogs.map((log) => {
                    const categoryInfo = getCategoryBadgeInfo(log.category);
                    const CatIcon = categoryInfo.icon;

                    return (
                      <tr
                        key={log.id}
                        className={`audit-table-row ${log.rawPetition ? 'clickable-row' : ''}`}
                        onClick={() => {
                          if (log.rawPetition && onSelectPetition) {
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
                            <CatIcon size={13} />
                            <span>{categoryInfo.label}</span>
                          </span>
                        </td>

                        {/* 3. Officer */}
                        <td className="cell-officer" title={log.officer}>
                          {log.officer}
                        </td>

                        {/* 4. Source ID (Truncated) */}
                        <td className="cell-source-id">
                          <span className="source-id-badge" title={log.source_id}>
                            {log.source_id}
                          </span>
                        </td>

                        {/* 5. Details */}
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
                  ? 'No entries match the currently selected date or search filters.'
                  : 'Messages submitted in GDP Assistant will automatically appear here.'}
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
