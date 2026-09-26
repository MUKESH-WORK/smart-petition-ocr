import React, { useState, useEffect, useCallback } from 'react';
import Header from './components/layout/Header';
import Sidebar from './components/layout/Sidebar';
import UploadLanding from './components/upload/UploadLanding';
import ProcessingOverlay from './components/upload/ProcessingOverlay';
import WorkspaceHeader from './components/workspace/WorkspaceHeader';
import SummaryChatView from './components/workspace/SummaryChatView';
import DocumentDrawer from './components/workspace/DocumentDrawer';
import AuditLogsView from './components/audit/AuditLogsView';
import ProfileView from './components/profile/ProfileView';
import MobileCapturePage from './components/mobile/MobileCapturePage';
import LoginPage from './components/auth/LoginPage';
import AdminWorkspace from './components/admin/AdminWorkspace';
import AdminNotifications from './components/admin/AdminNotifications';
import { ChevronRight, ChevronLeft } from 'lucide-react';
import { fetchAuditHistory, fetchPetitionBySourceId, logoutAdminSession, updateMyProfile, fetchAdminUsers } from './services/apiService';
import ErrorBoundary from './components/common/ErrorBoundary';
import PrivacyPolicyPage from './components/pages/PrivacyPolicyPage';
import TermsPage from './components/pages/TermsPage';
import './styles/index.css';

function getStaticPageRoute() {
  if (typeof window === 'undefined') return null;
  const path = window.location.pathname.toLowerCase();
  const hash = window.location.hash.toLowerCase();
  if (path === '/privacy' || path.startsWith('/privacy/') || hash === '#/privacy' || hash === '#privacy') return 'privacy';
  if (path === '/terms' || path.startsWith('/terms/') || hash === '#/terms' || hash === '#terms') return 'terms';
  return null;
}

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

function createProfileFromSession(session) {
  if (!session) return null;
  const isAdm = Boolean(session.role === 'admin' || session.isAdmin || session.user?.isAdmin || session.user?.is_admin);
  const u = session.user || session.profile || session || {};

  return {
    fullName: u.name || u.fullName || '',
    name: u.name || u.fullName || '',
    nameTamil: u.name_tamil || u.nameTamil || '',
    designation: u.designation || (isAdm ? 'District Administrator' : 'Department Officer'),
    department: u.department || '',
    officerId: u.id || u.officerId || '',
    id: u.id || u.officerId || '',
    email: u.email || '',
    phone: u.mobile || u.phone || '',
    mobile: u.mobile || u.phone || '',
    role: isAdm ? 'District Administrator' : (u.role || session.role || 'Department User'),
    assignedOffice: u.assignedOffice || 'Erode District Collectorate, Tamil Nadu'
  };
}

const PROFILE_STORAGE_KEY = 'tn_gdp_officer_profile';
const SESSION_STORAGE_KEY = 'gdp_user_session';
const ACTIVE_PETITION_KEY = 'gdp_active_petition';

function getInitialSession() {
  if (typeof window === 'undefined') return null;
  try {
    const raw = sessionStorage.getItem(SESSION_STORAGE_KEY) || localStorage.getItem(SESSION_STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed && (parsed.id || parsed.officerId || parsed.user?.id)) {
        return parsed;
      }
    }
    const token = localStorage.getItem('auth_token') || localStorage.getItem('token');
    const officerId = localStorage.getItem('officer_id');
    const officerName = localStorage.getItem('officer_name');
    const officerRole = localStorage.getItem('officer_role');
    if (token && officerId) {
      const isAdm = officerRole === 'admin';
      return {
        id: officerId,
        officerId: officerId,
        name: officerName || officerId,
        role: isAdm ? 'admin' : 'user',
        isAdmin: isAdm,
        access_token: token
      };
    }
  } catch (e) {
    console.warn('Session restoration notice:', e);
  }
  return null;
}

