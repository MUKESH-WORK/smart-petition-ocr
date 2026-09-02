import React, { useState, useRef } from 'react';
import { UploadCloud, Smartphone } from 'lucide-react';
import MobileQrModal from './MobileQrModal';
import { MOCK_PETITIONS } from '../../data/mockPetitions';
import './Upload.css';

export default function UploadLanding({ onSelectPetition }) {
  const [isDragging, setIsDragging] = useState(false);
  const [isQrModalOpen, setIsQrModalOpen] = useState(false);

  const desktopFileInputRef = useRef(null);

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

  const handleFileProcess = (file) => {
    if (!file) return;

    const isPdf = file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf');
    const previewUrl = URL.createObjectURL(file);
    const sizeFormatted = file.size > 1024 * 1024 
      ? `${(file.size / (1024 * 1024)).toFixed(1)} MB` 
      : `${Math.max(1, Math.round(file.size / 1024))} KB`;

    const uploadedDoc = {
      file: file,
      id: `TEMP-${Math.floor(100 + Math.random() * 900)}`,
      fileName: file.name,
      fileSize: sizeFormatted,
      fileType: file.type || (isPdf ? 'PDF Document' : 'Scanned Image'),
      isPdf: isPdf,
      previewUrl: previewUrl,
      uploadedAt: `Today at ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`,
      totalPages: 1,
      language: 'Tamil',
      confidenceScore: 96,
      status: 'Analysis Complete',
      summary: 'The petitioner requests repair of a damaged road in ABC Village, Erode District. The petition states that the road has remained damaged for several months and causes transportation difficulties during rainfall.',
      portalDetails: MOCK_PETITIONS[0].portalDetails,
      rawOcrText: MOCK_PETITIONS[0].rawOcrText,
      qaDatabase: MOCK_PETITIONS[0].qaDatabase
    };

    onSelectPetition(uploadedDoc);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileProcess(e.dataTransfer.files[0]);
    }
  };

  const handleDesktopFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileProcess(e.target.files[0]);
    }
  };

  const handleMobileDocumentUploaded = (uploadedDoc) => {
    onSelectPetition(uploadedDoc);
  };

  return (
    <div className="landing-wrapper">
      <div className="landing-container">
        
        {/* Government Emblem Header */}
        <div className="landing-header">
          <div className="landing-emblem" aria-hidden="true">
            <img 
              src="/tn-emblem.png" 
              alt="Government of Tamil Nadu Official Emblem" 
              className="landing-emblem-img" 
            />
          </div>
          <h2 className="landing-title">Petition Document Assistant</h2>
          <p className="landing-description">
            Upload or scan a petition to begin.
          </p>
        </div>

        {/* Clean Upload Dropzone Card */}
        <div 
          className={`upload-dropzone ${isDragging ? 'dragging' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => {
            if (desktopFileInputRef.current) {
              desktopFileInputRef.current.click();
            }
          }}
          role="region"
          aria-label="Upload citizen petition"
        >
          <input 
            type="file" 
            ref={desktopFileInputRef} 
            onChange={handleDesktopFileChange} 
            accept=".pdf,.jpg,.jpeg,.png,.webp" 
            style={{ display: 'none' }} 
          />

          <div className="dropzone-inner">
            
            {/* Upload Icon */}
            <div className="upload-icon-wrapper">
              <UploadCloud size={30} className="upload-icon-svg" />
            </div>

            {/* Headings */}
            <div className="upload-heading">Upload Petition</div>
            <div className="upload-subtext">Drag & drop your document here</div>

            {/* Primary Action Button */}
            <button 
              type="button" 
              className="browse-btn"
              onClick={(e) => {
                e.stopPropagation();
                if (desktopFileInputRef.current) {
                  desktopFileInputRef.current.click();
                }
              }}
            >
              Browse Document
            </button>

            {/* Small Muted Format List */}
            <div className="supported-formats-line">
              <span>PDF • JPG • PNG • WEBP</span>
            </div>

            {/* OR Divider */}
            <div className="upload-or-divider">
              <span>or</span>
            </div>

            {/* Secondary Action: Scan using mobile */}
            <button
              type="button"
              className="scan-mobile-action-btn"
              onClick={(e) => {
                e.stopPropagation();
                setIsQrModalOpen(true);
              }}
              title="Scan and upload petition from your smartphone"
            >
              <Smartphone size={17} className="scan-phone-icon" />
              <span className="scan-phone-text">Scan using mobile</span>
            </button>

          </div>
        </div>

      </div>

      {/* Dynamic QR Code Modal (Phone capture only) */}
      <MobileQrModal
        isOpen={isQrModalOpen}
        onClose={() => setIsQrModalOpen(false)}
        onDocumentUploaded={handleMobileDocumentUploaded}
      />

    </div>
  );
}
