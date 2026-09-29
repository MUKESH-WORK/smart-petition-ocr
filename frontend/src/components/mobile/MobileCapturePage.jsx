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
  Edit3,
  Plus,
  Trash2
} from 'lucide-react';
import { uploadPetitionImage } from '../../services/uploadSessionService';
import { 
  saveMobileDraft, 
  loadMobileDraft, 
  deleteMobileDraft, 
  downscaleMobilePhotoIfHuge 
} from '../../utils/mobileStorage';
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
  const [scanPages, setScanPages] = useState([]);
  const [customFileName, setCustomFileName] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [fileDetails, setFileDetails] = useState(null);

  const cameraInputRef = useRef(null);
  const docInputRef = useRef(null);
  const galleryInputRef = useRef(null);
  const previewUrlsRef = useRef(new Set());

  const createPreviewUrl = (file) => {
    const url = URL.createObjectURL(file);
    previewUrlsRef.current.add(url);
    return url;
  };

  const revokePreviewUrl = (url) => {
    if (url && previewUrlsRef.current.has(url)) {
      URL.revokeObjectURL(url);
      previewUrlsRef.current.delete(url);
    }
  };

  // Restore draft from IndexedDB if mobile browser reloads or unloads after opening camera
  useEffect(() => {
    if (!sessionId) return;
    let isMounted = true;

    loadMobileDraft(sessionId)
      .then((draft) => {
        if (!isMounted || !draft || !draft.file) return;
        const files = draft.files || [draft.file];
        const isPdf = files.length === 1 && (files[0].type === 'application/pdf' || files[0].name?.toLowerCase().endsWith('.pdf'));
        if (isPdf) {
          setSelectedFile(files[0]);
          setPreviewUrl(null);
        } else {
          const restoredPages = files.map((file) => ({ file, previewUrl: createPreviewUrl(file) }));
          setScanPages(restoredPages);
          setSelectedFile(null);
          setPreviewUrl(null);
        }
        setCustomFileName(draft.customFileName || draft.meta?.name || '');
        setFileDetails({ ...draft.meta, isPdf, pageCount: files.length });
      })
      .catch((err) => {
        console.warn('Draft restoration notice:', err);
      });

    return () => {
      isMounted = false;
    };
  }, [sessionId]);

  // Release all generated previews when leaving the capture page.
  useEffect(() => {
    return () => {
      previewUrlsRef.current.forEach((url) => URL.revokeObjectURL(url));
      previewUrlsRef.current.clear();
    };
  }, []);

  const persistScanDraft = (pages, meta, fileName) => {
    if (sessionId) {
      saveMobileDraft(sessionId, pages.map((page) => page.file), meta, fileName).catch((err) => {
        console.warn('IndexedDB auto-save warning:', err);
      });
    }
  };

  const prepareImageFile = async (rawFile) => {
    const isImage = Boolean(
      (rawFile.type && rawFile.type.startsWith('image/')) ||
      (rawFile.name && rawFile.name.match(/\.(jpg|jpeg|png|webp|heic|bmp|tiff|tif|svg)$/i))
    );
    if (!isImage) throw new Error('Please capture or select image pages, or upload an existing PDF.');

    try {
      return await downscaleMobilePhotoIfHuge(rawFile, 2400, 0.92);
    } catch (scaleErr) {
      console.warn('Downscaling fallback to original file:', scaleErr);
      return rawFile;
    }
  };

  const appendImagePages = async (rawFiles) => {
    const files = Array.from(rawFiles || []).filter(Boolean);
    if (!files.length) return;
    try {
      const newPages = [];
      for (const rawFile of files) {
        const file = await prepareImageFile(rawFile);
        newPages.push({ file, previewUrl: createPreviewUrl(file) });
      }

      revokePreviewUrl(previewUrl);
      const nextPages = [...scanPages, ...newPages];
      setScanPages(nextPages);
      setSelectedFile(null);
      setPreviewUrl(null);
      setErrorMessage('');
      const totalSize = nextPages.reduce((sum, page) => sum + page.file.size, 0);
      const sizeFormatted = totalSize > 1024 * 1024
        ? `${(totalSize / (1024 * 1024)).toFixed(1)} MB`
        : `${Math.max(1, Math.round(totalSize / 1024))} KB`;
      const initialName = customFileName.trim() || `petition_${new Date().toISOString().slice(0, 10)}.pdf`;
      const meta = { name: initialName, size: sizeFormatted, type: 'application/pdf', isPdf: false, pageCount: nextPages.length };
      setCustomFileName(initialName);
      setFileDetails(meta);
      persistScanDraft(nextPages, meta, initialName);
    } catch (err) {
      setErrorMessage(err.message || 'Could not prepare the scanned pages. Please choose JPG or PNG images.');
    }
  };

  const handleFileChange = async (e) => {
    const rawFiles = Array.from(e.target.files || []);
    if (!rawFiles.length) return;
    const rawFile = rawFiles[0];

    const isPdf = Boolean(
      (rawFile.type && rawFile.type === 'application/pdf') ||
      (rawFile.name && rawFile.name.toLowerCase().endsWith('.pdf'))
    );
    const isImage = Boolean(
      (rawFile.type && rawFile.type.startsWith('image/')) ||
      (rawFile.name && rawFile.name.match(/\.(jpg|jpeg|png|webp|heic|bmp|tiff|tif|svg)$/i))
    );

    if (!isPdf && !isImage) {
      setErrorMessage('Please select a valid document (PDF) or image (JPG, PNG, WEBP, etc.).');
      return;
    }

    setErrorMessage('');
    if (!isPdf) {
      await appendImagePages(rawFiles);
      e.target.value = '';
      return;
    }

    const processedFile = rawFile;

    if (previewUrl && previewUrl.startsWith('blob:')) {
      revokePreviewUrl(previewUrl);
    }
    scanPages.forEach((page) => revokePreviewUrl(page.previewUrl));
    setScanPages([]);

    const objectUrl = createPreviewUrl(processedFile);
    setSelectedFile(processedFile);
    setPreviewUrl(objectUrl);

    const sizeFormatted = processedFile.size > 1024 * 1024 
      ? `${(processedFile.size / (1024 * 1024)).toFixed(1)} MB` 
      : `${Math.max(1, Math.round(processedFile.size / 1024))} KB`;

    // Detect extension from file name or default
    const existingExtMatch = processedFile.name ? processedFile.name.match(/\.[0-9a-z]+$/i) : null;
    const defaultExt = isPdf ? '.pdf' : (existingExtMatch ? existingExtMatch[0] : '.jpg');

    const initialName = processedFile.name && !processedFile.name.match(/^\d{10,}/) 
      ? processedFile.name 
      : `petition_${new Date().toISOString().slice(0, 10)}${defaultExt}`;

    const meta = {
      name: initialName,
      size: sizeFormatted,
      type: processedFile.type || (isPdf ? 'application/pdf' : 'image/jpeg'),
      isPdf: isPdf,
      lastModified: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setCustomFileName(initialName);
    setFileDetails(meta);

    persistScanDraft([{ file: processedFile }], meta, initialName);
    e.target.value = '';
  };

  const handleCameraCapture = (e) => {
    void appendImagePages(e.target.files);
    e.target.value = '';
  };

  const handleGallerySelection = async (e) => {
    const files = Array.from(e.target.files || []);
    const pdfFile = files.find((file) => file.type === 'application/pdf' || file.name?.toLowerCase().endsWith('.pdf'));
    if (pdfFile) {
      if (files.length > 1) {
        setErrorMessage('Choose one PDF, or select image pages together. Do not mix PDFs and images in one selection.');
        e.target.value = '';
        return;
      }
      await handleFileChange({ target: { files: [pdfFile], value: e.target.value } });
      e.target.value = '';
      return;
    }
    await appendImagePages(files);
    e.target.value = '';
  };

  const handleRemoveScanPage = (index) => {
    const removed = scanPages[index];
    revokePreviewUrl(removed?.previewUrl);
    const nextPages = scanPages.filter((_, pageIndex) => pageIndex !== index);
    setScanPages(nextPages);
    if (nextPages.length === 0) {
      setFileDetails(null);
      setCustomFileName('');
      if (sessionId) deleteMobileDraft(sessionId).catch(() => {});
      return;
    }
    const totalSize = nextPages.reduce((sum, page) => sum + page.file.size, 0);
    const sizeFormatted = totalSize > 1024 * 1024 ? `${(totalSize / (1024 * 1024)).toFixed(1)} MB` : `${Math.max(1, Math.round(totalSize / 1024))} KB`;
    const meta = { name: customFileName, size: sizeFormatted, type: 'application/pdf', isPdf: false, pageCount: nextPages.length };
    setFileDetails(meta);
    persistScanDraft(nextPages, meta, customFileName);
  };

  const handleRetake = () => {
    revokePreviewUrl(previewUrl);
    setSelectedFile(null);
    setPreviewUrl(null);
    scanPages.forEach((page) => revokePreviewUrl(page.previewUrl));
    setScanPages([]);
    setFileDetails(null);
    setCustomFileName('');
    setErrorMessage('');
    
    if (sessionId) {
      deleteMobileDraft(sessionId).catch(() => {});
    }

    if (cameraInputRef.current) cameraInputRef.current.value = '';
    if (docInputRef.current) docInputRef.current.value = '';
    if (galleryInputRef.current) galleryInputRef.current.value = '';
  };

  const handleUpload = async () => {
    if ((!selectedFile && scanPages.length === 0) || !sessionId) {
      setErrorMessage('Missing file or session ID.');
      return;
    }

    setIsUploading(true);
    setErrorMessage('');

    let fileToUpload = selectedFile;
    const isMultiPageScan = scanPages.length > 1;
    if (scanPages.length > 0) {
      if (isMultiPageScan) {
        setIsUploading(true);
        try {
          const baseName = (customFileName.trim() || `petition_${new Date().toISOString().slice(0, 10)}`).replace(/\.(pdf|jpg|jpeg|png|webp|bmp|tiff|tif)$/i, '');
          const { createScannedPdf } = await import('../../utils/mobileScan');
          fileToUpload = await createScannedPdf(scanPages.map((page) => page.file), `${baseName}.pdf`);
        } catch (pdfErr) {
          setIsUploading(false);
          setErrorMessage(pdfErr.message || 'Could not combine the scanned pages into a PDF.');
          return;
        }
      } else {
        fileToUpload = scanPages[0].file;
      }
    }

    const isPdf = Boolean(
      (fileToUpload.type && fileToUpload.type === 'application/pdf') ||
      (fileToUpload.name && fileToUpload.name.toLowerCase().endsWith('.pdf'))
    );

    const defaultFileExt = isPdf ? '.pdf' : (fileToUpload.name.match(/\.[0-9a-z]+$/i)?.[0] || '.jpg');
    const fileBaseName = (customFileName.trim() || 'petition').replace(/\.[0-9a-z]+$/i, '');
    const finalFileName = `${fileBaseName}${defaultFileExt}`;

    try {
      await uploadPetitionImage(sessionId, fileToUpload, finalFileName);
      setFileDetails(prev => ({ ...prev, name: finalFileName }));
      
      // Clean up temporary draft from IndexedDB upon successful upload
      if (sessionId) {
        deleteMobileDraft(sessionId).catch(() => {});
      }
      
      setIsUploading(false);
      setUploadSuccess(true);
    } catch (err) {
      console.error('Mobile upload error:', err);
      setIsUploading(false);
      setErrorMessage(err.message || 'Failed to upload petition. Please tap Upload Petition to retry.');
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
        ) : (previewUrl || scanPages.length > 0) ? (
          /* =========================================================
              STATE 2: PHOTO PREVIEW & EDITABLE FILENAME
             ========================================================= */
          <div className="mobile-card mobile-preview-card animate-fade-in">
            <div className="preview-card-header">
              <h2 className="preview-title">Petition Preview</h2>
              <span className="preview-subtitle">Verify that the document is sharp and legible</span>
            </div>

            {/* Photo / Document Container */}
            <div className={`preview-photo-frame ${fileDetails?.isPdf ? 'preview-pdf-mode' : ''}`}>
              {fileDetails?.isPdf ? (
                <div className="preview-pdf-container">
                  <div className="preview-pdf-icon-wrap">
                    <FileText size={48} className="preview-pdf-icon" />
                  </div>
                  <div className="preview-pdf-info">
                    <span className="preview-pdf-badge">PDF Document</span>
                    <span className="preview-pdf-filename font-mono">{fileDetails?.name || 'document.pdf'}</span>
                    <span className="preview-pdf-hint">Multi-page or single-page PDF document ready for upload</span>
                  </div>
                </div>
              ) : scanPages.length > 0 ? (
                <div className="mobile-scan-pages-grid" aria-label={`${scanPages.length} captured petition pages`}>
                  {scanPages.map((page, index) => (
                    <div className="mobile-scan-page-tile" key={`${page.file.name}-${index}`}>
                      <img src={page.previewUrl} alt={`Scanned petition page ${index + 1}`} />
                      <span className="mobile-scan-page-number">Page {index + 1}</span>
                      <button
                        type="button"
                        className="mobile-scan-page-remove"
                        onClick={() => handleRemoveScanPage(index)}
                        disabled={isUploading}
                        aria-label={`Remove page ${index + 1}`}
                      >
                        <Trash2 size={15} />
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                <img 
                  src={previewUrl} 
                  alt="Captured Petition Preview" 
                  className="preview-image-element"
                />
              )}
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
                  placeholder={fileDetails?.isPdf ? "e.g. petition_road_repair.pdf" : "e.g. road_repair_petition.jpg"}
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

            {scanPages.length > 0 && (
              <div className="mobile-add-page-row">
                <span>{scanPages.length} page{scanPages.length === 1 ? '' : 's'} selected</span>
                <button
                  type="button"
                  className="mobile-btn-secondary mobile-add-page-btn"
                  onClick={() => cameraInputRef.current?.click()}
                  disabled={isUploading}
                >
                  <Plus size={17} />
                  <span>Add Page</span>
                </button>
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
                <div className="viewfinder-prompt-title">Capture Every Petition Page</div>
                <p className="viewfinder-prompt-sub">
                  Capture one page, then tap Add Page for the next. You can also select several images or upload a PDF.
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

              {/* Upload PDF Document */}
              <button 
                type="button" 
                className="mobile-btn-secondary mobile-btn-pdf"
                onClick={() => docInputRef.current?.click()}
              >
                <FileText size={18} className="btn-icon pdf-btn-icon" />
                <span className="btn-text">Upload PDF Document</span>
              </button>

              {/* Secondary: Choose from Photo Gallery */}
              <button 
                type="button" 
                className="mobile-btn-secondary"
                onClick={() => galleryInputRef.current?.click()}
              >
                <ImageIcon size={18} className="btn-icon" />
                <span className="btn-text">Choose from Gallery (Images)</span>
              </button>

            </div>

            {/* Hidden HTML5 Native File Inputs */}
            <input 
              type="file" 
              ref={cameraInputRef}
              onChange={handleCameraCapture}
              accept="image/*"
              capture="environment"
              style={{ display: 'none' }}
              aria-label="Capture petition with camera"
            />

            <input 
              type="file" 
              ref={docInputRef}
              onChange={handleFileChange}
              accept="application/pdf,.pdf"
              style={{ display: 'none' }}
              aria-label="Upload PDF petition document"
            />

            <input 
              type="file" 
              ref={galleryInputRef}
              accept="image/*,application/pdf,.pdf,.jpg,.jpeg,.png,.webp,.bmp,.tiff,.tif,.heic"
              multiple
              style={{ display: 'none' }}
              onChange={handleGallerySelection}
              aria-label="Choose petition photo or document from gallery"
            />

            {/* Quality Tips */}
            <div className="mobile-tips-card">
              <div className="tips-header">
                <ShieldCheck size={15} className="tips-shield" />
                <span>Tips for Best Accuracy</span>
              </div>
              <ul className="tips-list">
                <li>PDF documents (scanned or digital) are fully supported.</li>
                <li>Supports JPG, PNG, WEBP & high-resolution camera scans.</li>
                <li>Ensure good lighting and avoid shadows on paper petitions.</li>
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
