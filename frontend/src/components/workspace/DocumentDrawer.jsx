import React, { useState } from 'react';
import { 
  ChevronLeft, 
  ChevronRight, 
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

  const totalPages = petition?.totalPages || 1;
  const fileName = petition?.fileName || 'Document';
  const hasPreview = Boolean(petition?.previewUrl);

  const handlePrevPage = () => {
    setCurrentPage((prev) => Math.max(prev - 1, 1));
  };

  const handleNextPage = () => {
    setCurrentPage((prev) => Math.min(prev + 1, totalPages));
  };

  return (
    <aside 
      className={`right-document-panel ${isOpen ? 'panel-open' : 'panel-collapsed'}`}
      aria-label="Original Scanned Petition Viewer"
    >
      {isOpen && (
        <div className="right-panel-inner">
          
          {/* 1. DOCUMENT TOOLBAR — Centered Page Navigation Controls Only */}
          <div className="drawer-header drawer-header-centered">
            <div className="page-nav-controls page-nav-centered">
              <button
                type="button"
                className="toolbar-btn"
                onClick={handlePrevPage}
                disabled={currentPage <= 1}
                title="Previous page"
                aria-label="Previous page"
              >
                <ChevronLeft size={16} />
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
                <ChevronRight size={16} />
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
                  />
                ) : (
                  <img
                    src={petition.previewUrl}
                    alt={fileName}
                    className="real-uploaded-document-image"
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

          {/* 3. READ-ONLY FOOTER — Fixed stationary at bottom of right panel */}
          <div className="drawer-bottom-hint">
            <CheckCircle size={13} className="hint-icon" />
            <span>Scanned document is read-only for officer verification.</span>
          </div>

        </div>
      )}
    </aside>
  );
}
