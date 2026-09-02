import React, { useState } from 'react';
import { 
  FileText, 
  Search, 
  X, 
  ArrowRight, 
  CheckCircle2, 
  Clock, 
  History, 
  FilePlus2,
  FolderSearch
} from 'lucide-react';
import './AuditLogs.css';

export default function AuditLogsView({
  auditRecords = [],
  currentPetitionId,
  onSelectPetition,
  onNavigateToGDP
}) {
  const [searchQuery, setSearchQuery] = useState('');
  const [timeFilter, setTimeFilter] = useState('all'); // 'all' | 'today' | 'week'

  // Filter records based on search query and time filter
  const filteredRecords = auditRecords.filter((rec) => {
    const query = searchQuery.toLowerCase().trim();
    const matchesQuery = !query || (
      rec.fileName?.toLowerCase().includes(query) ||
      rec.id?.toLowerCase().includes(query) ||
      rec.summary?.toLowerCase().includes(query) ||
      rec.language?.toLowerCase().includes(query)
    );

    let matchesTime = true;
    if (timeFilter === 'today') {
      matchesTime = rec.uploadedAt?.toLowerCase().includes('today');
    } else if (timeFilter === 'week') {
      matchesTime = true; // all recent session items belong to current week
    }

    return matchesQuery && matchesTime;
  });

  const hasActiveFilters = searchQuery.trim() !== '' || timeFilter !== 'all';

  const handleClearFilters = () => {
    setSearchQuery('');
    setTimeFilter('all');
  };

  return (
    <div className="audit-logs-page" role="region" aria-label="Audit Logs">
      <div className="audit-logs-container">
        
        {/* Page Header */}
        <div className="audit-page-header">
          <div className="audit-title-group">
            <h2 className="audit-page-title">Audit Logs</h2>
            <p className="audit-page-subtext">Processed petitions and document activity in current session.</p>
          </div>

          {hasActiveFilters && (
            <div className="audit-header-actions">
              <button 
                type="button" 
                className="clear-filters-btn"
                onClick={handleClearFilters}
              >
                Clear Filters
              </button>
            </div>
          )}
        </div>

        {/* Controls Bar: Search & Filter Chips */}
        <div className="audit-controls-bar">
          
          {/* Search Input */}
          <div className="audit-search-box">
            <Search size={16} className="search-icon" />
            <input 
              type="text"
              className="audit-search-input"
              placeholder="Search by filename, petition ID, or summary..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            {searchQuery && (
              <button 
                type="button" 
                className="search-clear-btn"
                onClick={() => setSearchQuery('')}
                aria-label="Clear search"
              >
                <X size={14} />
              </button>
            )}
          </div>

          {/* Time Filter Pills */}
          <div className="audit-filter-chips">
            <button
              type="button"
              className={`filter-chip-btn ${timeFilter === 'all' ? 'active' : ''}`}
              onClick={() => setTimeFilter('all')}
            >
              All Records
            </button>
            <button
              type="button"
              className={`filter-chip-btn ${timeFilter === 'today' ? 'active' : ''}`}
              onClick={() => setTimeFilter('today')}
            >
              Today
            </button>
            <button
              type="button"
              className={`filter-chip-btn ${timeFilter === 'week' ? 'active' : ''}`}
              onClick={() => setTimeFilter('week')}
            >
              This Week
            </button>
          </div>

        </div>

        {/* Records Section */}
        <div className="audit-records-section">
          
          {filteredRecords.length > 0 ? (
            <>
              <div className="audit-records-count-label">
                {filteredRecords.length} {filteredRecords.length === 1 ? 'Record Found' : 'Records Found'}
              </div>

              {filteredRecords.map((rec) => {
                const isCurrent = rec.id === currentPetitionId;

                return (
                  <div
                    key={rec.id}
                    className={`audit-record-card ${isCurrent ? 'active-record' : ''}`}
                    onClick={() => onSelectPetition && onSelectPetition(rec)}
                    role="button"
                    tabIndex={0}
                    title="Click to open this petition in GDP Assistant workspace"
                  >
                    
                    {/* Left Icon + Text Details */}
                    <div className="record-main-col">
                      <div className="record-doc-icon-box">
                        <FileText size={18} />
                      </div>

                      <div className="record-text-details">
                        <div className="record-title-row">
                          <span className="record-file-name">{rec.fileName}</span>
                          <span className="record-id-badge font-mono">#{rec.id}</span>
                          {isCurrent && <span className="record-current-tag">Active in Workspace</span>}
                        </div>

                        <div className="record-summary-text">
                          {rec.summary}
                        </div>

                        <div className="record-meta-strip">
                          <span>Language: <span className="meta-val-highlight">{rec.language || 'Tamil'}</span></span>
                          <span>•</span>
                          <span>Pages: <span className="meta-val-highlight">{rec.totalPages || 1}</span></span>
                          <span>•</span>
                          <span>OCR Confidence: <span className="meta-val-highlight">{rec.confidenceScore || 96}%</span></span>
                          <span>•</span>
                          <span className="record-time-badge">
                            <Clock size={12} />
                            <span>{rec.uploadedAt || 'Today'}</span>
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Right Status + Action Arrow */}
                    <div className="record-right-col">
                      <div className="record-status-pill">
                        <CheckCircle2 size={12} />
                        <span>{rec.status || 'Analysis Complete'}</span>
                      </div>
                      <ArrowRight size={17} className="record-open-arrow" />
                    </div>

                  </div>
                );
              })}
            </>
          ) : (
            /* Empty State */
            <div className="audit-empty-card">
              <div className="audit-empty-icon-box">
                {hasActiveFilters ? <FolderSearch size={28} /> : <History size={28} />}
              </div>
              <h3 className="audit-empty-title">
                {hasActiveFilters ? 'No matching audit records' : 'No processed petitions yet.'}
              </h3>
              <p className="audit-empty-subtext">
                {hasActiveFilters 
                  ? 'Try clearing search terms or adjusting the filter.'
                  : 'Processed petitions and document understanding activity will appear here automatically.'}
              </p>

              {hasActiveFilters ? (
                <button 
                  type="button" 
                  className="audit-go-gdp-btn"
                  onClick={handleClearFilters}
                >
                  Clear Filters
                </button>
              ) : (
                <button 
                  type="button" 
                  className="audit-go-gdp-btn"
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
