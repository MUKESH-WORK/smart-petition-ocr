import React, { useState, useEffect } from 'react';
import { History, FileText, X, ArrowRight, Clock, Loader2 } from 'lucide-react';
import { authHeaders } from '../../services/apiService';
import './HistoryModal.css';

export default function HistoryModal({ 
  isOpen, 
  onClose, 
  currentPetitionId, 
  onSelectPetition,
  officerId = null
}) {
  const [petitions, setPetitions] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isOpen) return;
    setLoading(true);
    const effOfficer = officerId || localStorage.getItem('officer_id') || '';
    const queryParam = effOfficer && effOfficer !== 'all' ? `&officer_id=${encodeURIComponent(effOfficer)}` : '';
    fetch(`/api/v1/grievance/recent?limit=25${queryParam}`, {
      headers: authHeaders()
    })
      .then(res => res.ok ? res.json() : [])
      .then(data => {
        setPetitions(Array.isArray(data) ? data : []);
      })
      .catch(err => {
        console.warn('Could not fetch recent petitions:', err);
        setPetitions([]);
      })
      .finally(() => setLoading(false));
  }, [isOpen, officerId]);

  if (!isOpen) return null;

  return (
    <div className="modal-backdrop" onClick={onClose} role="dialog" aria-modal="true">
      <div className="modal-card history-modal-card" onClick={(e) => e.stopPropagation()}>
        
        {/* Modal Header */}
        <div className="modal-header">
          <div className="modal-title-group">
            <div className="modal-icon-badge navy-badge">
              <History size={18} />
            </div>
            <div>
              <h3 className="modal-title">Audit Logs</h3>
              <p className="modal-subtitle">Recent documents and processing history in this session</p>
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

        {/* Modal Body */}
        <div className="modal-body-scroll">
          {loading ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '40px 0', gap: '8px', color: '#64748b' }}>
              <Loader2 size={20} className="spin" />
              <span>Loading recent documents...</span>
            </div>
          ) : petitions.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px 0', color: '#64748b' }}>
              <p>No recent petition uploads found.</p>
            </div>
          ) : (
            <div className="history-list">
              {petitions.map((pet) => {
                const isCurrent = pet.source_id === currentPetitionId || pet.id === currentPetitionId;

                return (
                  <div 
                    key={pet.source_id || pet.id} 
                    className={`history-item-row ${isCurrent ? 'current-item' : ''}`}
                    onClick={() => {
                      if (onSelectPetition) {
                        onSelectPetition(pet);
                      }
                      onClose();
                    }}
                    role="button"
                    tabIndex={0}
                  >
                    <div className="history-item-icon">
                      <FileText size={18} />
                    </div>

                    <div className="history-item-content">
                      <div className="history-item-header">
                        <span className="history-file-name">{pet.fileName}</span>
                        <span className="history-pet-id font-mono">#{pet.id}</span>
                        {isCurrent && <span className="active-tag">Active</span>}
                      </div>

                      <div className="history-item-summary">
                        {pet.summary}
                      </div>

                      <div className="history-item-meta">
                        <span>Petitioner: <strong>{pet.petitionerName}</strong></span>
                        <span>•</span>
                        <span>Dept: <strong>{pet.department}</strong></span>
                        <span>•</span>
                        <span className="history-time">
                          <Clock size={11} />
                          {pet.uploadedAt}
                        </span>
                      </div>
                    </div>

                    <div className="history-item-arrow">
                      <ArrowRight size={15} />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="modal-footer">
          <span className="history-footer-count">{petitions.length} documents recorded</span>
          <button type="button" className="secondary-modal-btn" onClick={onClose}>
            Close
          </button>
        </div>

      </div>
    </div>
  );
}