export default function App() {
  const [session, setSession] = useState(() => getInitialSession());
  const [staticPage, setStaticPage] = useState(() => getStaticPageRoute());

  useEffect(() => {
    const handlePop = () => setStaticPage(getStaticPageRoute());
    window.addEventListener('popstate', handlePop);
    window.addEventListener('hashchange', handlePop);
    return () => {
      window.removeEventListener('popstate', handlePop);
      window.removeEventListener('hashchange', handlePop);
    };
  }, []);

  const handleLoginSuccess = (newSession) => {
    try {
      if (newSession) {
        sessionStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(newSession));
        localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(newSession));
      } else {
        sessionStorage.removeItem(SESSION_STORAGE_KEY);
        localStorage.removeItem(SESSION_STORAGE_KEY);
      }
    } catch (e) {
      console.warn('Session save notice:', e);
    }
    setSession(newSession);
  };

  const handleAppLogout = async () => {
    try {
      const officerId = session?.id || session?.officerId || session?.user?.id;
      if (officerId) {
        await logoutAdminSession(officerId);
      }
    } catch (err) {
      console.warn('Logout session cleanup warning:', err);
    } finally {
      sessionStorage.removeItem(SESSION_STORAGE_KEY);
      localStorage.removeItem(SESSION_STORAGE_KEY);
      sessionStorage.removeItem(ACTIVE_PETITION_KEY);
      localStorage.removeItem('auth_token');
      localStorage.removeItem('token');
      localStorage.removeItem('officer_id');
      localStorage.removeItem('officer_name');
      localStorage.removeItem('officer_role');
      setSession(null);
    }
  };

  if (staticPage === 'privacy') {
    return <PrivacyPolicyPage onBack={() => { window.history.pushState({}, '', '/'); setStaticPage(null); }} />;
  }
  if (staticPage === 'terms') {
    return <TermsPage onBack={() => { window.history.pushState({}, '', '/'); setStaticPage(null); }} />;
  }

  // Render Mobile QR Capture directly at root level without workstation overhead
  const captureSessionId = getCaptureSessionFromUrl();
  if (captureSessionId) {
    return <MobileCapturePage sessionId={captureSessionId} />;
  }

  if (!session) {
    return <LoginPage onLogin={handleLoginSuccess} />;
  }

  return <Workstation session={session} onLogout={handleAppLogout} />;
}

