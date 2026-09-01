import React, { useState, useRef } from 'react';
import { UploadCloud, FileText, CheckCircle2 } from 'lucide-react';
import { MOCK_PETITIONS } from '../../data/mockPetitions';
import './Upload.css';

export default function UploadLanding({ onSelectPetition }) {
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef(null);

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      const uploadedDoc = {
        ...MOCK_PETITIONS[0],
        fileName: file.name,
        fileSize: `${(file.size / (1024 * 1024)).toFixed(1)} MB`,
        fileType: file.type || 'PDF Document (Scanned)'
      };
      onSelectPetition(uploadedDoc);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      const uploadedDoc = {
        ...MOCK_PETITIONS[0],
        fileName: file.name,
        fileSize: `${(file.size / (1024 * 1024)).toFixed(1)} MB`,
        fileType: file.type || 'PDF Document (Scanned)'
      };
      onSelectPetition(uploadedDoc);
    } else {
      // Fallback default sample if cancelled
      onSelectPetition(MOCK_PETITIONS[0]);
    }
  };

  return (
    <div className="landing-wrapper">
      <div className="landing-container">
        
        {/* Government Emblem Header */}
        <div className="landing-header">
          <div className="landing-emblem" aria-hidden="true">
            <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="24" cy="24" r="23" stroke="#D9531E" strokeWidth="1.5" fill="#0A2540" />
              <path d="M24 9L29 19H19L24 9Z" fill="#EA580C" />
              <path d="M14 21H34V25C34 30.5228 29.5228 35 24 35C18.4772 35 14 30.5228 14 25V21Z" fill="#E4EFFB" />
              <path d="M18 25V31M24 25V32M30 25V31" stroke="#0A2540" strokeWidth="2" strokeLinecap="round" />
              <path d="M19 40H29" stroke="#D9531E" strokeWidth="2.5" strokeLinecap="round" />
            </svg>
          </div>
          <h2 className="landing-title">Petition Document Assistant</h2>
          <p className="landing-description">
            Upload a citizen petition to automatically summarize and extract the required grievance information.
          </p>
        </div>

        {/* Clean Upload Dropzone */}
        <div 
          className={`upload-dropzone ${isDragging ? 'dragging' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => {
            if (fileInputRef.current) {
              fileInputRef.current.click();
            }
          }}
          role="button"
          tabIndex={0}
          aria-label="Upload citizen petition"
        >
          <input 
            type="file" 
            ref={fileInputRef} 
            onChange={handleFileChange} 
            accept=".pdf,.jpg,.jpeg,.png" 
            style={{ display: 'none' }} 
          />

          <div className="dropzone-inner">
            <div className="upload-icon-wrapper">
              <UploadCloud size={32} className="upload-icon-svg" />
            </div>

            <div className="upload-heading">Upload Petition</div>
            <div className="upload-subtext">Drag and drop a scanned petition here</div>

            <div className="upload-or-divider">
              <span>or</span>
            </div>

            <button 
              type="button" 
              className="browse-btn"
              onClick={(e) => {
                e.stopPropagation();
                if (fileInputRef.current) {
                  fileInputRef.current.click();
                } else {
                  onSelectPetition(MOCK_PETITIONS[0]);
                }
              }}
            >
              Browse Document
            </button>

            <div className="supported-formats">
              <span className="format-tag">PDF</span>
              <span className="format-dot">•</span>
              <span className="format-tag">JPG</span>
              <span className="format-dot">•</span>
              <span className="format-tag">JPEG</span>
              <span className="format-dot">•</span>
              <span className="format-tag">PNG</span>
            </div>

            <div className="bilingual-badge">
              <span className="bilingual-dot"></span>
              Supports Tamil and English petition documents
            </div>
          </div>
        </div>

        {/* Supporting Note */}
        <div className="landing-footer-note">
          <CheckCircle2 size={13} className="note-icon" />
          <span>Assists grievance pre-processing before entry into the official grievance portal.</span>
        </div>

      </div>
    </div>
  );
}
