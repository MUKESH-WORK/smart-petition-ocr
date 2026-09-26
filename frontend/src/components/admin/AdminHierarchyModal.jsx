import React, { useState, useEffect } from 'react';
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
  Check 
} from 'lucide-react';
import { getOfficerId } from '../../services/apiService';
import './AdminHierarchyModal.css';

// Helper to determine badge color class for Local Body Classification
const getLocalBodyClass = (localBody) => {
  if (!localBody) return 'panchayats';
  const lb = localBody.toLowerCase();
  if (lb.includes('corporation')) return 'corporation';
  if (lb.includes('municipality') || lb.includes('municipalities')) return 'municipality';
  if (lb.includes('tribal') || lb.includes('hill')) return 'tribal';
  return 'panchayats';
};

export default function AdminHierarchyModal({ onClose }) {
  // Pure real database state - zero hardcoded data
  const [district, setDistrict] = useState({ name: '', nameTamil: '' });
  const [divisions, setDivisions] = useState([]);
  const [activeTab, setActiveTab] = useState('all'); // 'all' | division name
  const [editingTaluk, setEditingTaluk] = useState(null); // When set, opens Image 2 modal
  const [loading, setLoading] = useState(true);
  const [feedback, setFeedback] = useState(null);

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

  // Determine list of taluks to show based on active tab
  const visibleTaluks = activeTab === 'all'
    ? divisions.flatMap(d => (d.taluks || []).map(t => ({ ...t, division: t.division || d.name })))
    : (divisions.find(d => d.name === activeTab)?.taluks || []).map(t => ({ ...t, division: activeTab }));

  // Open Edit Modal (matching Image 2)
  const handleEditTaluk = (taluk) => {
    setEditingTaluk({
      isNew: false,
      division: taluk.division || (divisions[0]?.name || ''),
      taluk: taluk.name || '',
      talukTamil: taluk.nameTamil || '',
      subDepartmentsStr: (taluk.subDepartments || []).join(', '),
      localBody: taluk.localBody || '',
      firkasStr: (taluk.firkas || []).join(', ')
    });
  };

  // Open Add Taluk Modal
  const handleOpenAddTaluk = () => {
    const defaultDiv = activeTab === 'all' ? (divisions[0]?.name || '') : activeTab;
    setEditingTaluk({
      isNew: true,
      division: defaultDiv,
      taluk: '',
      talukTamil: '',
      subDepartmentsStr: '',
      localBody: '',
      firkasStr: ''
    });
  };

  // Quick inline Firka Add
  const handleAddFirkaQuick = (taluk) => {
    const name = window.prompt(`Enter new Firka name for Taluk "${taluk.name}":`);
    if (!name || !name.trim()) return;
    const cleanName = name.trim();
    if (taluk.firkas && taluk.firkas.some(f => f.toLowerCase() === cleanName.toLowerCase())) {
      alert(`Firka "${cleanName}" already exists in ${taluk.name} Taluk.`);
      return;
    }

    const updatedTaluk = {
      ...taluk,
      firkas: [...(taluk.firkas || []), cleanName]
    };
    saveTalukToBackend(taluk.division, updatedTaluk);
  };

  // Quick inline Firka Remove (x button on chip)
  const handleRemoveFirka = async (taluk, firkaToRemove) => {
    if ((taluk.firkas || []).length <= 1) {
      alert('A Taluk must have at least one Firka in the administrative database.');
      return;
    }
    const updatedTaluk = {
      ...taluk,
      firkas: taluk.firkas.filter(f => f !== firkaToRemove)
    };
    saveTalukToBackend(taluk.division, updatedTaluk);
  };

  // Remove Entire Taluk
  const handleRemoveTaluk = async (taluk) => {
    if (!window.confirm(`Are you sure you want to remove Taluk "${taluk.name}" from ${taluk.division}? This will delete all its firkas and vector indexes from the database.`)) {
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

  // Save Taluk from Modal Form (Image 2)
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
      firkas: firkas.length > 0 ? firkas : [editingTaluk.taluk.trim()]
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
        firkas: talukData.firkas || []
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
          message: `Taluk "${payload.taluk}" saved to Admin DB and synchronized with 384-d RAG vectors.` 
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
            </div>
            <p className="hierarchy-subtitle">
              Authoritative district administrative hierarchy for {district.name ? `${district.name} Collectorate` : 'Collectorate'}. All taluks and firkas are synchronized for grievance routing.
            </p>
          </div>
          <button className="hierarchy-close-btn" onClick={onClose} aria-label="Close modal">
            <X size={20} />
          </button>
        </header>

        {/* Controls Bar matching Image 1 */}
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
            <span className="hierarchy-firkas-count">
              {totalFirkasCount} Total Firkas Indexed
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

                  {/* Section 1: SUB-DEPARTMENTS (Clean structured data) */}
                  <div className="taluk-data-row">
                    <span className="taluk-data-label">
                      <Landmark size={13} className="taluk-section-icon" />
                      Sub-Departments:
                    </span>
                    <p className="taluk-data-value">{subDepts}</p>
                  </div>

                  {/* Section 2: AVAILABLE FIRKAS (Clean structured data) */}
                  <div className="taluk-data-row">
                    <span className="taluk-data-label">
                      <Tag size={13} className="taluk-section-icon" />
                      Firkas ({taluk.firkas?.length || 0}):
                    </span>
                    <p className="taluk-data-value">{firkasList}</p>
                  </div>

                  {/* Card Actions Footer (Only Edit Taluk and Remove) */}
                  <div className="taluk-card-actions">
                    <button
                      type="button"
                      className="btn-card-action edit"
                      onClick={() => handleEditTaluk(taluk)}
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

      {/* Edit Taluk Modal Dialog (Matching Image 2 with Pixel Perfection) */}
      {editingTaluk && (
        <div
          className="edit-taluk-overlay"
          role="dialog"
          aria-modal="true"
          onClick={() => setEditingTaluk(null)}
        >
          <div className="edit-taluk-modal" onClick={(e) => e.stopPropagation()}>
            <div className="edit-taluk-header">
              <h3>{editingTaluk.isNew ? 'Add New Taluk' : `Edit Taluk: ${editingTaluk.taluk}`}</h3>
              <button
                type="button"
                className="hierarchy-close-btn"
                onClick={() => setEditingTaluk(null)}
                aria-label="Close edit dialog"
              >
                <X size={18} />
              </button>
            </div>

            <div className="edit-taluk-body">
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
