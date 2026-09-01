import React from 'react';
import { History, FileText, X, ArrowRight, CheckCircle2, Clock } from 'lucide-react';
import { MOCK_PETITIONS } from '../../data/mockPetitions';
import './HistoryModal.css';

export default function HistoryModal({ 
  isOpen, 
  onClose, 
  currentPetitionId, 
  onSelectPetition 
}) {
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
              <h3 className="modal-title">Petition History</h3>
              <p className="modal-subtitle">Recent documents processed in this session</p>
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
          <div className="history-list">
            {MOCK_PETITIONS.map((pet) => {
              const isCurrent = pet.id === currentPetitionId;

              return (
                <div 
                  key={pet.id} 
                  className={`history-item-row ${isCurrent ? 'current-item' : ''}`}
                  onClick={() => {
                    onSelectPetition(pet);
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
                      <span>Language: <strong>{pet.language}</strong></span>
                      <span>•</span>
                      <span>Pages: <strong>{pet.totalPages}</strong></span>
                      <span>•</span>
                      <span>OCR: <strong>{pet.confidenceScore}%</strong></span>
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
        </div>

        {/* Modal Footer */}
        <div className="modal-footer">
          <span className="history-footer-count">{MOCK_PETITIONS.length} petitions available in current session</span>
          <button type="button" className="secondary-modal-btn" onClick={onClose}>
            Close
          </button>
        </div>

      </div>
    </div>
  );
}
