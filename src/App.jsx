import React, { useState } from 'react';
import Header from './components/layout/Header';
import HistoryModal from './components/layout/HistoryModal';
import SettingsModal from './components/layout/SettingsModal';
import UploadLanding from './components/upload/UploadLanding';
import ProcessingOverlay from './components/upload/ProcessingOverlay';
import WorkspaceHeader from './components/workspace/WorkspaceHeader';
import SummaryChatView from './components/workspace/SummaryChatView';
import DocumentDrawer from './components/workspace/DocumentDrawer';
import { MOCK_PETITIONS } from './data/mockPetitions';
import { ChevronRight, ChevronLeft } from 'lucide-react';
import './styles/index.css';

export default function App() {
  // Navigation / View state: 'landing' | 'processing' | 'workspace'
  const [viewState, setViewState] = useState('landing');
  
  // Current active petition
  const [activePetition, setActivePetition] = useState(MOCK_PETITIONS[0]);
  
  // Document Drawer state (Stationary left panel open/collapsed)
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  
  // Modals state
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

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
    setActivePetition(petition);
    setViewState('processing');
  };

  // Processing Completed handler
  const handleProcessingComplete = () => {
    setViewState('workspace');
    setIsDrawerOpen(false);
    showToast(`Analysis complete for ${activePetition.fileName}`);
  };

  // Reset to Upload Landing
  const handleNewPetition = () => {
    setViewState('landing');
    setIsDrawerOpen(false);
  };

  return (
    <div className="app-container">
      
      {/* Slim Top Navigation Header (Stationary, Fixed Height) */}
      <Header
        activeView={viewState}
        onNewPetition={handleNewPetition}
        onOpenHistory={() => setIsHistoryOpen(true)}
        onOpenSettings={() => setIsSettingsOpen(true)}
        historyCount={MOCK_PETITIONS.length}
      />

      {/* Main App Body (Stationary 100vh Shell) */}
      <main className="main-content">
        
        {/* View 1: Landing / Upload Screen */}
        {viewState === 'landing' && (
          <UploadLanding onSelectPetition={handleSelectPetition} />
        )}

        {/* View 2: Simulated Multi-Step OCR Processing */}
        {viewState === 'processing' && (
          <ProcessingOverlay
            petition={activePetition}
            onComplete={handleProcessingComplete}
          />
        )}

        {/* View 3: Two-Panel Petition Workspace (Fixed Desktop Layout) */}
        {viewState === 'workspace' && (
          <div className="workspace-layout">
            
            {/* Workspace Bar with ID, File, Status, and New Petition (Stationary) */}
            <WorkspaceHeader
              petition={activePetition}
              onNewPetition={handleNewPetition}
            />

            {/* True Two-Panel Body Split (Remaining Viewport Height, No Body Scroll) */}
            <div className="workspace-body-split">
              
              {/* 1. Left Original Petition Panel (Stationary) */}
              <DocumentDrawer
                isOpen={isDrawerOpen}
                onClose={() => setIsDrawerOpen(false)}
                petition={activePetition}
              />

              {/* 2. Vertically-Centered Toggle Handle (Fixed at Panel Edge) */}
              <button
                type="button"
                className={`panel-toggle-handle ${isDrawerOpen ? 'handle-panel-open' : 'handle-panel-collapsed'}`}
                onClick={() => setIsDrawerOpen(!isDrawerOpen)}
                title={isDrawerOpen ? "Collapse Original Petition" : "Open Original Petition"}
                aria-label={isDrawerOpen ? "Collapse Original Petition" : "Open Original Petition"}
              >
                {isDrawerOpen ? (
                  <ChevronLeft size={15} className="handle-chevron" />
                ) : (
                  <ChevronRight size={15} className="handle-chevron" />
                )}
                <span className="panel-toggle-handle-text">
                  {isDrawerOpen ? 'Close' : 'Original Petition'}
                </span>
              </button>

              {/* 3. Right AI Workspace Panel (Summary Stationary + Chat Isolated Scroll + Input Stationary) */}
              <section className="right-ai-panel" aria-label="AI Document Assistant">
                <SummaryChatView
                  petition={activePetition}
                />
              </section>

            </div>

          </div>
        )}

      </main>

      {/* Petition History Modal */}
      <HistoryModal
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
        currentPetitionId={activePetition?.id}
        onSelectPetition={(pet) => {
          setActivePetition(pet);
          setViewState('workspace');
          setIsDrawerOpen(false);
          showToast(`Switched to petition #${pet.id}`);
        }}
      />

      {/* Settings Modal */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        onNotify={showToast}
      />

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
