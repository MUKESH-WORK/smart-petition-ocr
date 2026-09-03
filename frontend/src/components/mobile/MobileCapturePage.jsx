import React, { useState, useRef, useEffect } from 'react';
import { 
  Camera, 
  Image as ImageIcon, 
  RefreshCw, 
  Upload, 
  CheckCircle2, 
  AlertCircle, 
  FileText, 
  ShieldCheck, 
  Smartphone,
  ChevronRight,
  Info,
  Edit3
} from 'lucide-react';
import { uploadPetitionImage } from '../../services/uploadSessionService';
import './MobileCapture.css';

function getSessionIdFromLocation(propId) {
  if (propId) return propId;
  if (typeof window === 'undefined') return '';

  const path = window.location.pathname;
  const hash = window.location.hash;
  const searchParams = new URLSearchParams(window.location.search);

  if (path.includes('/capture/')) {
    return path.split('/capture/')[1]?.split('/')[0]?.split('?')[0] || '';
  }
  if (hash.includes('/capture/')) {
    return hash.split('/capture/')[1]?.split('/')[0]?.split('?')[0] || '';
  }
  if (searchParams.get('session')) {
    return searchParams.get('session') || '';
  }
  return '';
}

export default function MobileCapturePage({ sessionId: propSessionId }) {
  const [sessionId] = useState(() => getSessionIdFromLocation(propSessionId));
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [customFileName, setCustomFileName] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [fileDetails, setFileDetails] = useState(null);

  const cameraInputRef = useRef(null);
  const galleryInputRef = useRef(null);

  // Clean up object URLs on unmount or file change
  useEffect(() => {
    return () => {
      if (previewUrl && previewUrl.startsWith('blob:')) {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/') && !file.name.match(/\.(jpg|jpeg|png|webp|heic)$/i)) {
      setErrorMessage('Please capture or select a valid image file (JPG, PNG, WEBP).');
      return;
    }

    setErrorMessage('');
    setSelectedFile(file);

    const url = URL.createObjectURL(file);
    setPreviewUrl(url);

    const sizeFormatted = file.size > 1024 * 1024 
      ? `${(file.size / (1024 * 1024)).toFixed(1)} MB` 
      : `${Math.max(1, Math.round(file.size / 1024))} KB`;

    // Default clean filename e.g. petition_01.jpg
    const initialName = file.name && !file.name.match(/^\d{10,}/) 
      ? file.name 
      : `petition_${new Date().toISOString().slice(0, 10)}.jpg`;

    setCustomFileName(initialName);
    setFileDetails({
      name: initialName,
      size: sizeFormatted,
      type: file.type || 'image/jpeg',
      lastModified: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    });
  };

  const handleRetake = () => {
    if (previewUrl && previewUrl.startsWith('blob:')) {
      URL.revokeObjectURL(previewUrl);
    }
    setSelectedFile(null);
    setPreviewUrl(null);
    setFileDetails(null);
    setCustomFileName('');
    setErrorMessage('');
    if (cameraInputRef.current) cameraInputRef.current.value = '';
    if (galleryInputRef.current) galleryInputRef.current.value = '';
  };

  const handleUpload = async () => {
    if (!selectedFile || !sessionId) {
      setErrorMessage('Missing image or session ID.');
      return;
    }

    setIsUploading(true);
    setErrorMessage('');

    // Ensure filename ends with proper image extension
    let finalFileName = customFileName.trim() || 'petition.jpg';
    if (!finalFileName.match(/\.(jpg|jpeg|png|webp)$/i)) {
      finalFileName += '.jpg';
    }

    try {
      await uploadPetitionImage(sessionId, selectedFile, finalFileName);
      setFileDetails(prev => ({ ...prev, name: finalFileName }));
      setIsUploading(false);
      setUploadSuccess(true);
    } catch (err) {
      console.error('Upload failed:', err);
      setIsUploading(false);
      setErrorMessage('Failed to upload petition. Please try again.');
    }
  };

  return (
    <div className="mobile-capture-root">
      
      {/* Mobile Top Header */}
      <header className="mobile-top-bar">
        <div className="mobile-brand-group">
          <img 
            src="/tn-emblem.png" 
            alt="Government Emblem" 
            className="mobile-emblem-icon"
            onError={(e) => { e.target.style.display = 'none'; }}
          />
          <div className="mobile-brand-text">
            <h1 className="mobile-app-title">Tamil Nadu e-Grievance</h1>
            <span className="mobile-app-subtitle">Petition Capture System</span>
          </div>
        </div>

        {sessionId && (
          <div className="mobile-session-pill" title={`Session ID: ${sessionId}`}>
            <span className="session-dot"></span>
            <span className="session-code">#{sessionId.substring(0, 8)}</span>
          </div>
        )}
      </header>

      {/* Main Screen Container */}
      <main className="mobile-capture-main">
        
        {/* =========================================================
            STATE 3: UPLOAD SUCCESS CONFIRMATION
           ========================================================= */}
        {uploadSuccess ? (
          <div className="mobile-card mobile-success-card animate-fade-in">
            <div className="success-icon-bubble">
              <CheckCircle2 size={54} className="success-check-icon" />
            </div>

            <h2 className="success-title">Petition Uploaded!</h2>
            <p className="success-desc">
              Your petition document has been securely transferred to the officer's desktop workstation.
            </p>

            <div className="success-meta-box">
              <div className="meta-row">
                <span className="meta-label">Session:</span>
                <span className="meta-value font-mono">#{sessionId}</span>
              </div>
              <div className="meta-row">
                <span className="meta-label">File Name:</span>
                <span className="meta-value font-mono file-name-value">{fileDetails?.name || 'petition.jpg'}</span>
              </div>
              <div className="meta-row">
                <span className="meta-label">Status:</span>
                <span className="meta-value status-badge-success">Transferred to Desktop</span>
              </div>
            </div>

            <div className="success-action-area">
              <div className="instruction-tip">
                <ShieldCheck size={18} className="tip-icon" />
                <span>You can safely close this browser tab now.</span>
              </div>
            </div>
          </div>
        ) : previewUrl ? (
          /* =========================================================
              STATE 2: PHOTO PREVIEW & EDITABLE FILENAME
             ========================================================= */
          <div className="mobile-card mobile-preview-card animate-fade-in">
            <div className="preview-card-header">
              <h2 className="preview-title">Petition Preview</h2>
              <span className="preview-subtitle">Verify that the document is sharp and legible</span>
            </div>

            {/* Photo Container */}
            <div className="preview-photo-frame">
              <img 
                src={previewUrl} 
                alt="Captured Petition Preview" 
                className="preview-image-element"
              />
              <div className="preview-overlay-tag">
                <FileText size={13} />
                <span>{fileDetails?.size || 'Ready'}</span>
              </div>
            </div>

            {/* Editable File Name Input */}
            <div className="editable-filename-container">
              <label htmlFor="custom-file-name" className="filename-input-label">
                <Edit3 size={13} className="label-icon" />
                <span>Document Name</span>
              </label>
              <div className="filename-input-wrapper">
                <input 
                  id="custom-file-name"
                  type="text" 
                  value={customFileName}
                  onChange={(e) => setCustomFileName(e.target.value)}
                  placeholder="e.g. road_repair_petition.jpg"
                  className="filename-custom-input"
                  disabled={isUploading}
                />
              </div>
            </div>

            {errorMessage && (
              <div className="mobile-error-banner">
                <AlertCircle size={16} />
                <span>{errorMessage}</span>
              </div>
            )}

            {/* Actions: Retake or Upload */}
            <div className="preview-action-grid">
              <button 
                type="button" 
                className="mobile-btn-retake"
                onClick={handleRetake}
                disabled={isUploading}
              >
                <RefreshCw size={17} />
                <span>Retake</span>
              </button>

              <button 
                type="button" 
                className="mobile-btn-upload"
                onClick={handleUpload}
                disabled={isUploading}
              >
                {isUploading ? (
                  <>
                    <RefreshCw size={17} className="spin" />
                    <span>Uploading...</span>
                  </>
                ) : (
                  <>
                    <Upload size={17} />
                    <span>Upload Petition</span>
                  </>
                )}
              </button>
            </div>

            <div className="preview-footer-note">
              <Info size={14} className="note-icon" />
              <span>Ensure petitioner details, signatures, and grievance text are clearly visible.</span>
            </div>
          </div>
        ) : (
          /* =========================================================
              STATE 1: INITIAL CAPTURE / SELECTION SCREEN
             ========================================================= */
          <div className="mobile-card mobile-capture-card animate-fade-in">
            
            {/* Guidance Viewfinder Graphic */}
            <div className="viewfinder-guide-box">
              <div className="viewfinder-corner top-left"></div>
              <div className="viewfinder-corner top-right"></div>
              <div className="viewfinder-corner bottom-left"></div>
              <div className="viewfinder-corner bottom-right"></div>
              
              <div className="viewfinder-inner-content">
                <div className="viewfinder-icon-pulse">
                  <Camera size={38} className="viewfinder-cam-icon" />
                </div>
                <div className="viewfinder-prompt-title">Place Petition in Frame</div>
                <p className="viewfinder-prompt-sub">
                  Align the document borders within the frame. Avoid glare and shadows.
                </p>
              </div>
            </div>

            {/* Error Message */}
            {errorMessage && (
              <div className="mobile-error-banner">
                <AlertCircle size={16} />
                <span>{errorMessage}</span>
              </div>
            )}

            {/* Primary & Secondary Capture Buttons */}
            <div className="capture-buttons-stack">
              
              {/* Primary: Take Photo with Rear Camera */}
              <button 
                type="button" 
                className="mobile-btn-primary"
                onClick={() => cameraInputRef.current?.click()}
              >
                <Camera size={20} className="btn-icon" />
                <span className="btn-text">Capture Photo</span>
                <ChevronRight size={18} className="btn-chevron" />
              </button>

              {/* Secondary: Choose from Photo Gallery */}
              <button 
                type="button" 
                className="mobile-btn-secondary"
                onClick={() => galleryInputRef.current?.click()}
              >
                <ImageIcon size={18} className="btn-icon" />
                <span className="btn-text">Choose from Gallery</span>
              </button>

            </div>

            {/* Hidden HTML5 Native File Inputs */}
            <input 
              type="file" 
              ref={cameraInputRef}
              onChange={handleFileChange}
              accept="image/*"
              capture="environment"
              style={{ display: 'none' }}
              aria-label="Capture petition with camera"
            />

            <input 
              type="file" 
              ref={galleryInputRef}
              onChange={handleFileChange}
              accept="image/*"
              style={{ display: 'none' }}
              aria-label="Choose petition photo from gallery"
            />

            {/* Quality Tips */}
            <div className="mobile-tips-card">
              <div className="tips-header">
                <ShieldCheck size={15} className="tips-shield" />
                <span>Tips for Best Accuracy</span>
              </div>
              <ul className="tips-list">
                <li>Flatten any folded petition pages before taking photo.</li>
                <li>Hold your phone directly above the paper.</li>
                <li>Ensure good daylight or ambient room lighting.</li>
              </ul>
            </div>

          </div>
        )}

      </main>

      {/* Mobile Footer */}
      <footer className="mobile-footer">
        <div className="footer-secure-row">
          <Smartphone size={13} />
          <span>Government Grievance Cell • Direct Mobile Link</span>
        </div>
      </footer>

    </div>
  );
}
