import React, { useState } from 'react';
import { 
  ChevronLeft, 
  ChevronRight, 
  ZoomIn, 
  ZoomOut, 
  X, 
  FileText, 
  CheckCircle, 
  Image as ImageIcon 
} from 'lucide-react';
import './Workspace.css';

export default function DocumentDrawer({ 
  isOpen, 
  onClose, 
  petition 
}) {
  const [currentPage, setCurrentPage] = useState(1);
  const [zoomLevel, setZoomLevel] = useState(100);

  const totalPages = petition?.totalPages || 1;
  const fileName = petition?.fileName || 'No document selected';
  const hasPreview = Boolean(petition?.previewUrl);

  const handleZoomIn = () => {
    setZoomLevel((prev) => Math.min(prev + 15, 200));
  };

  const handleZoomOut = () => {
    setZoomLevel((prev) => Math.max(prev - 15, 50));
  };

  const handleFitPage = () => {
    setZoomLevel(85);
  };

  const handleResetZoom = () => {
    setZoomLevel(100);
  };

  const handlePrevPage = () => {
    setCurrentPage((prev) => Math.max(prev - 1, 1));
  };

  const handleNextPage = () => {
    setCurrentPage((prev) => Math.min(prev + 1, totalPages));
  };

  return (
    <aside 
      className={`left-document-panel ${isOpen ? 'panel-open' : 'panel-collapsed'}`}
      aria-label="Original Scanned Petition Viewer"
    >
      {isOpen && (
        <div className="left-panel-inner">
          
          {/* 1. DOCUMENT TOOLBAR — Fixed stationary inside left panel */}
          <div className="drawer-header">
            <div className="drawer-title-group" title={fileName}>
              <FileText size={16} className="drawer-title-icon" />
              <div className="drawer-title-text">
                <h3 className="drawer-heading">Original Scanned Petition</h3>
                <span className="drawer-file-sub font-mono">{fileName}</span>
              </div>
            </div>

            {/* Toolbar Controls */}
            <div className="drawer-toolbar">
              
              {/* Page Switcher */}
              <div className="page-nav-controls">
                <button
                  type="button"
                  className="toolbar-btn"
                  onClick={handlePrevPage}
                  disabled={currentPage <= 1}
                  title="Previous page"
                  aria-label="Previous page"
                >
                  <ChevronLeft size={14} />
                </button>
                <span className="page-indicator font-mono">
                  {currentPage}/{totalPages}
                </span>
                <button
                  type="button"
                  className="toolbar-btn"
                  onClick={handleNextPage}
                  disabled={currentPage >= totalPages}
                  title="Next page"
                  aria-label="Next page"
                >
                  <ChevronRight size={14} />
                </button>
              </div>

              <div className="toolbar-separator"></div>

              {/* Zoom Controls */}
              <div className="zoom-controls">
                <button
                  type="button"
                  className="toolbar-btn"
                  onClick={handleZoomOut}
                  disabled={zoomLevel <= 50}
                  title="Zoom out"
                  aria-label="Zoom out"
                >
                  <ZoomOut size={14} />
                </button>
                <span 
                  className="zoom-indicator font-mono"
                  onClick={handleResetZoom}
                  title="Click to reset to 100%"
                  style={{ cursor: 'pointer' }}
                >
                  {zoomLevel}%
                </span>
                <button
                  type="button"
                  className="toolbar-btn"
                  onClick={handleZoomIn}
                  disabled={zoomLevel >= 200}
                  title="Zoom in"
                  aria-label="Zoom in"
                >
                  <ZoomIn size={14} />
                </button>
                <button
                  type="button"
                  className="toolbar-btn fit-btn"
                  onClick={handleFitPage}
                  title="Fit whole page in viewer"
                >
                  Fit
                </button>
              </div>

              <div className="toolbar-separator"></div>

              {/* Close Button */}
              <button
                type="button"
                className="drawer-close-btn"
                onClick={onClose}
                title="Collapse original petition preview"
                aria-label="Collapse panel"
              >
                <X size={16} />
              </button>

            </div>
          </div>

          {/* 2. DOCUMENT CANVAS — Renders the REAL User-Uploaded Document */}
          <div className="drawer-canvas-container">
            <div className="document-sheet-wrapper">
              {hasPreview ? (
                petition.isPdf ? (
                  <iframe
                    src={petition.previewUrl}
                    title={fileName}
                    className="real-uploaded-document-pdf"
                    style={{ 
                      transform: `scale(${zoomLevel / 100})`, 
                      transformOrigin: 'top center'
                    }}
                  />
                ) : (
                  <img
                    src={petition.previewUrl}
                    alt={fileName}
                    className="real-uploaded-document-image"
                    style={{ 
                      transform: `scale(${zoomLevel / 100})`, 
                      transformOrigin: 'top center'
                    }}
                  />
                )
              ) : (
                <div className="no-document-placeholder">
                  <ImageIcon size={36} className="no-doc-icon" />
                  <p className="no-doc-title">No petition document loaded.</p>
                  <span className="no-doc-sub">Upload an image or PDF to view the original scan.</span>
                </div>
              )}
            </div>
          </div>

          {/* 3. READ-ONLY FOOTER — Fixed stationary at bottom of left panel */}
          <div className="drawer-bottom-hint">
            <CheckCircle size={13} className="hint-icon" />
            <span>Scanned document is read-only for officer verification.</span>
          </div>

        </div>
      )}
    </aside>
  );
}