function Workstation({ session, onLogout }) {
  const isAdmin = session?.role === 'admin' || session?.isAdmin;
  // Check if current route is dedicated mobile capture page
  const [mobileSessionId, setMobileSessionId] = useState(() => getCaptureSessionFromUrl());

  // Officer profile state derived dynamically from session
  const [officerProfile, setOfficerProfile] = useState(() => createProfileFromSession(session));

  useEffect(() => {
    if (session) {
      setOfficerProfile(createProfileFromSession(session));
    }
  }, [session]);

  const handleSaveProfile = async (updatedProfile) => {
    setOfficerProfile(updatedProfile);
    try {
      localStorage.setItem(PROFILE_STORAGE_KEY, JSON.stringify(updatedProfile));
      await updateMyProfile({
        name: updatedProfile.fullName || updatedProfile.name,
        name_tamil: updatedProfile.nameTamil || updatedProfile.name_tamil,
        mobile: updatedProfile.phone || updatedProfile.mobile,
        email: updatedProfile.email,
        department: updatedProfile.department
      });
      showToast('Profile updated and saved to database successfully.');
    } catch (err) {
      console.error('Failed to persist officer profile to database:', err);
      showToast('Profile saved locally (database update warning).');
    }
  };

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
  const [activeModule, setActiveModule] = useState(isAdmin ? 'dashboard' : 'gdp');

  // Current active petition (Single source of truth for uploaded document)
  const [activePetition, setActivePetition] = useState(() => {
    if (typeof window === 'undefined') return null;
    try {
      const saved = sessionStorage.getItem(ACTIVE_PETITION_KEY);
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });

  // GDP Assistant internal view state: 'landing' | 'processing' | 'workspace'
  const [viewState, setViewState] = useState(() => {
    if (typeof window === 'undefined') return 'landing';
    try {
      const saved = sessionStorage.getItem(ACTIVE_PETITION_KEY);
      return saved ? 'workspace' : 'landing';
    } catch {
      return 'landing';
    }
  });

  // Session audit records list (Maintains real activity records in current session)
  const [auditRecords, setAuditRecords] = useState([]);
  const [adminActivity, setAdminActivity] = useState([]);
  const [officersList, setOfficersList] = useState([]);
  
  // Document Drawer state (Right panel open/collapsed in workspace)
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  
  // Sidebar collapsed state
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(() => isAdmin && window.matchMedia('(max-width: 640px)').matches);

  useEffect(() => {
    if (!isAdmin) return;
    const mobile = window.matchMedia('(max-width: 640px)');
    const collapseOnMobile = () => { if (mobile.matches) setIsSidebarCollapsed(true); };
    mobile.addEventListener('change', collapseOnMobile);
    return () => mobile.removeEventListener('change', collapseOnMobile);
  }, [isAdmin]);

  // Load system officers list when admin
  useEffect(() => {
    if (isAdmin) {
      fetchAdminUsers().then((users) => {
        if (Array.isArray(users)) {
          setOfficersList(users);
        }
      }).catch((err) => console.warn('Could not load officers list:', err));
    }
  }, [isAdmin]);
  
  // Language state: 'en' | 'ta'
  const [currentLanguage, setCurrentLanguage] = useState('en');

  // Synchronize data-lang on HTML root for global CSS resilience
  useEffect(() => {
    document.documentElement.setAttribute('data-lang', currentLanguage);
    document.documentElement.lang = currentLanguage;
  }, [currentLanguage]);

  // Toast notifications state
  const [toasts, setToasts] = useState([]);

  const showToast = (message) => {
    const id = Date.now();
    setToasts((prev) => [...prev, { id, message }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 3000);
  };

  const handleRefreshAudit = useCallback(async (officerId = null) => {
    try {
      const activeOfficerId = officerId || (!isAdmin ? (session?.officerId || session?.id || session?.user?.id || localStorage.getItem('officer_id')) : null);
      const records = await fetchAuditHistory(activeOfficerId);
      if (Array.isArray(records)) {
        setAuditRecords(records);
      }
    } catch (err) {
      console.warn('Failed to refresh audit history:', err);
    }
  }, [isAdmin, session]);

  // Fetch officer audit records from backend on mount and officer/session change
  useEffect(() => {
    handleRefreshAudit();
  }, [session?.officerId, session?.id, session?.email, isAdmin, handleRefreshAudit]);

  // Upload / Petition Selection handler
  const handleSelectPetition = useCallback((petition) => {
    setActivePetition((prev) => {
      if (prev?.previewUrl && prev.previewUrl !== petition?.previewUrl) {
        try { URL.revokeObjectURL(prev.previewUrl); } catch (e) {}
      }
      return petition;
    });
    try {
      if (petition) {
        sessionStorage.setItem(ACTIVE_PETITION_KEY, JSON.stringify(petition));
      } else {
        sessionStorage.removeItem(ACTIVE_PETITION_KEY);
      }
    } catch (e) {}
    setActiveModule('gdp');
    setViewState('processing');
  }, []);

  // Processing Completed handler — stable reference required by ProcessingOverlay useEffect
  const handleProcessingComplete = useCallback((analyzedPetition) => {
    setActivePetition((prev) => {
      const finalPetition = analyzedPetition || prev;
      if (finalPetition) {
        try {
          sessionStorage.setItem(ACTIVE_PETITION_KEY, JSON.stringify(finalPetition));
        } catch (e) {}
        const auditEntry = {
          id: `AUD-${Date.now()}`,
          timestamp: new Date().toISOString(),
          category: 'GDP Assistant',
          categoryLabel: 'GDP Assistant',
          officer: 'USER',
          source_id: finalPetition.source_id || finalPetition.id || 'SESSION-001',
          details: `Processed: ${finalPetition.fileName} (${finalPetition.portalDetails?.grievanceType || 'Grievance Analysis Complete'})`,
          rawPetition: finalPetition
        };
        setAuditRecords((records) => [auditEntry, ...records]);
        showToast(`Analysis complete for ${finalPetition.fileName || 'Petition'}`);
      }
      return analyzedPetition || prev;
    });
    setViewState('workspace');
    setIsDrawerOpen(false);
  }, []);

  // Log user-submitted prompts in GDP Assistant to Audit Trail
  const handleLogUserMessage = (promptText, petition) => {
    if (!promptText) return;
    const newEntry = {
      id: `AUD-${Date.now()}`,
      timestamp: new Date().toISOString(),
      category: 'GDP Assistant',
      categoryLabel: 'GDP Assistant',
      officer: 'USER',
      source_id: petition?.id || petition?.fileName || 'SESSION-001',
      details: promptText,
      rawPetition: petition
    };
    setAuditRecords((prev) => [newEntry, ...prev]);
  };

  // Reset to Upload Landing (cleans up memory)
  const handleNewPetition = () => {
    if (activePetition?.previewUrl) {
      try { URL.revokeObjectURL(activePetition.previewUrl); } catch (e) {}
    }
    try { sessionStorage.removeItem(ACTIVE_PETITION_KEY); } catch (e) {}
    setActivePetition(null);
    setActiveModule('gdp');
    setViewState('landing');
    setIsDrawerOpen(false);
  };

  // Selecting an audit record from the Audit Logs page
  const handleSelectAuditRecord = async (record) => {
    if (record) {
      if (record.source_id && (!record.rawPetition || !record.rawPetition.portalDetails)) {
        showToast('Loading petition details...');
        const fullDoc = await fetchPetitionBySourceId(record.source_id);
        if (fullDoc) {
          setActivePetition(fullDoc);
          setActiveModule('gdp');
          setViewState('workspace');
          setIsDrawerOpen(false);
          showToast(`Loaded petition #${fullDoc.id}`);
          return;
        }
      }
      setActivePetition(record.rawPetition || record);
      setActiveModule('gdp');
      setViewState('workspace');
      setIsDrawerOpen(false);
      showToast(`Loaded petition #${record.id}`);
    }
  };

  // Handle user logout action from top-right officer profile menu
  const handleLogout = () => {
    if (activePetition?.previewUrl) URL.revokeObjectURL(activePetition.previewUrl);
    onLogout();
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
        notifications={isAdmin ? <AdminNotifications activity={adminActivity} petitionActivity={auditRecords} /> : null}
        loginRole={session?.role}
        officerProfile={officerProfile}
        onLogoClick={handleNewPetition}
        currentLanguage={currentLanguage}
        onLanguageChange={setCurrentLanguage}
        onNavigateToProfile={() => setActiveModule('profile')}
        onLogout={handleLogout}
      />

      {/* 2. Application Body Container (Left Sidebar + Main Content Area) */}
      <div className={`app-body-container${isAdmin ? ' admin-layout' : ''}`}>
        
        {/* Left Administrative Sidebar */}
        <Sidebar
          isAdmin={isAdmin}
          activeModule={activeModule}
          onSelectModule={(mod) => {
            setActiveModule(mod);
            if (isAdmin && window.matchMedia('(max-width: 640px)').matches) setIsSidebarCollapsed(true);
          }}
          isCollapsed={isSidebarCollapsed}
          onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
          currentLanguage={currentLanguage}
        />

        {/* Main Application Content Area */}
        <main className="main-content">
          {isAdmin && (
            <AdminWorkspace
              activeModule={activeModule}
              onNavigate={setActiveModule}
              onActivityChange={setAdminActivity}
              currentLanguage={currentLanguage}
            />
          )}
          
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
                  onCancel={() => setViewState('landing')}
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
                      <ErrorBoundary onReset={() => setViewState('landing')}>
                        <SummaryChatView
                          petition={activePetition}
                          onLogUserMessage={handleLogUserMessage}
                        />
                      </ErrorBoundary>
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
              isAdmin={isAdmin}
              officers={officersList}
              onRefreshAudit={handleRefreshAudit}
              currentPetitionId={activePetition?.id}
              onSelectPetition={handleSelectAuditRecord}
              onNavigateToGDP={() => {
                setActiveModule('gdp');
                if (!activePetition) setViewState('landing');
              }}
            />
          )}

          {/* VIEW C: FULL-PAGE MY PROFILE MODULE */}
          {activeModule === 'profile' && (
            <ProfileView
              officerProfile={officerProfile}
              loginRole={session?.role}
              isAdmin={session?.role === 'admin'}
              currentLanguage={currentLanguage}
              onSaveProfile={handleSaveProfile}
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
