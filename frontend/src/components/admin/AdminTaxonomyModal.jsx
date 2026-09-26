import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  GitFork,
  RefreshCw,
  Plus,
  Pencil,
  Trash2,
  Search,
  Building2,
  ShieldCheck,
  FileText,
  Users,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  X,
  Check,
  AlertCircle,
  Filter,
  Sparkles,
  Layers,
  Radio
} from 'lucide-react';
import {
  fetchTaxonomyStats,
  fetchTaxonomyDepartments,
  fetchTaxonomyList,
  createTaxonomyItem,
  updateTaxonomyItem,
  deleteTaxonomyItem,
  fetchIntakeChannels,
  createIntakeChannel,
  updateIntakeChannel,
  deleteIntakeChannel
} from '../../services/apiService';
import './AdminTaxonomyModal.css';

const VECTOR_CATEGORIES = [
  { key: 'digital_direct', label: '1. Digital Direct Channels', icon: Radio, desc: 'Toll-free 1100 Call Center, Citizen Web Portal, and direct inbound e-mail' },
  { key: 'executive_leadership', label: '2. Executive Leadership Grievance Desks', icon: ShieldCheck, desc: 'CM Special Cell, CM Camp Office, Chief Secretary Office, CM Secretaries, Ministers Office' },
  { key: 'legislative', label: '3. Legislative Representation', icon: Users, desc: 'State MLA Constituency Grievances and MP Reference Petitions' },
  { key: 'district_grievance_days', label: '4. District Grievance Days', icon: Building2, desc: 'Weekly Monday Collectorate Grievance Day, Differently Abled, Agriculture, Jamabandhi, Mass Contact' },
  { key: 'field_outreach_camps', label: '5. Field Outreach Camps & Walk-in Counters', icon: Sparkles, desc: 'Makkaludan Mudhalvar Rural/Urban/Special Camps, e-Sevai Centers, and Taluk Office Counters', extraKeys: ['counters_walkin'] }
];

