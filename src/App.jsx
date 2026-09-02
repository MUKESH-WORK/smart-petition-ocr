import React, { useState, useEffect } from 'react';
import Header from './components/layout/Header';
import Sidebar from './components/layout/Sidebar';
import UploadLanding from './components/upload/UploadLanding';
import ProcessingOverlay from './components/upload/ProcessingOverlay';
import WorkspaceHeader from './components/workspace/WorkspaceHeader';
import SummaryChatView from './components/workspace/SummaryChatView';
import DocumentDrawer from './components/workspace/DocumentDrawer';
import AuditLogsView from './components/audit/AuditLogsView';
import SettingsView from './components/settings/SettingsView';
import MobileCapturePage from './components/mobile/MobileCapturePage';
import { ChevronRight, ChevronLeft } from 'lucide-react';
import './styles/index.css';

function getCaptureSessionFromUrl() {
  if (typeof window === 'undefined') return null;
  const path = window.location.pathname;
  const hash = window.location.hash;
  const searchParams = new URLSearchParams(window.location.search);

  if (path.startsWith('/capture/')) {
    return path.replace('/capture/', '').split('/')[0].split('?')[0];
  }
  if (hash.startsWith('#/capture/') || hash.startsWith('#capture/')) {
    return hash.replace(/^#\/?capture\//, '').split('/')[0].split('?')[0];
  }
  if (searchParams.get('capture')) {
    return searchParams.get('capture');
  }
  return null;
}

export default function App() {
  // Check if current route is dedicated mobile capture page
  const [mobileSessionId, setMobileSessionId] = useState(() => getCaptureSessionFromUrl());

  // Listen for navigation changes
  useEffect(() => {
    const handleUrlChange = () => {
      setMobileSessionId(getCaptureSessionFromUrl());
    };

    window.addEventListener('popstate', handleUrlChange);
    window.addEventListener('hashchange', handleUrlChange);
    return () => {
      window.removeEventListener('popstate', handleUrlChange);
      window.removeEventListener('hashchange', handleUrlChange);
    };
  }, []);

  // Navigation Modules: 'gdp' | 'audit' | 'settings'
  const [activeModule, setActiveModule] = useState('gdp');

  // GDP Assistant internal view state: 'landing' | 'processing' | 'workspace'
  const [viewState, setViewState] = useState('landing');
  
  // Current active petition (Single source of truth for uploaded document)
  const [activePetition, setActivePetition] = useState(null);

  // Session audit records list (Maintains real processed documents in current session)
  const [auditRecords, setAuditRecords] = useState([]);
  
  // Document Drawer state (Right panel open/collapsed in workspace)
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  
  // Sidebar collapsed state
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  
  // Language state: 'en' | 'ta'
  const [currentLanguage, setCurrentLanguage] = useState('en');

  // Toast notifications state
  const [toasts, setToasts] = useState([]);

  const showToast = (message) => {
    const id = Date.now();
    setToasts((prev) => [...prev, { id, message }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 3000);
  };

  // Upload / Petition Selection handler
  const handleSelectPetition = (petition) => {
    if (activePetition?.previewUrl && activePetition.previewUrl !== petition.previewUrl) {
      URL.revokeObjectURL(activePetition.previewUrl);
    }
    setActivePetition(petition);
    setActiveModule('gdp');
    setViewState('processing');
  };

  // Processing Completed handler
  const handleProcessingComplete = () => {
    setViewState('workspace');
    setIsDrawerOpen(false);

    // Add to session audit logs if not already recorded
    if (activePetition) {
      setAuditRecords((prev) => {
        const exists = prev.some((item) => item.id === activePetition.id);
        if (exists) return prev;
        return [activePetition, ...prev];
      });
    }

    showToast(`Analysis complete for ${activePetition?.fileName || 'Petition'}`);
  };

  // Reset to Upload Landing (cleans up memory)
  const handleNewPetition = () => {
    if (activePetition?.previewUrl) {
      URL.revokeObjectURL(activePetition.previewUrl);
    }
    setActivePetition(null);
    setActiveModule('gdp');
    setViewState('landing');
    setIsDrawerOpen(false);
  };

  // Selecting an audit record from the Audit Logs page
  const handleSelectAuditRecord = (record) => {
    setActivePetition(record);
    setActiveModule('gdp');
    setViewState('workspace');
    setIsDrawerOpen(false);
    showToast(`Loaded petition #${record.id}`);
  };

  // -------------------------------------------------------------
  // If user is accessing the mobile capture route on phone/browser
  // -------------------------------------------------------------
  if (mobileSessionId) {
    return <MobileCapturePage sessionId={mobileSessionId} />;
  }

  // -------------------------------------------------------------
  // Otherwise render Desktop Workstation
  // -------------------------------------------------------------
  return (
    <div className="app-container">
      
      {/* 1. Slim Top Navigation Header (Stationary, Fixed Height) */}
      <Header
        onLogoClick={handleNewPetition}
        currentLanguage={currentLanguage}
        onLanguageChange={setCurrentLanguage}
      />

      {/* 2. Application Body Container (Left Sidebar + Main Content Area) */}
      <div className="app-body-container">
        
        {/* Left Administrative Sidebar */}
        <Sidebar
          activeModule={activeModule}
          onSelectModule={(mod) => setActiveModule(mod)}
          isCollapsed={isSidebarCollapsed}
          onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
        />

        {/* Main Application Content Area */}
        <main className="main-content">
          
          {/* VIEW A: GDP ASSISTANT MODULE */}
          {activeModule === 'gdp' && (
            <>
              {/* GDP View 1: Landing / Upload Screen */}
              {viewState === 'landing' && (
                <UploadLanding onSelectPetition={handleSelectPetition} />
              )}

              {/* GDP View 2: Multi-Step Document Processing */}
              {viewState === 'processing' && activePetition && (
                <ProcessingOverlay
                  petition={activePetition}
                  onComplete={handleProcessingComplete}
                />
              )}

              {/* GDP View 3: Two-Panel Petition Workspace (Left: Chat+Summary, Right: Document) */}
              {viewState === 'workspace' && activePetition && (
                <div className="workspace-layout">
                  
                  {/* Workspace Bar with ID, File, Status, and New Petition (Stationary) */}
                  <WorkspaceHeader
                    petition={activePetition}
                    onNewPetition={handleNewPetition}
                  />

                  {/* True Two-Panel Body Split (Remaining Viewport Height, No Body Scroll) */}
                  <div className="workspace-body-split">
                    
                    {/* 1. Left AI Workspace Panel (Summary & Chat in Scrollable Area + Stationary Input) */}
                    <section className="left-ai-panel" aria-label="AI Document Assistant">
                      <SummaryChatView
                        petition={activePetition}
                      />
                    </section>

                    {/* 2. Vertically-Centered Toggle Handle (Anchored to Right Panel Left Edge) */}
                    <button
                      type="button"
                      className={`panel-toggle-handle ${isDrawerOpen ? 'handle-panel-open' : 'handle-panel-collapsed'}`}
                      onClick={() => setIsDrawerOpen(!isDrawerOpen)}
                      title={isDrawerOpen ? "Collapse Original Petition" : "Open Original Petition"}
                      aria-label={isDrawerOpen ? "Collapse Original Petition" : "Open Original Petition"}
                    >
                      {isDrawerOpen ? (
                        <ChevronRight size={15} className="handle-chevron" />
                      ) : (
                        <ChevronLeft size={15} className="handle-chevron" />
                      )}
                      <span className="panel-toggle-handle-text">
                        {isDrawerOpen ? 'Close' : 'Original Petition'}
                      </span>
                    </button>

                    {/* 3. Right Original Petition Panel (Stationary) */}
                    <DocumentDrawer
                      isOpen={isDrawerOpen}
                      onClose={() => setIsDrawerOpen(false)}
                      petition={activePetition}
                    />

                  </div>

                </div>
              )}
            </>
          )}

          {/* VIEW B: FULL-PAGE AUDIT LOGS MODULE */}
          {activeModule === 'audit' && (
            <AuditLogsView
              auditRecords={auditRecords}
              currentPetitionId={activePetition?.id}
              onSelectPetition={handleSelectAuditRecord}
              onNavigateToGDP={() => {
                setActiveModule('gdp');
                if (!activePetition) setViewState('landing');
              }}
            />
          )}

          {/* VIEW C: FULL-PAGE SETTINGS MODULE */}
          {activeModule === 'settings' && (
            <SettingsView
              onNotify={showToast}
            />
          )}

        </main>

      </div>

      {/* Toast Notification Stream */}
      <div className="toast-container" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className="toast-message">
            <span>{t.message}</span>
          </div>
        ))}
      </div>

    </div>
  );
}
