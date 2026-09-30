import React, { useState, useEffect, useMemo } from 'react';
import { 
  Layers, 
  RefreshCw, 
  Plus, 
  Pencil, 
  Trash2, 
  Landmark, 
  MapPin, 
  Tag, 
  X, 
  Check,
  Search,
  Building2,
  Home,
  Trees,
  Filter,
  Eye,
  FileSpreadsheet,
  AlertCircle
} from 'lucide-react';
import { getOfficerId } from '../../services/apiService';
import './AdminHierarchyModal.css';

export default function AdminHierarchyModal({ onClose }) {
  // Database state
  const [district, setDistrict] = useState({ name: '', nameTamil: '' });
  const [divisions, setDivisions] = useState([]);
  const [activeTab, setActiveTab] = useState('all'); // 'all' | division name
  const [editingTaluk, setEditingTaluk] = useState(null); // When set, opens Edit/Add modal
  const [editActiveTab, setEditActiveTab] = useState('overview'); // 'overview' | 'villages'
  const [loading, setLoading] = useState(true);
  const [feedback, setFeedback] = useState(null);

  // Village search & filters inside Edit modal
  const [villageSearch, setVillageSearch] = useState('');
  const [villageCategoryFilter, setVillageCategoryFilter] = useState('all'); // 'all' | 'Rural' | 'Urban'
  const [newVillageName, setNewVillageName] = useState('');
  const [newVillageCategory, setNewVillageCategory] = useState('Rural');
  const [newVillageGP, setNewVillageGP] = useState('');

  // Fetch live hierarchy directly from backend Admin DB master_locations
  const loadHierarchy = async () => {
    try {
      setLoading(true);
      const res = await fetch('/api/v1/admin/hierarchy', {
        headers: { 'X-Officer-Id': getOfficerId() }
      });
      if (res.ok) {
        const data = await res.json();
        setDistrict(data.district || { name: '', nameTamil: '' });
        setDivisions(data.divisions || []);
      } else {
        const errData = await res.json().catch(() => ({}));
        setFeedback({ 
          type: 'error', 
          message: errData.detail || 'Failed to fetch live hierarchy from Admin DB.' 
        });
      }
    } catch (err) {
      console.error('Failed to load hierarchy:', err);
      setFeedback({ 
        type: 'error', 
        message: 'Network error connecting to Admin DB: ' + err.message 
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHierarchy();
  }, []);

  // Compute live aggregate statistics directly from DB state
  const totalTaluksCount = divisions.reduce((acc, d) => acc + (d.taluks?.length || 0), 0);
  const totalFirkasCount = divisions.reduce(
    (acc, d) => acc + (d.taluks || []).reduce((tAcc, t) => tAcc + (t.firkas?.length || 0), 0),
    0
  );
  const totalVillagesCount = divisions.reduce(
    (acc, d) => acc + (d.taluks || []).reduce((tAcc, t) => tAcc + (t.totalVillages || t.villages?.length || 0), 0),
    0
  );

  // Determine list of taluks to show based on active tab
  const visibleTaluks = activeTab === 'all'
    ? divisions.flatMap(d => (d.taluks || []).map(t => ({ ...t, division: t.division || d.name })))
    : (divisions.find(d => d.name === activeTab)?.taluks || []).map(t => ({ ...t, division: activeTab }));

  // Open Edit Modal
  const handleEditTaluk = (taluk, initialTab = 'overview') => {
    setEditActiveTab(initialTab);
    setVillageSearch('');
    setVillageCategoryFilter('all');
    setEditingTaluk({
      isNew: false,
      division: taluk.division || (divisions[0]?.name || ''),
      taluk: taluk.name || '',
      talukTamil: taluk.nameTamil || '',
      subDepartmentsStr: (taluk.subDepartments || []).join(', '),
      localBody: taluk.localBody || '',
      firkasStr: (taluk.firkas || []).join(', '),
      villages: taluk.villages ? [...taluk.villages] : []
    });
  };

  // Open Add Taluk Modal
  const handleOpenAddTaluk = () => {
    const defaultDiv = activeTab === 'all' ? (divisions[0]?.name || '') : activeTab;
    setEditActiveTab('overview');
    setVillageSearch('');
    setVillageCategoryFilter('all');
    setEditingTaluk({
      isNew: true,
      division: defaultDiv,
      taluk: '',
      talukTamil: '',
      subDepartmentsStr: '',
      localBody: '',
      firkasStr: '',
      villages: []
    });
  };

  // Add Village inline in edit modal
  const handleAddVillageInline = () => {
    if (!newVillageName.trim()) {
      alert('Please enter a village name.');
      return;
    }
    const cleanName = newVillageName.trim();
    const currentVillages = editingTaluk.villages || [];
    if (currentVillages.some(v => v.name.toLowerCase() === cleanName.toLowerCase())) {
      alert(`Village "${cleanName}" already exists in this taluk.`);
      return;
    }

    const newVillage = {
      name: cleanName,
      nameTamil: cleanName,
      category: newVillageCategory,
      gramPanchayat: newVillageCategory === 'Urban' ? 'Not applicable' : (newVillageGP.trim() || cleanName)
    };

    setEditingTaluk({
      ...editingTaluk,
      villages: [...currentVillages, newVillage]
    });
    setNewVillageName('');
    setNewVillageGP('');
  };

  // Remove Village inline in edit modal
  const handleRemoveVillageInline = (indexToRemove) => {
    const currentVillages = editingTaluk.villages || [];
    const updated = currentVillages.filter((_, idx) => idx !== indexToRemove);
    setEditingTaluk({
      ...editingTaluk,
      villages: updated
    });
  };

  // Filtered villages list for the Villages tab
  const filteredVillages = useMemo(() => {
    if (!editingTaluk || !editingTaluk.villages) return [];
    return editingTaluk.villages.filter(v => {
      const matchSearch = villageSearch === '' || 
        v.name.toLowerCase().includes(villageSearch.toLowerCase()) ||
        (v.gramPanchayat && v.gramPanchayat.toLowerCase().includes(villageSearch.toLowerCase()));
      const matchCat = villageCategoryFilter === 'all' || v.category === villageCategoryFilter;
      return matchSearch && matchCat;
    });
  }, [editingTaluk, villageSearch, villageCategoryFilter]);

  // Remove Entire Taluk
  const handleRemoveTaluk = async (taluk) => {
    if (!window.confirm(`Are you sure you want to remove Taluk "${taluk.name}" from ${taluk.division}? This will delete all its firkas, villages, and vector indexes from the database.`)) {
      return;
    }

    try {
      setLoading(true);
      const res = await fetch(`/api/v1/admin/hierarchy/taluk?division=${encodeURIComponent(taluk.division)}&taluk=${encodeURIComponent(taluk.name)}`, {
        method: 'DELETE',
        headers: { 'X-Officer-Id': getOfficerId() }
      });
      if (res.ok) {
        setFeedback({ type: 'success', message: `Taluk "${taluk.name}" removed from Admin DB successfully.` });
        await loadHierarchy();
      } else {
        const errData = await res.json().catch(() => ({}));
        setFeedback({ type: 'error', message: errData.detail || 'Could not delete taluk from database.' });
      }
    } catch (err) {
      setFeedback({ type: 'error', message: 'Failed to delete taluk: ' + err.message });
    } finally {
      setLoading(false);
    }
  };

  // Save Taluk from Modal Form
  const handleSaveTalukForm = async () => {
    if (!editingTaluk.taluk.trim()) {
      alert('Please enter a Taluk name in English.');
      return;
    }

    const subDepts = editingTaluk.subDepartmentsStr
      .split(',')
      .map(s => s.trim())
      .filter(Boolean);

    const firkas = editingTaluk.firkasStr
      .split(',')
      .map(s => s.trim())
      .filter(Boolean);

    await saveTalukToBackend(editingTaluk.division, {
      taluk: editingTaluk.taluk.trim(),
      talukTamil: editingTaluk.talukTamil?.trim() || '',
      subDepartments: subDepts,
      localBody: editingTaluk.localBody?.trim() || '',
      firkas: firkas.length > 0 ? firkas : [editingTaluk.taluk.trim()],
      villages: editingTaluk.villages
    });
  };

  // Core backend persistence & 384-d vector embedding generator
  const saveTalukToBackend = async (divisionName, talukData) => {
    setLoading(true);
    try {
      const payload = {
        division: divisionName,
        taluk: talukData.taluk || talukData.name,
        taluk_tamil: talukData.talukTamil || talukData.nameTamil || '',
        sub_departments: talukData.subDepartments || [],
        local_body: talukData.localBody || '',
        firkas: talukData.firkas || [],
        villages: talukData.villages || []
      };

      const res = await fetch('/api/v1/admin/hierarchy/taluk', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Officer-Id': getOfficerId()
        },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        setFeedback({ 
          type: 'success', 
          message: `Taluk "${payload.taluk}" saved with ${payload.villages.length} villages and synchronized with 384-d RAG vectors.` 
        });
        setEditingTaluk(null);
        await loadHierarchy();
      } else {
        const errData = await res.json().catch(() => ({}));
        setFeedback({ type: 'error', message: errData.detail || 'Could not save taluk.' });
      }
    } catch (err) {
      setFeedback({ type: 'error', message: 'Error saving: ' + err.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="hierarchy-overlay" role="dialog" aria-modal="true">
      <div className="hierarchy-dialog">
        {/* Header */}
        <header className="hierarchy-header">
          <div className="hierarchy-header-content">
            <div className="hierarchy-title-row">
              <Layers size={22} className="hierarchy-title-icon" />
              <h2>Administrative Hierarchy &amp; Revenue Jurisdiction</h2>
              <span className="hierarchy-badge-rag">
                <span className="hierarchy-rag-dot"></span>
                RAG Vector Synchronized
              </span>
            </div>
            <p className="hierarchy-subtitle">
              Authoritative district administrative hierarchy for {district.name ? `${district.name} District (${district.nameTamil || 'ஈரோடு'})` : 'Erode District'}. All taluks, firkas, and {totalVillagesCount} revenue villages are indexed for leaf-to-root grievance routing.
            </p>
          </div>
          <button className="hierarchy-close-btn" onClick={onClose} aria-label="Close modal">
            <X size={20} />
          </button>
        </header>

        {/* Controls Bar */}
        <div className="hierarchy-controls-bar">
          <div className="hierarchy-filter-pills">
            <button
              type="button"
              className={`hierarchy-pill-btn ${activeTab === 'all' ? 'active' : ''}`}
              onClick={() => setActiveTab('all')}
            >
              All Taluks ({totalTaluksCount})
            </button>
            {divisions.map((div) => (
              <button
                type="button"
                key={div.name}
                className={`hierarchy-pill-btn ${activeTab === div.name ? 'active' : ''}`}
                onClick={() => setActiveTab(div.name)}
              >
                {div.name} ({div.taluks?.length || 0})
              </button>
            ))}
          </div>

          <div className="hierarchy-actions-right">
            <span className="hierarchy-stats-badge">
              <Trees size={13} /> {totalVillagesCount} Villages
            </span>
            <span className="hierarchy-stats-badge">
              <Tag size={13} /> {totalFirkasCount} Firkas
            </span>
            <button
              type="button"
              className="hierarchy-btn-refresh"
              onClick={loadHierarchy}
              title="Refresh from Admin DB"
              disabled={loading}
            >
              <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
              Refresh
            </button>
            <button
              type="button"
              className="hierarchy-btn-add"
              onClick={handleOpenAddTaluk}
            >
              <Plus size={14} />
              Add Taluk
            </button>
          </div>
        </div>

        {/* Main Content Area */}
        <div className="hierarchy-content">
          {feedback && (
            <div
              style={{
                padding: '0.65rem 1rem',
                marginBottom: '1.25rem',
                borderRadius: '8px',
                background: feedback.type === 'success' ? '#dcfce7' : '#fee2e2',
                color: feedback.type === 'success' ? '#15803d' : '#b91c1c',
                fontSize: '0.85rem',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between'
              }}
            >
              <span>{feedback.message}</span>
              <button
                onClick={() => setFeedback(null)}
                style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'inherit', fontSize: '1.1rem' }}
              >
                &times;
              </button>
            </div>
          )}

          {/* Loading State */}
          {loading && divisions.length === 0 && (
            <div style={{ textAlign: 'center', padding: '3rem 1rem', color: '#64748b' }}>
              <RefreshCw size={32} className="animate-spin" style={{ margin: '0 auto 1rem auto', display: 'block', color: '#0d9488' }} />
              <p style={{ fontWeight: 600, fontSize: '0.95rem' }}>Loading live administrative hierarchy from Admin DB...</p>
            </div>
          )}

          {/* Empty State */}
          {!loading && divisions.length === 0 && (
            <div style={{ textAlign: 'center', padding: '3rem 1rem', color: '#64748b' }}>
              <p style={{ fontWeight: 600, fontSize: '0.95rem' }}>No administrative divisions found in the database.</p>
              <button 
                type="button" 
                className="hierarchy-btn-add" 
                style={{ marginTop: '1rem', display: 'inline-flex' }}
                onClick={handleOpenAddTaluk}
              >
                <Plus size={14} /> Add First Taluk
              </button>
            </div>
          )}

          {/* 3-Column Taluk Card Grid */}
          <div className="hierarchy-taluk-grid">
            {visibleTaluks.map((taluk) => {
              const subDepts = taluk.subDepartments && taluk.subDepartments.length > 0
                ? taluk.subDepartments.join(', ')
                : 'General Administration';
              const firkasList = taluk.firkas && taluk.firkas.length > 0
                ? taluk.firkas.join(', ')
                : 'None configured';
              const villageCount = taluk.totalVillages || taluk.villages?.length || 0;
              const ruralCount = taluk.ruralCount ?? (taluk.villages?.filter(v => v.category === 'Rural').length || 0);
              const urbanCount = taluk.urbanCount ?? (taluk.villages?.filter(v => v.category === 'Urban').length || 0);

              return (
                <article className="taluk-card" key={`${taluk.division}-${taluk.name}`}>
                  {/* Card Header: Title + Division */}
                  <div className="taluk-card-header">
                    <div className="taluk-title-area">
                      <h3>
                        {taluk.name} Taluk
                        {taluk.nameTamil && (
                          <span className="taluk-tamil-title"> ({taluk.nameTamil})</span>
                        )}
                      </h3>
                    </div>
                    <span className="taluk-division-label" title={taluk.division || ''}>
                      {taluk.division ? taluk.division.replace(/\s*Division/i, '').toUpperCase() : ''}
                    </span>
                  </div>

                  {/* Section 1: SUB-DEPARTMENTS */}
                  <div className="taluk-data-row">
                    <span className="taluk-data-label">
                      <Landmark size={13} className="taluk-section-icon" />
                      Sub-Departments:
                    </span>
                    <p className="taluk-data-value">{subDepts}</p>
                  </div>

                  {/* Section 2: AVAILABLE FIRKAS */}
                  <div className="taluk-data-row">
                    <span className="taluk-data-label">
                      <Tag size={13} className="taluk-section-icon" />
                      Firkas ({taluk.firkas?.length || 0}):
                    </span>
                    <p className="taluk-data-value">{firkasList}</p>
                  </div>

                  {/* Section 3: VILLAGES SUMMARY BADGE */}
                  <div className="taluk-data-row taluk-villages-summary-row">
                    <span className="taluk-data-label">
                      <Trees size={13} className="taluk-section-icon" />
                      Revenue Villages ({villageCount}):
                    </span>
                    <div className="taluk-villages-badge-group">
                      <span className="badge-village-stat rural">{ruralCount} Rural</span>
                      <span className="badge-village-stat urban">{urbanCount} Urban</span>
                      <button 
                        type="button" 
                        className="btn-view-villages-chip"
                        onClick={() => handleEditTaluk(taluk, 'villages')}
                        title="View and manage all revenue villages for this taluk"
                      >
                        <Eye size={12} /> View Directory
                      </button>
                    </div>
                  </div>

                  {/* Card Actions Footer */}
                  <div className="taluk-card-actions">
                    <button
                      type="button"
                      className="btn-card-action edit"
                      onClick={() => handleEditTaluk(taluk, 'overview')}
                    >
                      <Pencil size={13} /> Edit Taluk
                    </button>
                    <button
                      type="button"
                      className="btn-card-action remove"
                      onClick={() => handleRemoveTaluk(taluk)}
                    >
                      <Trash2 size={13} /> Remove
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
        </div>
      </div>

      {/* Edit Taluk Modal Dialog with Tabs for Overview & Villages */}
      {editingTaluk && (
        <div
          className="edit-taluk-overlay"
          role="dialog"
          aria-modal="true"
          onClick={() => setEditingTaluk(null)}
        >
          <div className="edit-taluk-modal" onClick={(e) => e.stopPropagation()}>
            <div className="edit-taluk-header">
              <div>
                <h3>{editingTaluk.isNew ? 'Add New Taluk' : `Edit Taluk: ${editingTaluk.taluk}`}</h3>
                <p className="edit-taluk-subheader">
                  {editingTaluk.division} &bull; {editingTaluk.villages?.length || 0} Villages Configured
                </p>
              </div>
              <button
                type="button"
                className="hierarchy-close-btn"
                onClick={() => setEditingTaluk(null)}
                aria-label="Close edit dialog"
              >
                <X size={18} />
              </button>
            </div>

            {/* Edit Modal Nav Tabs */}
            <div className="edit-modal-tabs">
              <button
                type="button"
                className={`edit-tab-btn ${editActiveTab === 'overview' ? 'active' : ''}`}
                onClick={() => setEditActiveTab('overview')}
              >
                <Landmark size={15} />
                Overview &amp; Firkas
              </button>
              <button
                type="button"
                className={`edit-tab-btn ${editActiveTab === 'villages' ? 'active' : ''}`}
                onClick={() => setEditActiveTab('villages')}
              >
                <Trees size={15} />
                Revenue Villages ({editingTaluk.villages?.length || 0})
              </button>
            </div>

            <div className="edit-taluk-body">
              {/* TAB 1: OVERVIEW & FIRKAS */}
              {editActiveTab === 'overview' && (
                <div className="edit-tab-content">
                  <div className="edit-taluk-field">
                    <label>Revenue Division</label>
                    <select
                      value={editingTaluk.division}
                      onChange={(e) => setEditingTaluk({ ...editingTaluk, division: e.target.value })}
                    >
                      {divisions.map((div) => (
                        <option key={div.name} value={div.name}>
                          {div.name} {div.nameTamil ? `(${div.nameTamil})` : ''}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="edit-taluk-field">
                    <label>Taluk Name (English)</label>
                    <input
                      type="text"
                      value={editingTaluk.taluk}
                      disabled={!editingTaluk.isNew}
                      onChange={(e) => setEditingTaluk({ ...editingTaluk, taluk: e.target.value })}
                      placeholder="e.g. Taluk Name"
                    />
                    <span className="field-helper">Taluk identifier is fixed. To rename, remove and re-add.</span>
                  </div>

                  <div className="edit-taluk-field">
                    <label>Taluk Name (Tamil / தமிழ்)</label>
                    <input
                      type="text"
                      value={editingTaluk.talukTamil || ''}
                      onChange={(e) => setEditingTaluk({ ...editingTaluk, talukTamil: e.target.value })}
                      placeholder="e.g. தமிழ் பெயர்"
                    />
                  </div>

                  <div className="edit-taluk-field">
                    <label>Sub-Departments (comma-separated badges)</label>
                    <input
                      type="text"
                      value={editingTaluk.subDepartmentsStr}
                      onChange={(e) => setEditingTaluk({ ...editingTaluk, subDepartmentsStr: e.target.value })}
                      placeholder="Revenue, Civil Supplies, Land Records"
                    />
                    <span className="field-helper">Badges shown on the Taluk card (e.g. Revenue, Civil Supplies, Land Records)</span>
                  </div>

                  <div className="edit-taluk-field">
                    <label>Local Body Classification</label>
                    <input
                      type="text"
                      value={editingTaluk.localBody}
                      onChange={(e) => setEditingTaluk({ ...editingTaluk, localBody: e.target.value })}
                      placeholder="e.g. City Municipal Corporation, Municipality, Town Panchayats"
                    />
                    <span className="field-helper">e.g. City Municipal Corporation, Municipality, Rural Town Panchayats, Tribal Hill Panchayats</span>
                  </div>

                  <div className="edit-taluk-field">
                    <label>Available Firkas (comma-separated)</label>
                    <textarea
                      rows={3}
                      value={editingTaluk.firkasStr}
                      onChange={(e) => setEditingTaluk({ ...editingTaluk, firkasStr: e.target.value })}
                      placeholder="Firka 1, Firka 2, Firka 3"
                    />
                  </div>
                </div>
              )}

              {/* TAB 2: REVENUE VILLAGES & GRAM PANCHAYATS DIRECTORY */}
              {editActiveTab === 'villages' && (
                <div className="edit-tab-content villages-tab-content">
                  {/* Inline Add Village Form */}
                  <div className="add-village-box">
                    <h4>Add Revenue Village to {editingTaluk.taluk}</h4>
                    <div className="add-village-grid">
                      <div className="add-v-input">
                        <label>Village Name</label>
                        <input
                          type="text"
                          placeholder="e.g. Alathur"
                          value={newVillageName}
                          onChange={(e) => setNewVillageName(e.target.value)}
                        />
                      </div>
                      <div className="add-v-input cat">
                        <label>Category</label>
                        <select
                          value={newVillageCategory}
                          onChange={(e) => setNewVillageCategory(e.target.value)}
                        >
                          <option value="Rural">Rural</option>
                          <option value="Urban">Urban</option>
                        </select>
                      </div>
                      <div className="add-v-input gp">
                        <label>Gram Panchayat</label>
                        <input
                          type="text"
                          placeholder={newVillageCategory === 'Urban' ? 'Not applicable' : 'e.g. Alathur'}
                          disabled={newVillageCategory === 'Urban'}
                          value={newVillageCategory === 'Urban' ? 'Not applicable' : newVillageGP}
                          onChange={(e) => setNewVillageGP(e.target.value)}
                        />
                      </div>
                      <button
                        type="button"
                        className="btn-add-village-submit"
                        onClick={handleAddVillageInline}
                      >
                        <Plus size={15} /> Add Village
                      </button>
                    </div>
                  </div>

                  {/* Search and Filters Header */}
                  <div className="villages-table-controls">
                    <div className="village-search-bar">
                      <Search size={15} className="v-search-icon" />
                      <input
                        type="text"
                        placeholder="Search village or Gram Panchayat..."
                        value={villageSearch}
                        onChange={(e) => setVillageSearch(e.target.value)}
                      />
                      {villageSearch && (
                        <button 
                          className="v-search-clear" 
                          onClick={() => setVillageSearch('')}
                        >
                          &times;
                        </button>
                      )}
                    </div>

                    <div className="village-filter-pills">
                      <button
                        type="button"
                        className={`v-filter-pill ${villageCategoryFilter === 'all' ? 'active' : ''}`}
                        onClick={() => setVillageCategoryFilter('all')}
                      >
                        All ({editingTaluk.villages?.length || 0})
                      </button>
                      <button
                        type="button"
                        className={`v-filter-pill ${villageCategoryFilter === 'Rural' ? 'active' : ''}`}
                        onClick={() => setVillageCategoryFilter('Rural')}
                      >
                        Rural ({editingTaluk.villages?.filter(v => v.category === 'Rural').length || 0})
                      </button>
                      <button
                        type="button"
                        className={`v-filter-pill ${villageCategoryFilter === 'Urban' ? 'active' : ''}`}
                        onClick={() => setVillageCategoryFilter('Urban')}
                      >
                        Urban ({editingTaluk.villages?.filter(v => v.category === 'Urban').length || 0})
                      </button>
                    </div>
                  </div>

                  {/* Villages Table */}
                  <div className="villages-table-container">
                    {filteredVillages.length === 0 ? (
                      <div className="villages-empty">
                        <AlertCircle size={28} className="empty-icon" />
                        <p>No revenue villages match the current filter.</p>
                      </div>
                    ) : (
                      <table className="villages-table">
                        <thead>
                          <tr>
                            <th style={{ width: '50px' }}>Sl. No.</th>
                            <th>Village Name</th>
                            <th style={{ width: '100px' }}>Category</th>
                            <th>Gram Panchayat</th>
                            <th style={{ width: '60px', textAlign: 'center' }}>Action</th>
                          </tr>
                        </thead>
                        <tbody>
                          {filteredVillages.map((vill, idx) => {
                            // Find real index in editingTaluk.villages
                            const realIndex = editingTaluk.villages.findIndex(v => v.name === vill.name);
                            return (
                              <tr key={`${vill.name}-${idx}`}>
                                <td className="cell-num">{idx + 1}</td>
                                <td className="cell-name">
                                  <strong>{vill.name}</strong>
                                  {vill.nameTamil && vill.nameTamil !== vill.name && (
                                    <span className="v-tamil-sub"> ({vill.nameTamil})</span>
                                  )}
                                </td>
                                <td>
                                  <span className={`badge-cat ${vill.category.toLowerCase()}`}>
                                    {vill.category}
                                  </span>
                                </td>
                                <td className="cell-gp">
                                  {vill.gramPanchayat || 'Not applicable'}
                                </td>
                                <td style={{ textAlign: 'center' }}>
                                  <button
                                    type="button"
                                    className="btn-del-v"
                                    onClick={() => handleRemoveVillageInline(realIndex)}
                                    title={`Remove ${vill.name}`}
                                  >
                                    <Trash2 size={13} />
                                  </button>
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    )}
                  </div>

                  <div className="villages-footer-summary">
                    Showing {filteredVillages.length} of {editingTaluk.villages?.length || 0} revenue villages in {editingTaluk.taluk} Taluk.
                  </div>
                </div>
              )}
            </div>

            <div className="edit-taluk-footer">
              <button
                type="button"
                className="btn-taluk-cancel"
                onClick={() => setEditingTaluk(null)}
                disabled={loading}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn-taluk-save"
                onClick={handleSaveTalukForm}
                disabled={loading}
              >
                <Check size={16} />
                {loading ? 'Saving Changes…' : 'Save Taluk Changes'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
