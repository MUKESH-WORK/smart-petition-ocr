import React, { useCallback, useEffect, useRef, useState } from 'react';
import { 
  ChevronLeft, 
  ChevronRight, 
  CheckCircle, 
  Image as ImageIcon 
} from 'lucide-react';
import { getMostVisiblePage } from './pageVisibility';
import './Workspace.css';

export default function DocumentDrawer({ 
  isOpen, 
  onClose, 
  petition 
}) {
  const [currentPage, setCurrentPage] = useState(1);
  const [usePdfFallback, setUsePdfFallback] = useState(false);
  const pageRefs = useRef([]);
  const canvasRef = useRef(null);
  const scrollFrameRef = useRef(null);

  const fileName = petition?.fileName || 'Document';
  const sourceId = petition?.source_id || petition?.sourceId;
  const isPdf = Boolean(
    petition?.isPdf ||
    (petition?.fileType && petition.fileType.toLowerCase().includes('pdf')) ||
    (fileName && fileName.toLowerCase().endsWith('.pdf'))
  );
  const totalPages = isPdf ? Math.max(1, Number(petition?.totalPages) || 1) : 1;
  const effectivePreviewUrl = petition?.previewUrl || (sourceId ? `/api/v1/grievance/${sourceId}/file` : null);
  const hasPreview = Boolean(effectivePreviewUrl);

  const updateCurrentPageFromViewport = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || usePdfFallback || !isPdf) return;
    const rects = pageRefs.current.slice(0, totalPages).map((page) => page?.getBoundingClientRect() || null);
    const page = getMostVisiblePage(rects, canvas.getBoundingClientRect());
    setCurrentPage((current) => current === page ? current : page);
  }, [isPdf, totalPages, usePdfFallback]);

  const scheduleViewportUpdate = useCallback(() => {
    if (scrollFrameRef.current !== null) cancelAnimationFrame(scrollFrameRef.current);
    scrollFrameRef.current = requestAnimationFrame(() => {
      scrollFrameRef.current = null;
      updateCurrentPageFromViewport();
    });
  }, [updateCurrentPageFromViewport]);

  useEffect(() => {
    setCurrentPage(1);
    setUsePdfFallback(false);
    if (canvasRef.current) canvasRef.current.scrollTop = 0;
  }, [petition?.source_id, petition?.sourceId, petition?.previewUrl, totalPages]);

  useEffect(() => {
    if (!isOpen) return undefined;
    scheduleViewportUpdate();
    window.addEventListener('resize', scheduleViewportUpdate);
    return () => {
      window.removeEventListener('resize', scheduleViewportUpdate);
      if (scrollFrameRef.current !== null) cancelAnimationFrame(scrollFrameRef.current);
    };
  }, [isOpen, scheduleViewportUpdate]);

  const goToPage = (requestedPage) => {
    const page = Math.max(1, Math.min(requestedPage, totalPages));
    setCurrentPage(page);
    if (usePdfFallback) return;
    const canvas = canvasRef.current;
    const target = pageRefs.current[page - 1];
    if (!canvas || !target) return;
    const canvasTop = canvas.getBoundingClientRect().top;
    const targetTop = target.getBoundingClientRect().top;
    canvas.scrollTo({
      top: canvas.scrollTop + targetTop - canvasTop - canvas.clientTop,
      behavior: 'smooth'
    });
  };

  const handlePrevPage = () => goToPage(currentPage - 1);
  const handleNextPage = () => goToPage(currentPage + 1);

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
          <div
            className={`drawer-canvas-container${isPdf && sourceId && !usePdfFallback ? ' multi-page-document' : ''}`}
            ref={canvasRef}
            onScroll={scheduleViewportUpdate}
          >
            <div className="document-sheet-wrapper">
              {hasPreview ? (
                isPdf ? (
                  sourceId && !usePdfFallback ? (
                    <div className="petition-page-stack">
                      {Array.from({ length: totalPages }, (_, index) => {
                        const pageNumber = index + 1;
                        return (
                          <section
                            key={`${sourceId}-page-${pageNumber}`}
                            ref={(element) => { pageRefs.current[index] = element; }}
                            className="petition-page"
                            aria-label={`Petition page ${pageNumber}`}
                          >
                            <img
                              src={`/api/v1/grievance/${encodeURIComponent(sourceId)}/page/${pageNumber}/image`}
                              alt={`${fileName} — page ${pageNumber}`}
                              className="real-uploaded-document-image petition-page-image"
                              onLoad={scheduleViewportUpdate}
                              onError={() => setUsePdfFallback(true)}
                            />
                          </section>
                        );
                      })}
                    </div>
                  ) : (
                    <iframe
                      src={`${effectivePreviewUrl}#page=${currentPage}`}
                      title={fileName}
                      className="real-uploaded-document-pdf"
                    />
                  )
                ) : (
                  <img
                    src={effectivePreviewUrl}
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
