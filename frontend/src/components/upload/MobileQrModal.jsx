import React, { useState, useEffect, useRef, useCallback } from 'react';
import QRCode from 'qrcode';
import { 
  Smartphone, 
  X, 
  CheckCircle2, 
  Loader2, 
  RefreshCw 
} from 'lucide-react';
import { 
  createUploadSession, 
  subscribeToUpload, 
  cleanupUploadSession 
} from '../../services/uploadSessionService';
import { MOCK_PETITIONS } from '../../data/mockPetitions';

export default function MobileQrModal({ isOpen, onClose, onDocumentUploaded }) {
  const [sessionId, setSessionId] = useState('');
  const [qrDataUrl, setQrDataUrl] = useState('');
  const [secondsRemaining, setSecondsRemaining] = useState(299); // 04:59
  const [isReceived, setIsReceived] = useState(false);
  const [receivedFileMeta, setReceivedFileMeta] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);

  const unsubscribeRef = useRef(null);
  const sessionIdRef = useRef('');

  const handleUploadSuccess = useCallback(async (uploadedData) => {
    setIsReceived(true);
    setReceivedFileMeta(uploadedData);

    const previewUrl = uploadedData.dataUrl || (uploadedData.file ? URL.createObjectURL(uploadedData.file) : null);
    
    let fileObj = uploadedData.file || null;
    if (!fileObj && uploadedData.dataUrl) {
      try {
        const res = await fetch(uploadedData.dataUrl);
        const blob = await res.blob();
        fileObj = new File([blob], uploadedData.fileName || `mobile_petition_${Date.now()}.jpg`, {
          type: blob.type || uploadedData.fileType || 'image/jpeg'
        });
      } catch (err) {
        console.warn('Could not convert dataUrl to File:', err);
      }
    }

    const uploadedDoc = {
      file: fileObj,
      id: `PET-${uploadedData.sessionId ? uploadedData.sessionId.substring(0, 6).toUpperCase() : Math.floor(100 + Math.random() * 900)}`,
      fileName: uploadedData.fileName || 'mobile_petition.jpg',
      fileSize: uploadedData.fileSize || '1.8 MB',
      fileType: uploadedData.fileType || 'Scanned Image (Mobile)',
      isPdf: false,
      previewUrl: previewUrl,
      uploadedAt: `Today at ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`,
      totalPages: 1,
      language: 'Tamil',
      confidenceScore: 95,
      status: 'Processing',
      summary: '',
      portalDetails: null,
      rawOcrText: '',
      qaDatabase: []
    };

    setTimeout(() => {
      onDocumentUploaded(uploadedDoc);
      onClose();
    }, 900);
  }, [onDocumentUploaded, onClose]);

  const initSession = useCallback(async () => {
    setIsGenerating(true);
    setIsReceived(false);
    setReceivedFileMeta(null);
    setSecondsRemaining(299);

    if (unsubscribeRef.current) {
      unsubscribeRef.current();
      unsubscribeRef.current = null;
    }

    try {
      const sessionResult = await createUploadSession();
      const newSessionId = typeof sessionResult === 'object' ? sessionResult.sessionId : sessionResult;
      const networkHost = typeof sessionResult === 'object' ? sessionResult.networkHost : null;

      setSessionId(newSessionId);
      sessionIdRef.current = newSessionId;

      // Prioritize LAN Wi-Fi network host so phone cameras connect immediately
      let targetOrigin = window.location.origin;
      if ((window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') && networkHost) {
        targetOrigin = networkHost;
      }

      const targetUrl = `${targetOrigin}/capture/${newSessionId}`;

      const dataUrl = await QRCode.toDataURL(targetUrl, {
        width: 320,
        margin: 2,
        color: {
          dark: '#000000',
          light: '#FFFFFF'
        },
        errorCorrectionLevel: 'M'
      });
      setQrDataUrl(dataUrl);

      unsubscribeRef.current = subscribeToUpload(newSessionId, (uploadedData) => {
        handleUploadSuccess(uploadedData);
      });
    } catch (err) {
      console.error('Failed to initialize QR session:', err);
    } finally {
      setIsGenerating(false);
    }
  }, [handleUploadSuccess]);

  // Initialize new session when modal opens
  useEffect(() => {
    if (!isOpen) {
      if (unsubscribeRef.current) {
        unsubscribeRef.current();
        unsubscribeRef.current = null;
      }
      if (sessionIdRef.current) {
        cleanupUploadSession(sessionIdRef.current);
        sessionIdRef.current = '';
      }
      return;
    }

    initSession();

    return () => {
      if (unsubscribeRef.current) {
        unsubscribeRef.current();
        unsubscribeRef.current = null;
      }
    };
  }, [isOpen, initSession]);

  // Countdown timer for 5 minutes
  useEffect(() => {
    if (!isOpen || isReceived || secondsRemaining <= 0) return;

    const timer = setInterval(() => {
      setSecondsRemaining((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [isOpen, isReceived, secondsRemaining]);

  // Handle escape key to close
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  const formatTime = (totalSeconds) => {
    const m = Math.floor(totalSeconds / 60).toString().padStart(2, '0');
    const s = (totalSeconds % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  if (!isOpen) return null;

  return (
    <div 
      className="qr-modal-backdrop" 
      onClick={onClose}
      role="dialog" 
      aria-modal="true"
      aria-labelledby="qr-modal-title"
    >
      <div 
        className="qr-centered-modal-card" 
        onClick={(e) => e.stopPropagation()}
      >
        
        {/* Modal Header */}
        <div className="qr-modal-header">
          <div className="qr-title-row">
            <Smartphone size={18} className="qr-title-icon" />
            <h3 id="qr-modal-title" className="qr-modal-title">Scan using mobile</h3>
          </div>
          <button 
            type="button" 
            className="qr-modal-close-btn" 
            onClick={onClose}
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
              {/* Centered QR Code Box */}
              <div 
                className="qr-modal-code-box"
                title="Scan with phone camera to capture petition"
              >
                {isGenerating ? (
                  <div className="qr-loading-spinner">
                    <Loader2 size={32} className="spin text-orange" />
                  </div>
                ) : qrDataUrl ? (
                  <img 
                    src={qrDataUrl} 
                    alt={`QR Code for capture session ${sessionId}`} 
                    className="qr-modal-svg"
                  />
                ) : (
                  <div className="qr-loading-spinner">
                    <Loader2 size={32} className="spin text-orange" />
                  </div>
                )}
              </div>

              <p className="qr-modal-instruction">
                Scan this QR code with your phone to upload the petition.
              </p>

              {/* Waiting Status Pill with Pulsing Dot */}
              <div className="qr-modal-waiting-pill">
                <span className="qr-pulsing-dot"></span>
                <span>Waiting for document...</span>
              </div>

              {/* Expiry Note */}
              <div className="qr-modal-expiry-note">
                Session expires in <strong className="font-mono">{formatTime(secondsRemaining)}</strong>
              </div>
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
                onClick={initSession}
              >
                <RefreshCw size={14} />
                <span>Generate New QR</span>
              </button>
            </div>
          )}

          {/* Success / Document Received State */}
          {isReceived && (
            <div className="qr-modal-received-view">
              <div className="qr-received-icon-wrap">
                <CheckCircle2 size={48} className="received-success-icon" />
              </div>
              <div className="received-title">✓ Petition uploaded successfully</div>
              <div className="received-subtext">Loading document into workspace...</div>
              <div className="received-loading-row">
                <Loader2 size={15} className="spin text-orange" />
                <span className="font-mono text-muted">{receivedFileMeta?.fileName || 'petition.jpg'}</span>
              </div>
            </div>
          )}

        </div>

        {/* Modal Footer */}
        <div className="qr-modal-footer">
          <button 
            type="button" 
            className="qr-modal-cancel-btn" 
            onClick={onClose}
          >
            Cancel
          </button>
        </div>

      </div>
    </div>
  );
}
