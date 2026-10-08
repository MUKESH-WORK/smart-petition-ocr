import React, { useState, useEffect, useRef, useCallback } from 'react';
import QRCode from 'qrcode';
import { 
  Smartphone, 
  X, 
  CheckCircle2, 
  Loader2, 
  RefreshCw,
  Wifi,
  Copy,
  Check
} from 'lucide-react';
import { 
  createUploadSession, 
  subscribeToUpload, 
  cleanupUploadSession 
} from '../../services/uploadSessionService';

export default function MobileQrModal({ isOpen, onClose, onDocumentUploaded }) {
  const [sessionId, setSessionId] = useState('');
  const [qrDataUrl, setQrDataUrl] = useState('');
  const [captureUrl, setCaptureUrl] = useState('');
  const [secondsRemaining, setSecondsRemaining] = useState(299); // 04:59
  const [isReceived, setIsReceived] = useState(false);
  const [receivedFileMeta, setReceivedFileMeta] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [copied, setCopied] = useState(false);
  const [availableHosts, setAvailableHosts] = useState([]);
  const [selectedHostUrl, setSelectedHostUrl] = useState('');

  const unsubscribeRef = useRef(null);
  const sessionIdRef = useRef('');

  const handleUploadSuccess = useCallback(async (uploadedData) => {
    setIsReceived(true);
    setReceivedFileMeta(uploadedData);

    const isPdf = Boolean(
      uploadedData.isPdf ||
      (uploadedData.fileType && uploadedData.fileType.toLowerCase().includes('pdf')) ||
      (uploadedData.fileName && uploadedData.fileName.toLowerCase().endsWith('.pdf'))
    );

    const sourceId = uploadedData.source_id || uploadedData.sourceId;
    const documentFileUrl = sourceId ? `/api/v1/grievance/${sourceId}/file` : null;
    let previewUrl = uploadedData.dataUrl || (uploadedData.file ? URL.createObjectURL(uploadedData.file) : documentFileUrl);
    
    let fileObj = uploadedData.file || null;
    if (!fileObj && uploadedData.dataUrl) {
      try {
        const res = await fetch(uploadedData.dataUrl);
        const blob = await res.blob();
        const fallbackExt = isPdf ? '.pdf' : '.jpg';
        const fallbackMime = isPdf ? 'application/pdf' : 'image/jpeg';
        fileObj = new File([blob], uploadedData.fileName || `mobile_petition_${Date.now()}${fallbackExt}`, {
          type: blob.type || uploadedData.fileType || fallbackMime
        });
      } catch (err) {
        console.warn('Could not convert dataUrl to File:', err);
      }
    }

    const uploadedDoc = {
      file: fileObj,
      source_id: sourceId,
      sourceId: sourceId,
      id: sourceId ? `PET-${sourceId.slice(0, 8).toUpperCase()}` : `PET-${uploadedData.sessionId ? uploadedData.sessionId.substring(0, 6).toUpperCase() : Math.floor(100 + Math.random() * 900)}`,
      fileName: uploadedData.fileName || (isPdf ? 'mobile_petition.pdf' : 'mobile_petition.jpg'),
      fileSize: uploadedData.fileSize || (isPdf ? '2.4 MB' : '1.8 MB'),
      fileType: uploadedData.fileType || (isPdf ? 'PDF Document (Mobile)' : 'Scanned Image (Mobile)'),
      isPdf: isPdf,
      previewUrl: previewUrl,
      documentFileUrl: documentFileUrl,
      uploadedAt: `Today at ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`,
      totalPages: uploadedData.page_count || 1,
      language: 'Tamil',
      confidenceScore: 95,
      status: uploadedData.status || 'uploaded',
      duplicate_detected: Boolean(uploadedData.duplicate_detected),
      duplicate_source_id: uploadedData.duplicate_source_id || null,
      duplicate_petitioner_name: uploadedData.duplicate_petitioner_name || null,
      duplicate_file_name: uploadedData.duplicate_file_name || null,
      duplicate_summary: uploadedData.duplicate_summary || null,
      duplicate_created_at: uploadedData.duplicate_created_at || uploadedData.created_at || null,
      isMobileUpload: true,
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

  const generateQrForUrl = async (targetUrl) => {
    try {
      const dataUrl = await QRCode.toDataURL(targetUrl, {
        width: 320,
        margin: 2,
        color: {
          dark: '#102C57',
          light: '#FFFFFF'
        },
        errorCorrectionLevel: 'M'
      });
      setQrDataUrl(dataUrl);
      setCaptureUrl(targetUrl);
    } catch (err) {
      console.error('Failed to generate QR code:', err);
    }
  };

  const initSession = useCallback(async () => {
    setIsGenerating(true);
    setIsReceived(false);
    setReceivedFileMeta(null);
    setSecondsRemaining(299);
    setCopied(false);

    if (unsubscribeRef.current) {
      unsubscribeRef.current();
      unsubscribeRef.current = null;
    }

    try {
      const sessionResult = await createUploadSession();
      const newSessionId = typeof sessionResult === 'object' ? sessionResult.sessionId : sessionResult;
      const networkHost = typeof sessionResult === 'object' ? sessionResult.networkHost : null;
      const rawHosts = (typeof sessionResult === 'object' && Array.isArray(sessionResult.availableHosts)) 
        ? sessionResult.availableHosts 
        : [];

      // Filter out any virtual Docker or loopback IP from available hosts list
      const isValidLan = (val) => {
        if (!val || typeof val !== 'string') return false;
        const clean = val.replace(/^https?:\/\//, '').split(':')[0].trim();
        if (clean === 'localhost' || clean === '127.0.0.1' || clean === '0.0.0.0') return false;
        if (clean.startsWith('169.254.') || clean.startsWith('192.168.65.')) return false;
        if (clean.startsWith('172.') && !clean.startsWith('172.0.') && !clean.startsWith('172.1.')) {
          const sec = parseInt(clean.split('.')[1], 10);
          if (sec >= 16 && sec <= 31) return false;
        }
        return true;
      };

      const validHosts = rawHosts.filter(h => isValidLan(h.ip || h.url));

      setSessionId(newSessionId);
      sessionIdRef.current = newSessionId;
      setAvailableHosts(validHosts);

      // Determine valid LAN target origin for the mobile phone
      let targetOrigin = window.location.origin;

      if (!isValidLan(window.location.hostname)) {
        if (networkHost && isValidLan(networkHost)) {
          try {
            const parsed = new URL(networkHost.includes('://') ? networkHost : `http://${networkHost}`);
            const portPart = parsed.port ? `:${parsed.port}` : (window.location.port ? `:${window.location.port}` : ':8080');
            targetOrigin = `${window.location.protocol}//${parsed.hostname}${portPart}`;
          } catch {
            targetOrigin = networkHost;
          }
        } else if (validHosts.length > 0) {
          targetOrigin = validHosts[0].url || `http://${validHosts[0].ip}:8080`;
        }
      }

      setSelectedHostUrl(targetOrigin);
      const targetUrl = `${targetOrigin}/capture/${newSessionId}`;
      await generateQrForUrl(targetUrl);

      unsubscribeRef.current = subscribeToUpload(newSessionId, (uploadedData) => {
        handleUploadSuccess(uploadedData);
      });
    } catch (err) {
      console.error('Failed to initialize QR session:', err);
    } finally {
      setIsGenerating(false);
    }
  }, [handleUploadSuccess]);

  const handleSwitchHost = (hostUrl) => {
    if (!sessionIdRef.current) return;
    try {
      const parsed = new URL(hostUrl.includes('://') ? hostUrl : `http://${hostUrl}`);
      const portPart = parsed.port ? `:${parsed.port}` : (window.location.port ? `:${window.location.port}` : ':8080');
      const newOrigin = `${window.location.protocol}//${parsed.hostname}${portPart}`;
      setSelectedHostUrl(newOrigin);
      const targetUrl = `${newOrigin}/capture/${sessionIdRef.current}`;
      generateQrForUrl(targetUrl);
    } catch {
      setSelectedHostUrl(hostUrl);
      const targetUrl = `${hostUrl}/capture/${sessionIdRef.current}`;
      generateQrForUrl(targetUrl);
    }
  };

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
        className="qr-modal-card qr-centered-modal-card" 
        onClick={(e) => e.stopPropagation()}
        style={{ maxWidth: '440px' }}
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
                    <Loader2 size={32} className="spin qr-spinner-icon" />
                  </div>
                ) : qrDataUrl ? (
                  <img 
                    src={qrDataUrl} 
                    alt={`QR Code for capture session ${sessionId}`} 
                    className="qr-modal-svg"
                  />
                ) : (
                  <div className="qr-loading-spinner">
                    <Loader2 size={32} className="spin qr-spinner-icon" />
                  </div>
                )}
              </div>

              <p className="qr-modal-instruction">
                Scan this QR code with your phone camera or open the direct link below.
              </p>

              {/* Direct Link Badge with Edit / Manual Override */}
              {captureUrl && (
                <div style={{
                  width: '100%',
                  boxSizing: 'border-box',
                  background: '#F8FAFC',
                  borderRadius: '8px',
                  padding: '8px 10px',
                  margin: '6px 0 12px',
                  border: '1px solid #CBD5E1',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '6px'
                }}>
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: '6px',
                    width: '100%',
                    boxSizing: 'border-box'
                  }}>
                    <span 
                      title={captureUrl}
                      style={{ 
                        overflow: 'hidden', 
                        textOverflow: 'ellipsis', 
                        whiteSpace: 'nowrap', 
                        fontFamily: 'monospace',
                        color: '#1E293B',
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        minWidth: 0,
                        flex: 1
                      }}
                    >
                      {captureUrl}
                    </span>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px', flexShrink: 0 }}>
                      <button
                        type="button"
                        onClick={() => {
                          navigator.clipboard?.writeText(captureUrl);
                          setCopied(true);
                          setTimeout(() => setCopied(false), 2000);
                        }}
                        title="Copy direct capture link"
                        style={{
                          background: '#FFFFFF',
                          border: '1px solid #CBD5E1',
                          borderRadius: '5px',
                          padding: '4px 8px',
                          color: copied ? '#16A34A' : '#2563EB',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '4px',
                          fontSize: '0.72rem',
                          fontWeight: 600
                        }}
                      >
                        {copied ? <Check size={13} color="#16A34A" /> : <Copy size={13} />}
                        <span>{copied ? 'Copied' : 'Copy'}</span>
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {/* Multiple IP / Interface Switcher */}
              {availableHosts.length > 1 && (
                <div style={{ margin: '0 0 10px', textAlign: 'center' }}>
                  <div style={{ fontSize: '0.7rem', color: '#64748B', marginBottom: '4px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px' }}>
                    <Wifi size={11} />
                    <span>Select Laptop Network Interface:</span>
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', justifyContent: 'center' }}>
                    {availableHosts.map((h, idx) => {
                      const isSelected = selectedHostUrl.includes(h.ip);
                      return (
                        <button
                          key={idx}
                          type="button"
                          onClick={() => handleSwitchHost(h.url || h.ip)}
                          style={{
                            fontSize: '0.7rem',
                            padding: '2px 8px',
                            borderRadius: '12px',
                            border: isSelected ? '1px solid #2563EB' : '1px solid #CBD5E1',
                            background: isSelected ? '#EFF6FF' : '#F8FAFC',
                            color: isSelected ? '#1D4ED8' : '#475569',
                            fontWeight: isSelected ? 600 : 400,
                            cursor: 'pointer'
                          }}
                        >
                          {h.name}: {h.ip}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}

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
                <Loader2 size={15} className="spin qr-spinner-icon" />
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
