import React, { useState } from 'react';
import { 
  ChevronLeft, 
  ChevronRight, 
  ZoomIn, 
  ZoomOut, 
  X, 
  FileText, 
  CheckCircle, 
  Stamp 
} from 'lucide-react';
import './Workspace.css';

export default function DocumentDrawer({ 
  isOpen, 
  onClose, 
  petition 
}) {
  const [currentPage, setCurrentPage] = useState(1);
  const [zoomLevel, setZoomLevel] = useState(100);

  const totalPages = petition?.totalPages || 2;
  const scannedPages = petition?.scannedDocument?.pages || [];
  const currentPageData = scannedPages.find((p) => p.pageNumber === currentPage) || scannedPages[0];

  const handleZoomIn = () => {
    setZoomLevel((prev) => Math.min(prev + 15, 175));
  };

  const handleZoomOut = () => {
    setZoomLevel((prev) => Math.max(prev - 15, 60));
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
            <div className="drawer-title-group">
              <FileText size={16} className="drawer-title-icon" />
              <div className="drawer-title-text">
                <h3 className="drawer-heading">Original Scanned Petition</h3>
                <span className="drawer-file-sub font-mono">{petition?.fileName}</span>
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
                  disabled={zoomLevel <= 60}
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
                  disabled={zoomLevel >= 175}
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

          {/* 2. DOCUMENT CANVAS — Independent Internal Scroll Context */}
          <div className="drawer-canvas-container">
            <div className="document-sheet-wrapper">
              <div 
                className="scanned-document-sheet"
                style={{ 
                  transform: `scale(${zoomLevel / 100})`, 
                  transformOrigin: 'top center'
                }}
              >
                {/* Paper Texture & Official Watermark Background */}
                <div className="doc-watermark" aria-hidden="true">OFFICIAL PETITION</div>

                {/* Page 1 Scanned Content */}
                {currentPage === 1 && (
                  <div className="doc-page-inner">
                    
                    {/* Official Grievance Receipt Stamp */}
                    <div className="doc-header-stamp-box">
                      <div className="seal-round-mock">
                        <div className="seal-inner-circle">
                          <span className="seal-text-small">GOVT OF TAMIL NADU</span>
                          <span className="seal-text-bold">RECEIVED</span>
                          <span className="seal-text-date">{currentPageData?.headerStamp?.date || '16-02-2026'}</span>
                        </div>
                      </div>

                      <div className="stamp-official-meta">
                        <div className="stamp-header-tamil">{currentPageData?.headerStamp?.title}</div>
                        <div className="stamp-header-eng">{currentPageData?.headerStamp?.subTitle}</div>
                        <div className="stamp-ref-row">
                          <span className="stamp-ref-label">Ref:</span>
                          <span className="stamp-ref-val font-mono">{currentPageData?.headerStamp?.refNo}</span>
                          <span className="stamp-date-val">Date: {currentPageData?.headerStamp?.date}</span>
                        </div>
                      </div>
                    </div>

                    {/* Two Column From / To Block */}
                    <div className="doc-address-grid">
                      <div className="doc-address-box from-box">
                        <div className="address-section-tamil whitespace-pre">
                          {currentPageData?.fromSection?.tamil}
                        </div>
                        <div className="address-section-eng whitespace-pre">
                          {currentPageData?.fromSection?.english}
                        </div>
                      </div>

                      <div className="doc-address-box to-box">
                        <div className="address-section-tamil whitespace-pre">
                          {currentPageData?.toSection?.tamil}
                        </div>
                        <div className="address-section-eng whitespace-pre">
                          {currentPageData?.toSection?.english}
                        </div>
                      </div>
                    </div>

                    {/* Subject Line */}
                    <div className="doc-subject-line">
                      <div className="subject-tamil">{currentPageData?.subject?.tamil}</div>
                      <div className="subject-eng">{currentPageData?.subject?.english}</div>
                    </div>

                    {/* Body Text */}
                    <div className="doc-body-section">
                      <div className="body-tamil whitespace-pre">
                        {currentPageData?.body?.tamil}
                      </div>
                      <div className="body-eng whitespace-pre">
                        {currentPageData?.body?.english}
                      </div>
                    </div>

                    {/* Page 1 Footer Note */}
                    <div className="doc-page-footer">
                      <span>[தொடர்ச்சி பக்கம் 2ல்... / Continued on Page 2...]</span>
                      <span className="page-number-footer">Page 1</span>
                    </div>

                  </div>
                )}

                {/* Page 2 Scanned Content */}
                {currentPage === 2 && (
                  <div className="doc-page-inner">
                    <div className="doc-page2-header">
                      <span>Petition Ref: {scannedPages[0]?.headerStamp?.refNo}</span>
                      <span>Page 2 of 2</span>
                    </div>

                    <div className="doc-body-section">
                      <div className="body-tamil whitespace-pre">
                        {currentPageData?.bodyContinued?.tamil || 'மனுவின் தொடர்ச்சி...'}
                      </div>
                      <div className="body-eng whitespace-pre">
                        {currentPageData?.bodyContinued?.english || 'Petition content continued...'}
                      </div>
                    </div>

                    {/* Official Endorsement & Verification Box */}
                    <div className="doc-endorsement-block">
                      <div className="endorsement-title">
                        <Stamp size={14} />
                        <span>DISTRICT COLLECTORATE GRIEVANCE CELL ENDORSEMENT</span>
                      </div>
                      <div className="endorsement-note">
                        "Forwarded to Block Development Officer (BDO - Village Panchayats), Perundurai for priority field inspection and submission of action taken report within 15 working days."
                      </div>
                      <div className="endorsement-sign-row">
                        <div className="sign-col">
                          <div className="sign-fake font-handwriting">P. Venkatesh, SDM</div>
                          <div className="sign-role">Special Deputy Collector (Grievance)</div>
                          <div className="sign-date">Dated: 16-02-2026</div>
                        </div>
                        <div className="endorsement-stamp-round">
                          <span>SEAL OF DISTRICT COLLECTOR ERODE</span>
                        </div>
                      </div>
                    </div>

                    <div className="doc-page-footer">
                      <span>End of Document</span>
                      <span className="page-number-footer">Page 2</span>
                    </div>

                  </div>
                )}

              </div>
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
