import React, { useState, useRef, useEffect } from 'react';
import { UploadCloud, Smartphone, X, CheckCircle2, Loader2, RefreshCw } from 'lucide-react';
import { MOCK_PETITIONS } from '../../data/mockPetitions';
import './Upload.css';

export default function UploadLanding({ onSelectPetition }) {
  const [isDragging, setIsDragging] = useState(false);
  const [isQrModalOpen, setIsQrModalOpen] = useState(false);
  const [secondsRemaining, setSecondsRemaining] = useState(299); // 04:59
  const [isReceived, setIsReceived] = useState(false);
  const [receivedFileName, setReceivedFileName] = useState('');

  const desktopFileInputRef = useRef(null);
  const qrFileInputRef = useRef(null);

  // Countdown timer for QR Modal session
  useEffect(() => {
    if (!isQrModalOpen) {
      setSecondsRemaining(299);
      setIsReceived(false);
      setReceivedFileName('');
      return;
    }

    const timer = setInterval(() => {
      setSecondsRemaining((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);

    return () => clearInterval(timer);
  }, [isQrModalOpen]);

  // Handle Escape key to close modal
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isQrModalOpen) {
        setIsQrModalOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isQrModalOpen]);

  const formatTime = (totalSeconds) => {
    const m = Math.floor(totalSeconds / 60).toString().padStart(2, '0');
    const s = (totalSeconds % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

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
      : `${Math.max(1, (file.size / 1024)).toFixed(0)} KB`;

    // Single source of truth for the uploaded document
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
      details: MOCK_PETITIONS[0].details,
      rawOcrText: MOCK_PETITIONS[0].rawOcrText,
      qaDatabase: MOCK_PETITIONS[0].qaDatabase
    };

    if (isQrModalOpen) {
      setReceivedFileName(file.name);
      setIsReceived(true);
      setTimeout(() => {
        setIsQrModalOpen(false);
        onSelectPetition(uploadedDoc);
      }, 700);
    } else {
      onSelectPetition(uploadedDoc);
    }
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

  const handleQrFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileProcess(e.target.files[0]);
    }
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

        {/* CLEAN UPLOAD CARD (Remains visible and unmodified in background) */}
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
              <Smartphone size={16} className="scan-phone-icon" />
              <span>Scan using mobile</span>
            </button>

          </div>
        </div>

      </div>

      {/* =========================================================
          CENTERED QR CODE MODAL POPUP OVER THE PAGE
         ========================================================= */}
      {isQrModalOpen && (
        <div 
          className="qr-modal-backdrop" 
          onClick={() => setIsQrModalOpen(false)}
          role="dialog" 
          aria-modal="true"
        >
          <div 
            className="qr-centered-modal-card" 
            onClick={(e) => e.stopPropagation()}
          >
            
            {/* Modal Header */}
            <div className="qr-modal-header">
              <div className="qr-title-row">
                <Smartphone size={17} className="qr-title-icon" />
                <h3 className="qr-modal-title">Scan using mobile</h3>
              </div>
              <button 
                type="button" 
                className="qr-modal-close-btn" 
                onClick={() => setIsQrModalOpen(false)}
                aria-label="Close modal"
              >
                <X size={17} />
              </button>
            </div>

            {/* Modal Body */}
            <div className="qr-modal-body">
              
              {/* Normal / Waiting State */}
              {!isReceived && secondsRemaining > 0 && (
                <>
                  {/* Clean Centered QR Code Box (176px x 176px) */}
                  <div 
                    className="qr-modal-code-box"
                    onClick={() => qrFileInputRef.current?.click()}
                    title="Click or scan with phone to upload document"
                  >
                    <svg 
                      className="qr-modal-svg" 
                      viewBox="0 0 160 160" 
                      fill="none" 
                      xmlns="http://www.w3.org/2000/svg"
                    >
                      {/* Clean White Background */}
                      <rect width="160" height="160" rx="8" fill="#FFFFFF" />

                      {/* Top-Left Position Detection Marker */}
                      <rect x="14" y="14" width="36" height="36" rx="4" fill="#0A2540" />
                      <rect x="20" y="20" width="24" height="24" rx="2" fill="#FFFFFF" />
                      <rect x="25" y="25" width="14" height="14" rx="2" fill="#EA580C" />

                      {/* Top-Right Position Detection Marker */}
                      <rect x="110" y="14" width="36" height="36" rx="4" fill="#0A2540" />
                      <rect x="116" y="20" width="24" height="24" rx="2" fill="#FFFFFF" />
                      <rect x="121" y="25" width="14" height="14" rx="2" fill="#EA580C" />

                      {/* Bottom-Left Position Detection Marker */}
                      <rect x="14" y="110" width="36" height="36" rx="4" fill="#0A2540" />
                      <rect x="20" y="116" width="24" height="24" rx="2" fill="#FFFFFF" />
                      <rect x="25" y="121" width="14" height="14" rx="2" fill="#EA580C" />

                      {/* QR Data Matrix Patterns */}
                      <g fill="#0A2540">
                        <rect x="58" y="16" width="6" height="6" rx="1" />
                        <rect x="70" y="16" width="6" height="6" rx="1" />
                        <rect x="88" y="16" width="6" height="6" rx="1" />

                        <rect x="58" y="28" width="6" height="12" rx="1" />
                        <rect x="70" y="28" width="12" height="6" rx="1" />
                        <rect x="88" y="28" width="6" height="6" rx="1" />
                        <rect x="98" y="28" width="6" height="12" rx="1" />

                        <rect x="16" y="58" width="6" height="12" rx="1" />
                        <rect x="28" y="58" width="12" height="6" rx="1" />
                        <rect x="46" y="58" width="6" height="6" rx="1" />
                        <rect x="58" y="58" width="12" height="12" rx="1" />
                        <rect x="76" y="58" width="6" height="6" rx="1" />
                        <rect x="88" y="58" width="12" height="6" rx="1" />
                        <rect x="110" y="58" width="6" height="12" rx="1" />
                        <rect x="128" y="58" width="16" height="6" rx="1" />

                        <rect x="16" y="76" width="12" height="6" rx="1" />
                        <rect x="34" y="76" width="6" height="12" rx="1" />
                        <rect x="46" y="82" width="12" height="6" rx="1" />
                        <rect x="64" y="76" width="6" height="12" rx="1" />
                        <rect x="76" y="82" width="12" height="6" rx="1" />
                        <rect x="94" y="76" width="12" height="6" rx="1" />
                        <rect x="116" y="76" width="6" height="12" rx="1" />
                        <rect x="134" y="76" width="12" height="12" rx="1" />

                        <rect x="16" y="94" width="6" height="6" rx="1" />
                        <rect x="28" y="94" width="6" height="6" rx="1" />
                        <rect x="40" y="94" width="12" height="6" rx="1" />
                        <rect x="58" y="94" width="6" height="6" rx="1" />
                        <rect x="70" y="94" width="12" height="6" rx="1" />
                        <rect x="88" y="94" width="6" height="6" rx="1" />
                        <rect x="100" y="94" width="12" height="6" rx="1" />
                        <rect x="118" y="94" width="6" height="6" rx="1" />
                        <rect x="130" y="94" width="14" height="6" rx="1" />

                        <rect x="58" y="112" width="12" height="6" rx="1" />
                        <rect x="76" y="112" width="6" height="12" rx="1" />
                        <rect x="88" y="112" width="12" height="6" rx="1" />
                        <rect x="110" y="112" width="6" height="6" rx="1" />
                        <rect x="122" y="112" width="12" height="12" rx="1" />
                        <rect x="140" y="112" width="6" height="6" rx="1" />

                        <rect x="58" y="128" width="6" height="14" rx="1" />
                        <rect x="70" y="134" width="12" height="8" rx="1" />
                        <rect x="88" y="128" width="6" height="14" rx="1" />
                        <rect x="100" y="134" width="12" height="8" rx="1" />
                        <rect x="120" y="134" width="6" height="8" rx="1" />
                        <rect x="134" y="128" width="12" height="14" rx="1" />
                      </g>

                      {/* Central Administrative Emblem Badge */}
                      <circle cx="80" cy="80" r="13" fill="#0A2540" />
                      <circle cx="80" cy="80" r="11" fill="#FFFFFF" />
                      <path d="M76 74H84V86H76V74Z" fill="#EA580C" />
                      <path d="M78 77H82M78 80H82M78 83H81" stroke="#FFFFFF" strokeWidth="1" strokeLinecap="round" />
                    </svg>
                  </div>

                  <p className="qr-modal-instruction">
                    Scan this QR code with your phone to upload the petition.
                  </p>

                  {/* Waiting Status Pill */}
                  <div className="qr-modal-waiting-pill">
                    <span className="qr-pulsing-dot"></span>
                    <span>Waiting for document...</span>
                  </div>

                  {/* Expiry Note */}
                  <div className="qr-modal-expiry-note">
                    Session expires in <strong className="font-mono">{formatTime(secondsRemaining)}</strong>
                  </div>

                  {/* Hidden Input for Phone Simulation / Local Testing */}
                  <input 
                    type="file" 
                    ref={qrFileInputRef} 
                    onChange={handleQrFileChange} 
                    accept=".pdf,image/*" 
                    style={{ display: 'none' }} 
                  />
                </>
              )}

              {/* Expired State */}
              {!isReceived && secondsRemaining === 0 && (
                <div className="qr-modal-expired-view">
                  <div className="qr-modal-expired-badge">Session expired</div>
                  <p className="qr-modal-expired-sub">
                    The temporary mobile upload session has timed out.
                  </p>
                  <button 
                    type="button" 
                    className="qr-modal-regenerate-btn"
                    onClick={() => setSecondsRemaining(299)}
                  >
                    <RefreshCw size={13} />
                    <span>Generate New QR</span>
                  </button>
                </div>
              )}

              {/* Success / Document Received State */}
              {isReceived && (
                <div className="qr-modal-received-view">
                  <div className="qr-received-icon-wrap">
                    <CheckCircle2 size={46} className="text-green received-success-icon" />
                  </div>
                  <div className="received-title">✓ Document received</div>
                  <div className="received-subtext">Preparing petition...</div>
                  <div className="received-loading-row">
                    <Loader2 size={15} className="spin text-orange" />
                    <span className="font-mono text-muted">{receivedFileName}</span>
                  </div>
                </div>
              )}

            </div>

            {/* Modal Footer */}
            <div className="qr-modal-footer">
              <button 
                type="button" 
                className="qr-modal-cancel-btn" 
                onClick={() => setIsQrModalOpen(false)}
              >
                Cancel
              </button>
            </div>

          </div>
        </div>
      )}

    </div>
  );
}