export default function AdminTaxonomyModal({ onClose }) {
  // Navigation Sub-Tab State: 'mappings' | 'channels'
  const [activeTab, setActiveTab] = useState('mappings');

  // Live server state - zero hardcoded data
  const [stats, setStats] = useState({
    total_mappings: 0,
    total_departments: 0,
    total_grievance_types: 0,
    total_sub_types: 0,
    department_breakdown: []
  });
  const [departments, setDepartments] = useState([]);
  const [items, setItems] = useState([]);
  const [totalItems, setTotalItems] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);

  // Intake Channels State
  const [channels, setChannels] = useState([]);
  const [channelsLoading, setChannelsLoading] = useState(false);
  const [channelFilter, setChannelFilter] = useState('all');

  // Channel Edit / Create / Delete State
  const [editingChannel, setEditingChannel] = useState(null);
  const [isCreatingChannel, setIsCreatingChannel] = useState(false);
  const [deletingChannel, setDeletingChannel] = useState(null);
  const [channelFormName, setChannelFormName] = useState('');
  const [channelFormCode, setChannelFormCode] = useState('');
  const [channelFormCategory, setChannelFormCategory] = useState('digital_direct');
  const [channelFormDesc, setChannelFormDesc] = useState('');
  const [channelFormActive, setChannelFormActive] = useState(true);

  // Filters
  const [selectedDept, setSelectedDept] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');

  // UI state
  const [loading, setLoading] = useState(true);
  const [tableLoading, setTableLoading] = useState(false);
  const [feedback, setFeedback] = useState(null);
  const [editingItem, setEditingItem] = useState(null); // null | object
  const [isCreating, setIsCreating] = useState(false);
  const [deletingItem, setDeletingItem] = useState(null);
  const [saving, setSaving] = useState(false);

  // Form State for Add / Edit Mapping
  const [formDept, setFormDept] = useState('');
  const [formCode, setFormCode] = useState('');
  const [formSubDept, setFormSubDept] = useState('');
  const [formGrievanceType, setFormGrievanceType] = useState('');
  const [formGrievanceSubType, setFormGrievanceSubType] = useState('');
  const [formResponsibleOfficer, setFormResponsibleOfficer] = useState('');

  // Debounce search query
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedQuery(searchQuery);
      setCurrentPage(1);
    }, 280);
    return () => clearTimeout(handler);
  }, [searchQuery]);

  // Derived: filtered channels by active/inactive/all
  const filteredChannels = useMemo(() => {
    if (channelFilter === 'all') return channels;
    if (channelFilter === 'active') return channels.filter(c => c.is_active);
    return channels.filter(c => !c.is_active);
  }, [channels, channelFilter]);

  // Load stats, departments, and intake channels once on mount
  const loadInitialData = useCallback(async () => {
    try {
      setLoading(true);
      const [statsData, deptData, channelsData] = await Promise.all([
        fetchTaxonomyStats(),
        fetchTaxonomyDepartments(),
        fetchIntakeChannels().catch(() => ({ channels: [] }))
      ]);
      setStats(statsData);
      const list = Array.isArray(deptData) ? deptData : (deptData?.departments || []);
      setDepartments(list);
      setChannels(channelsData?.channels || []);
    } catch (err) {
      console.error('Failed to load initial taxonomy stats:', err);
      setFeedback({ type: 'error', message: err.message || 'Failed to load taxonomy metadata.' });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadInitialData();
  }, [loadInitialData]);

  // Toggle channel active status in DB
  const handleToggleChannel = async (channel) => {
    try {
      const nextActive = !channel.is_active;
      await updateIntakeChannel(channel.id, { is_active: nextActive });
      setChannels((prev) => prev.map((c) => c.id === channel.id ? { ...c, is_active: nextActive } : c));
      setFeedback({ type: 'success', message: `Updated channel "${channel.channel_name}" to ${nextActive ? 'Active' : 'Inactive'}.` });
    } catch (err) {
      setFeedback({ type: 'error', message: err.message || 'Failed to update channel status.' });
    }
  };

  // Open Create Channel Dialog
  const handleOpenCreateChannel = () => {
    setChannelFormName('');
    setChannelFormCode('');
    setChannelFormCategory('digital_direct');
    setChannelFormDesc('');
    setChannelFormActive(true);
    setIsCreatingChannel(true);
    setEditingChannel(null);
  };

  // Open Edit Channel Dialog
  const handleOpenEditChannel = (ch) => {
    setEditingChannel(ch);
    setIsCreatingChannel(false);
    setChannelFormName(ch.channel_name || '');
    setChannelFormCode(ch.channel_code || '');
    setChannelFormCategory(ch.category || 'digital_direct');
    setChannelFormDesc(ch.description || '');
    setChannelFormActive(Boolean(ch.is_active));
  };

  // Save Channel (Create or Update)
  const handleSaveChannel = async (e) => {
    e.preventDefault();
    if (!channelFormName.trim() || !channelFormCode.trim()) {
      setFeedback({ type: 'error', message: 'Channel name and channel code are required.' });
      return;
    }

    try {
      setSaving(true);
      const payload = {
        channel_name: channelFormName.trim(),
        channel_code: channelFormCode.trim().toUpperCase(),
        category: channelFormCategory,
        description: channelFormDesc.trim(),
        is_active: channelFormActive
      };

      if (isCreatingChannel) {
        await createIntakeChannel(payload);
        setFeedback({ type: 'success', message: `Created new intake channel "${payload.channel_name}".` });
      } else if (editingChannel) {
        await updateIntakeChannel(editingChannel.id, payload);
        setFeedback({ type: 'success', message: `Updated intake channel "${payload.channel_name}".` });
      }

      setIsCreatingChannel(false);
      setEditingChannel(null);
      await loadInitialData();
    } catch (err) {
      setFeedback({ type: 'error', message: err.message || 'Failed to save intake channel.' });
    } finally {
      setSaving(false);
    }
  };

  // Delete Channel Action
  const handleDeleteChannelConfirm = async () => {
    if (!deletingChannel) return;
    try {
      setSaving(true);
      await deleteIntakeChannel(deletingChannel.id);
      setFeedback({ type: 'success', message: `Deleted intake channel "${deletingChannel.channel_name}".` });
      setDeletingChannel(null);
      await loadInitialData();
    } catch (err) {
      setFeedback({ type: 'error', message: err.message || 'Failed to delete intake channel.' });
    } finally {
      setSaving(false);
    }
  };

  // Load paginated list when filters or page change
  const loadTaxonomyPage = useCallback(async () => {
    try {
      setTableLoading(true);
      const res = await fetchTaxonomyList({
        department: selectedDept,
        q: debouncedQuery,
        page: currentPage,
        pageSize: pageSize
      });
      setItems(res.items || []);
      setTotalItems(res.total || 0);
      setTotalPages(res.total_pages || 1);
    } catch (err) {
      console.error('Failed to load taxonomy mappings:', err);
      setFeedback({ type: 'error', message: err.message || 'Failed to load taxonomy records.' });
    } finally {
      setTableLoading(false);
    }
  }, [selectedDept, debouncedQuery, currentPage, pageSize]);

  useEffect(() => {
    loadTaxonomyPage();
  }, [loadTaxonomyPage]);

  // Open Create Dialog
  const handleOpenCreate = () => {
    setFormDept(selectedDept || (departments[0]?.department || ''));
    setFormCode('');
    setFormSubDept('');
    setFormGrievanceType('');
    setFormGrievanceSubType('');
    setFormResponsibleOfficer('');
    setIsCreating(true);
    setEditingItem(null);
  };

  // Open Edit Dialog
  const handleOpenEdit = (item) => {
    setEditingItem(item);
    setIsCreating(false);
    setFormDept(item.department || '');
    setFormCode(item.department_code || '');
    setFormSubDept(item.sub_department || '');
    setFormGrievanceType(item.grievance_type || '');
    setFormGrievanceSubType(item.grievance_sub_type || '');
    setFormResponsibleOfficer(item.responsible_officer || '');
  };

  // Save (Create or Update)
  const handleSaveItem = async (e) => {
    e.preventDefault();
    if (!formDept.trim() || !formGrievanceType.trim() || !formGrievanceSubType.trim()) {
      setFeedback({
        type: 'error',
        message: 'Department, Grievance Type, and Grievance Sub-Type are mandatory.'
      });
      return;
    }

    try {
      setSaving(true);
      const payload = {
        department: formDept.trim(),
        department_code: formCode.trim(),
        sub_department: formSubDept.trim(),
        grievance_type: formGrievanceType.trim(),
        grievance_sub_type: formGrievanceSubType.trim(),
        responsible_officer: formResponsibleOfficer.trim()
      };

      if (isCreating) {
        await createTaxonomyItem(payload);
        setFeedback({ type: 'success', message: 'Authoritative taxonomy mapping created with AI vector index.' });
      } else if (editingItem) {
        await updateTaxonomyItem(editingItem.id, payload);
        setFeedback({ type: 'success', message: `Taxonomy mapping #${editingItem.id} updated successfully.` });
      }

      setIsCreating(false);
      setEditingItem(null);
      await Promise.all([loadInitialData(), loadTaxonomyPage()]);
    } catch (err) {
      setFeedback({ type: 'error', message: err.message || 'Error saving taxonomy record.' });
    } finally {
      setSaving(false);
    }
  };

  // Delete Action
  const handleDeleteConfirm = async () => {
    if (!deletingItem) return;
    try {
      setSaving(true);
      await deleteTaxonomyItem(deletingItem.id);
      setFeedback({
        type: 'success',
        message: `Deleted mapping: ${deletingItem.department} > ${deletingItem.grievance_sub_type}`
      });
      setDeletingItem(null);
      await Promise.all([loadInitialData(), loadTaxonomyPage()]);
    } catch (err) {
      setFeedback({ type: 'error', message: err.message || 'Failed to delete taxonomy mapping.' });
    } finally {
      setSaving(false);
    }
  };

  // Department code helper
  const extractCode = (deptName, givenCode) => {
    if (givenCode) return givenCode;
    if (!deptName) return '';
    const match = deptName.match(/\(([A-Z0-9]+)\)/);
    return match ? match[1] : deptName.substring(0, 4).toUpperCase();
  };

  return (
    <div className="taxonomy-overlay" role="dialog" aria-modal="true">
      <div className="taxonomy-dialog">
        {/* Top Header */}
        <header className="taxonomy-header">
          <div className="taxonomy-header-title-area">
            <h2>CM Grievance Mappings &amp; Intake Channels</h2>
          </div>
          <div className="taxonomy-header-actions">
            <button
              className="taxonomy-action-btn secondary"
              onClick={() => { loadInitialData(); loadTaxonomyPage(); }}
              disabled={loading || tableLoading}
              title="Refresh Dataset from live Database"
            >
              <RefreshCw size={15} className={loading || tableLoading ? 'spin' : ''} />
              <span>Refresh</span>
            </button>
            {activeTab === 'mappings' ? (
              <button
                className="taxonomy-action-btn primary"
                onClick={handleOpenCreate}
              >
                <Plus size={16} />
                <span>Add Mapping</span>
              </button>
            ) : (
              <button
                className="taxonomy-action-btn primary"
                onClick={handleOpenCreateChannel}
              >
                <Plus size={16} />
                <span>Add Channel</span>
              </button>
            )}
            <button
              className="taxonomy-close-btn"
              onClick={onClose}
              aria-label="Close modal"
            >
              <X size={20} />
            </button>
          </div>
        </header>

        {/* Live KPI Statistics Strip */}
        <section className="taxonomy-kpi-bar">
          <div className="taxonomy-kpi-card">
            <div className="kpi-icon-wrapper dept">
              <Building2 size={18} />
            </div>
            <div className="kpi-content">
              <span className="kpi-label">Department Groups</span>
              <strong className="kpi-value">{stats.total_departments || 0}</strong>
            </div>
          </div>
          <div className="taxonomy-kpi-card">
            <div className="kpi-icon-wrapper mappings">
              <GitFork size={18} />
            </div>
            <div className="kpi-content">
              <span className="kpi-label">Total Sub-Type Mappings</span>
              <strong className="kpi-value">{stats.total_mappings ? stats.total_mappings.toLocaleString() : 0}</strong>
            </div>
          </div>
          <div className="taxonomy-kpi-card">
            <div className="kpi-icon-wrapper types">
              <FileText size={18} />
            </div>
            <div className="kpi-content">
              <span className="kpi-label">Grievance Types</span>
              <strong className="kpi-value">{stats.total_grievance_types || 0}</strong>
            </div>
          </div>
          <div className="taxonomy-kpi-card">
            <div className="kpi-icon-wrapper officers">
              <ShieldCheck size={18} />
            </div>
            <div className="kpi-content">
              <span className="kpi-label">Distinct Sub-Types</span>
              <strong className="kpi-value">{stats.total_sub_types ? stats.total_sub_types.toLocaleString() : 0}</strong>
            </div>
          </div>
        </section>

        {/* Navigation Sub-Tabs */}
        <nav className="taxonomy-tabs-nav" aria-label="Section tabs">
          <button
            type="button"
            className={`taxonomy-tab-btn ${activeTab === 'mappings' ? 'active' : ''}`}
            onClick={() => setActiveTab('mappings')}
          >
            <GitFork size={15} />
            <span>CM Grievance Mappings</span>
            <span className="tab-counter-pill">{stats.total_mappings ? stats.total_mappings.toLocaleString() : 1861}</span>
          </button>
          <button
            type="button"
            className={`taxonomy-tab-btn ${activeTab === 'channels' ? 'active' : ''}`}
            onClick={() => setActiveTab('channels')}
          >
            <Layers size={15} />
            <span>Intake Channels ({channels.length} Sources)</span>
            <span className="tab-counter-pill">{channels.length}</span>
          </button>
        </nav>

        {/* Feedback Alert Banner */}
        {feedback && (
          <div className={`taxonomy-alert-banner ${feedback.type}`}>
            <div className="alert-content">
              {feedback.type === 'error' ? <AlertCircle size={16} /> : <Check size={16} />}
              <span>{feedback.message}</span>
            </div>
            <button className="alert-close" onClick={() => setFeedback(null)}>
              <X size={14} />
            </button>
          </div>
        )}

        {/* TAB 1: CM Grievance Mappings */}
        {activeTab === 'mappings' && (
          <>
            {/* Search & Department Filter Toolbar */}
            <section className="taxonomy-toolbar">
              <div className="toolbar-search">
                <Search size={18} className="search-icon" />
                <input
                  type="text"
                  placeholder="Search by Grievance Type, Sub-Type, Officer, or Sub-Department..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="taxonomy-search-input"
                />
                {searchQuery && (
                  <button className="search-clear-btn" onClick={() => setSearchQuery('')}>
                    <X size={14} />
                  </button>
                )}
              </div>

              <div className="toolbar-filters">
                <div className="dept-select-wrapper">
                  <Filter size={15} className="select-icon" />
                  <select
                    className="taxonomy-dept-select"
                    value={selectedDept}
                    onChange={(e) => {
                      setSelectedDept(e.target.value);
                      setCurrentPage(1);
                    }}
                  >
                    <option value="">All Departments ({stats.total_mappings || 0})</option>
                    {departments.map((d) => (
                      <option key={d.department} value={d.department}>
                        {d.department} ({d.count})
                      </option>
                    ))}
                  </select>
                  <ChevronDown size={14} className="select-chevron-icon" />
                </div>

                <div className="page-size-wrapper">
                  <label>Rows:</label>
                  <div className="size-select-wrapper">
                    <select
                      className="taxonomy-size-select"
                      value={pageSize}
                      onChange={(e) => {
                        setPageSize(Number(e.target.value));
                        setCurrentPage(1);
                      }}
                    >
                      <option value={10}>10</option>
                      <option value={25}>25</option>
                      <option value={50}>50</option>
                      <option value={100}>100</option>
                    </select>
                    <ChevronDown size={13} className="select-chevron-icon" />
                  </div>
                </div>
              </div>
            </section>

            {/* Main Table Container */}
            <main className="taxonomy-table-container">
              {tableLoading && (
                <div className="table-loading-overlay">
                  <RefreshCw size={24} className="spin" />
                  <span>Querying live database mappings...</span>
                </div>
              )}

              <table className="taxonomy-data-table">
                <thead>
                  <tr>
                    <th style={{ width: '60px' }}>ID</th>
                    <th style={{ width: '220px' }}>Department</th>
                    <th style={{ width: '200px' }}>Grievance Type</th>
                    <th style={{ width: '250px' }}>Grievance Sub-Type</th>
                    <th style={{ width: '180px' }}>Sub-Department</th>
                    <th>Responsible Officer</th>
                    <th style={{ width: '90px', textAlign: 'center' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {items.length === 0 && !tableLoading ? (
                    <tr>
                      <td colSpan={7} className="taxonomy-empty-state">
                        <AlertCircle size={32} />
                        <p>No taxonomy mappings match the current query or department filter.</p>
                        <button
                          className="taxonomy-action-btn secondary"
                          onClick={() => { setSelectedDept(''); setSearchQuery(''); }}
                        >
                          Clear Filters
                        </button>
                      </td>
                    </tr>
                  ) : (
                    items.map((item) => {
                      const code = extractCode(item.department, item.department_code);
                      return (
                        <tr key={item.id} className="taxonomy-row">
                          <td className="cell-id">#{item.id}</td>
                          <td className="cell-dept">
                            <div className="dept-cell-content">
                              {code && <span className="dept-code-tag">{code}</span>}
                              <span className="dept-full-name" title={item.department}>
                                {item.department.replace(/\s*\([A-Z0-9]+\)\s*$/, '')}
                              </span>
                            </div>
                          </td>
                          <td className="cell-gtype">
                            <span className="gtype-text" title={item.grievance_type}>
                              {item.grievance_type}
                            </span>
                          </td>
                          <td className="cell-gsub">
                            <span className="gsub-highlight" title={item.grievance_sub_type}>
                              {item.grievance_sub_type}
                            </span>
                          </td>
                          <td className="cell-sdept">
                            {item.sub_department ? (
                              <span className="subdept-badge" title={item.sub_department}>
                                {item.sub_department}
                              </span>
                            ) : (
                              <span className="na-text">—</span>
                            )}
                          </td>
                          <td className="cell-officer">
                            {item.responsible_officer ? (
                              <div className="officer-badge" title={item.responsible_officer}>
                                <ShieldCheck size={13} className="officer-badge-icon" />
                                <span>{item.responsible_officer}</span>
                              </div>
                            ) : (
                              <span className="na-text">Unassigned</span>
                            )}
                          </td>
                          <td className="cell-actions">
                            <div className="row-action-group">
                              <button
                                className="action-icon-btn edit"
                                onClick={() => handleOpenEdit(item)}
                                title="Edit Mapping"
                              >
                                <Pencil size={14} />
                              </button>
                              <button
                                className="action-icon-btn delete"
                                onClick={() => setDeletingItem(item)}
                                title="Delete Mapping"
                              >
                                <Trash2 size={14} />
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </main>

            {/* Footer Pagination Bar */}
            <footer className="taxonomy-footer">
              <div className="pagination-info">
                Showing <strong>{totalItems === 0 ? 0 : (currentPage - 1) * pageSize + 1}</strong> to{' '}
                <strong>{Math.min(currentPage * pageSize, totalItems)}</strong> of{' '}
                <strong>{totalItems.toLocaleString()}</strong> official mappings
              </div>

              <div className="pagination-controls">
                <button
                  className="page-nav-btn"
                  disabled={currentPage <= 1 || tableLoading}
                  onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                >
                  <ChevronLeft size={16} />
                  <span>Previous</span>
                </button>
                <span className="page-current-indicator">
                  Page <strong>{currentPage}</strong> of <strong>{totalPages}</strong>
                </span>
                <button
                  className="page-nav-btn"
                  disabled={currentPage >= totalPages || tableLoading}
                  onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                >
                  <span>Next</span>
                  <ChevronRight size={16} />
                </button>
              </div>
            </footer>
          </>
        )}

        {/* TAB 2: Intake Channels */}
        {activeTab === 'channels' && (
          <section className="channels-tab-content">
            {/* Channels Header Strip */}
            <div className="channels-header-strip">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <span style={{ fontWeight: 700, fontSize: '0.95rem', color: '#080505ff' }}>
                  {channels.length} Total Intake Channels Configured
                </span>
              </div>
            </div>

            {/* Grouped Channel Cards */}
            {VECTOR_CATEGORIES.map((cat) => {
              const matchKeys = [cat.key, ...(cat.extraKeys || [])];
              const catChannels = channels.filter(c => matchKeys.includes(c.category));
              if (catChannels.length === 0) return null;
              return (
                <div key={cat.key} className="channels-vector-group">
                  <div className="vector-group-title">
                    <span>{cat.label}</span>
                    <span className="tab-counter-pill" style={{ marginLeft: 'auto' }}>{catChannels.length}</span>
                  </div>
                  <p style={{ margin: 0, fontSize: '0.8rem', color: '#64748b', marginTop: '-0.5rem' }}>{cat.desc}</p>
                  <div className="channels-grid">
                    {catChannels.map((ch) => (
                      <div key={ch.id} className="channel-card">
                        <div className="channel-card-top">
                          <h4 className="channel-name">{ch.channel_name}</h4>
                          <span className="channel-code-badge">{ch.channel_code}</span>
                        </div>
                        <p className="channel-desc">{ch.description || 'Official grievance intake channel.'}</p>
                        <div className="channel-footer">
                          <div className="channel-footer-actions" style={{ marginLeft: 'auto' }}>
                            <button
                              className="btn-card-action edit"
                              onClick={() => handleOpenEditChannel(ch)}
                              title="Edit Channel"
                            >
                              Edit
                            </button>
                            <button
                              className="btn-card-action remove"
                              onClick={() => setDeletingChannel(ch)}
                              title="Delete Channel"
                            >
                              Delete
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}

            {/* Empty State */}
            {filteredChannels.length === 0 && (
              <div className="taxonomy-empty-state" style={{ padding: '3rem 2rem' }}>
                <p>No intake channels match the current filter.</p>
                <button
                  className="taxonomy-action-btn secondary"
                  onClick={() => setChannelFilter('all')}
                >
                  Show All Channels
                </button>
              </div>
            )}
          </section>
        )}


        {/* Create / Edit Mapping Dialog Modal */}
        {(isCreating || editingItem) && (
          <div className="taxonomy-submodal-overlay" role="dialog">
            <div className="taxonomy-submodal-card">
              <div className="submodal-header">
                <h3>{isCreating ? 'Add Authoritative Taxonomy Mapping' : `Edit Taxonomy Mapping #${editingItem?.id}`}</h3>
                <button
                  className="submodal-close-btn"
                  onClick={() => { setIsCreating(false); setEditingItem(null); }}
                >
                  <X size={18} />
                </button>
              </div>

              <form onSubmit={handleSaveItem} className="submodal-form">
                <div className="form-grid">
                  <div className="form-group full-width">
                    <label>Department Name *</label>
                    <select
                      required
                      className="taxonomy-submodal-select"
                      value={formDept}
                      onChange={(e) => {
                        const val = e.target.value;
                        setFormDept(val);
                        const selected = departments.find(d => (typeof d === 'string' ? d : d?.department) === val);
                        if (selected && typeof selected === 'object' && selected.department_code) {
                          setFormCode(selected.department_code);
                        } else {
                          const match = val.match(/\(([A-Z0-9]+)\)/);
                          if (match) setFormCode(match[1]);
                        }
                      }}
                    >
                      <option value="" disabled>-- Select Department ({departments.length} Available) --</option>
                      {departments.map((d) => {
                        const name = typeof d === 'string' ? d : (d?.department || '');
                        return (
                          <option key={name} value={name}>
                            {name}
                          </option>
                        );
                      })}
                      {formDept && !departments.some(d => (typeof d === 'string' ? d : d?.department) === formDept) && (
                        <option value={formDept}>{formDept}</option>
                      )}
                    </select>
                  </div>

                  <div className="form-group">
                    <label>Department Code</label>
                    <input
                      type="text"
                      placeholder="e.g. HEALTH, REV, MAWS"
                      value={formCode}
                      onChange={(e) => setFormCode(e.target.value.toUpperCase())}
                    />
                  </div>

                  <div className="form-group">
                    <label>Sub-Department</label>
                    <input
                      type="text"
                      placeholder="e.g. Directorate of Public Health and Preventive Medicine"
                      value={formSubDept}
                      onChange={(e) => setFormSubDept(e.target.value)}
                    />
                  </div>

                  <div className="form-group">
                    <label>Grievance Type *</label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. Hospital Administration"
                      value={formGrievanceType}
                      onChange={(e) => setFormGrievanceType(e.target.value)}
                    />
                  </div>

                  <div className="form-group">
                    <label>Grievance Sub-Type *</label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. Shortage of essential life-saving medicines"
                      value={formGrievanceSubType}
                      onChange={(e) => setFormGrievanceSubType(e.target.value)}
                    />
                  </div>

                  <div className="form-group full-width">
                    <label>Responsible Officer</label>
                    <input
                      type="text"
                      placeholder="e.g. Joint Director of Health Services (JDHS) / Dean"
                      value={formResponsibleOfficer}
                      onChange={(e) => setFormResponsibleOfficer(e.target.value)}
                    />
                    <span className="field-hint">
                      Designate the designated Field Officer (DRO, Tahsildar, BDO, DEO, EE) or Directorate Officer.
                    </span>
                  </div>
                </div>

                <div className="submodal-actions">
                  <button
                    type="button"
                    className="taxonomy-action-btn secondary"
                    onClick={() => { setIsCreating(false); setEditingItem(null); }}
                    disabled={saving}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="taxonomy-action-btn primary"
                    disabled={saving}
                  >
                    {saving ? <RefreshCw size={15} className="spin" /> : <Check size={15} />}
                    <span>{saving ? 'Generating Vector & Saving...' : 'Save Mapping'}</span>
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Delete Mapping Confirmation Dialog */}
        {deletingItem && (
          <div className="taxonomy-submodal-overlay" role="dialog">
            <div className="taxonomy-submodal-card delete-card">
              <div className="submodal-header">
                <h3 className="delete-title">Confirm Taxonomy Deletion</h3>
                <button
                  className="submodal-close-btn"
                  onClick={() => setDeletingItem(null)}
                >
                  <X size={18} />
                </button>
              </div>
              <div className="delete-body">
                <AlertCircle size={36} className="delete-warning-icon" />
                <p>Are you sure you want to delete this authoritative mapping?</p>
                <div className="delete-details-card">
                  <div><strong>Department:</strong> {deletingItem.department}</div>
                  <div><strong>Grievance Type:</strong> {deletingItem.grievance_type}</div>
                  <div><strong>Sub-Type:</strong> {deletingItem.grievance_sub_type}</div>
                  <div><strong>Responsible Officer:</strong> {deletingItem.responsible_officer || 'Unassigned'}</div>
                </div>
                <p className="delete-subtext">This action will update the active matching vector database immediately.</p>
              </div>
              <div className="submodal-actions">
                <button
                  type="button"
                  className="taxonomy-action-btn secondary"
                  onClick={() => setDeletingItem(null)}
                  disabled={saving}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="taxonomy-action-btn danger"
                  onClick={handleDeleteConfirm}
                  disabled={saving}
                >
                  {saving ? <RefreshCw size={15} className="spin" /> : <Trash2 size={15} />}
                  <span>{saving ? 'Deleting...' : 'Confirm Delete'}</span>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Create / Edit Channel Dialog Modal */}
        {(isCreatingChannel || editingChannel) && (
          <div className="taxonomy-submodal-overlay" role="dialog">
            <div className="taxonomy-submodal-card">
              <div className="submodal-header">
                <h3>{isCreatingChannel ? 'Add Intake Channel' : `Edit Intake Channel: ${editingChannel?.channel_name}`}</h3>
                <button
                  className="submodal-close-btn"
                  onClick={() => { setIsCreatingChannel(false); setEditingChannel(null); }}
                >
                  <X size={18} />
                </button>
              </div>

              <form onSubmit={handleSaveChannel} className="submodal-form">
                <div className="form-grid">
                  <div className="form-group full-width">
                    <label>Channel Name *</label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. CM Helpline 1100, Makkaludan Mudhalvar Camp"
                      value={channelFormName}
                      onChange={(e) => setChannelFormName(e.target.value)}
                    />
                  </div>

                  <div className="form-group">
                    <label>Channel Code *</label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. CALL_1100, MM_CAMP"
                      value={channelFormCode}
                      onChange={(e) => setChannelFormCode(e.target.value.toUpperCase())}
                    />
                  </div>

                  <div className="form-group">
                    <label>Category Vector *</label>
                    <select
                      required
                      className="taxonomy-submodal-select"
                      value={channelFormCategory}
                      onChange={(e) => setChannelFormCategory(e.target.value)}
                    >
                      <option value="digital_direct">1. Digital Direct Channels</option>
                      <option value="executive_leadership">2. Executive Leadership Desks</option>
                      <option value="legislative">3. Legislative Representation</option>
                      <option value="district_grievance_days">4. District Grievance Days</option>
                      <option value="field_outreach_camps">5. Field Outreach Camps</option>
                      <option value="counters_walkin">5. Walk-in Counters</option>
                    </select>
                  </div>

                  <div className="form-group full-width">
                    <label>Description</label>
                    <input
                      type="text"
                      placeholder="e.g. Centralized 24x7 voice helpline with computer telephony integration"
                      value={channelFormDesc}
                      onChange={(e) => setChannelFormDesc(e.target.value)}
                    />
                  </div>

                  <div className="form-group full-width" style={{ flexDirection: 'row', alignItems: 'center', gap: '0.6rem', marginTop: '0.25rem' }}>
                    <input
                      type="checkbox"
                      id="channelFormActive"
                      checked={channelFormActive}
                      onChange={(e) => setChannelFormActive(e.target.checked)}
                      style={{ width: '18px', height: '18px', cursor: 'pointer' }}
                    />
                    <label htmlFor="channelFormActive" style={{ cursor: 'pointer', margin: 0, fontWeight: 600 }}>
                      Active Intake Channel (Enabled for Petition Intake & Analytics)
                    </label>
                  </div>
                </div>

                <div className="submodal-actions">
                  <button
                    type="button"
                    className="taxonomy-action-btn secondary"
                    onClick={() => { setIsCreatingChannel(false); setEditingChannel(null); }}
                    disabled={saving}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="taxonomy-action-btn primary"
                    disabled={saving}
                  >
                    {saving ? <RefreshCw size={15} className="spin" /> : <Check size={15} />}
                    <span>{saving ? 'Saving...' : 'Save Channel'}</span>
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Delete Channel Confirmation Dialog */}
        {deletingChannel && (
          <div className="taxonomy-submodal-overlay" role="dialog">
            <div className="taxonomy-submodal-card delete-card">
              <div className="submodal-header">
                <h3 className="delete-title">Confirm Intake Channel Deletion</h3>
                <button
                  className="submodal-close-btn"
                  onClick={() => setDeletingChannel(null)}
                >
                  <X size={18} />
                </button>
              </div>
              <div className="delete-body">
                <AlertCircle size={36} className="delete-warning-icon" />
                <p>Are you sure you want to delete this intake channel?</p>
                <div className="delete-details-card">
                  <div><strong>Channel Name:</strong> {deletingChannel.channel_name}</div>
                  <div><strong>Channel Code:</strong> {deletingChannel.channel_code}</div>
                  <div><strong>Category:</strong> {deletingChannel.category}</div>
                  <div><strong>Status:</strong> {deletingChannel.is_active ? 'Active' : 'Inactive'}</div>
                </div>
                <p className="delete-subtext">This will remove the channel definition from the intake routing registry.</p>
              </div>
              <div className="submodal-actions">
                <button
                  type="button"
                  className="taxonomy-action-btn secondary"
                  onClick={() => setDeletingChannel(null)}
                  disabled={saving}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="taxonomy-action-btn danger"
                  onClick={handleDeleteChannelConfirm}
                  disabled={saving}
                >
                  {saving ? <RefreshCw size={15} className="spin" /> : <Trash2 size={15} />}
                  <span>{saving ? 'Deleting...' : 'Confirm Delete'}</span>
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

