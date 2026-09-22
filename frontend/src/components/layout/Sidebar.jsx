import React from 'react';
import { 
  FileText,
  LayoutDashboard,
  Users,
  DatabaseBackup,
  History, 
  ChevronLeft, 
  ChevronRight 
} from 'lucide-react';
import { getTranslation } from '../../utils/translations';
import './Sidebar.css';

export default function Sidebar({
  isAdmin = false,
  activeModule = 'gdp',
  onSelectModule,
  isCollapsed = false,
  onToggleCollapse,
  currentLanguage = 'en'
}) {
  return (
    <aside 
      className={`app-sidebar ${isCollapsed ? 'sidebar-collapsed' : 'sidebar-expanded'}`} 
      aria-label="Administrative Navigation Sidebar"
    >
      
      {/* 1. TOP / MAIN MODULE AREA */}
      <div className="sidebar-top-section">
        <nav className="sidebar-nav-list" aria-label="Main Modules">
          {isAdmin && [
            { id: 'dashboard', labelKey: 'dashboard', fallback: 'Dashboard', Icon: LayoutDashboard },
            { id: 'users', labelKey: 'userManagement', fallback: 'User Management', Icon: Users },
            { id: 'backup', labelKey: 'backup', fallback: 'Backup', Icon: DatabaseBackup }
          ].map(({ id, labelKey, fallback, Icon }) => {
            const label = getTranslation(currentLanguage, labelKey, fallback);
            return (
              <button key={id} type="button" title={label} aria-label={label}
                className={`sidebar-nav-item ${activeModule === id ? 'active' : ''}`}
                aria-current={activeModule === id ? 'page' : undefined}
                onClick={() => onSelectModule(id)}>
                <div className="sidebar-item-icon"><Icon size={18} /></div>
                {!isCollapsed && <div className="sidebar-item-text"><span className="sidebar-item-label">{label}</span></div>}
              </button>
            );
          })}
          {/* GDP Assistant - Primary Module */}
          <button
            type="button"
            className={`sidebar-nav-item ${activeModule === 'gdp' ? 'active' : ''}`}
            onClick={() => onSelectModule('gdp')}
            title={getTranslation(currentLanguage, 'gdpAssistant', 'GDP Assistant')}
            aria-current={activeModule === 'gdp' ? 'page' : undefined}
          >
            <div className="sidebar-item-icon">
              <FileText size={18} />
            </div>
            {!isCollapsed && (
              <div className="sidebar-item-text">
                <span className="sidebar-item-label">{getTranslation(currentLanguage, 'gdpAssistant', 'GDP Assistant')}</span>
                <span className="sidebar-item-sub">{getTranslation(currentLanguage, 'grievanceProcessing', 'Grievance Processing')}</span>
              </div>
            )}
          </button>
        </nav>
      </div>

      {/* 2. FLEXIBLE MIDDLE SPACER */}
      <div className="sidebar-spacer"></div>

      {/* 3. BOTTOM UTILITIES SECTION */}
      <div className="sidebar-bottom-section">
        <nav className="sidebar-nav-list" aria-label="Utilities & Settings">
          
          {/* Audit Logs */}
          <button
            type="button"
            className={`sidebar-nav-item ${activeModule === 'audit' ? 'active' : ''}`}
            onClick={() => onSelectModule('audit')}
            title={getTranslation(currentLanguage, 'auditLogs', 'Audit Logs')}
            aria-current={activeModule === 'audit' ? 'page' : undefined}
          >
            <div className="sidebar-item-icon">
              <History size={18} />
            </div>
            {!isCollapsed && (
              <div className="sidebar-item-text">
                <span className="sidebar-item-label">{getTranslation(currentLanguage, 'auditLogs', 'Audit Logs')}</span>
              </div>
            )}
          </button>

          {/* Collapse / Expand Toggle */}
          <button
            type="button"
            className="sidebar-nav-item collapse-item"
            onClick={onToggleCollapse}
            title={isCollapsed ? getTranslation(currentLanguage, 'expand', 'Expand sidebar') : getTranslation(currentLanguage, 'collapse', 'Collapse sidebar')}
            aria-label={isCollapsed ? getTranslation(currentLanguage, 'expand', 'Expand sidebar') : getTranslation(currentLanguage, 'collapse', 'Collapse sidebar')}
          >
            <div className="sidebar-item-icon">
              {isCollapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
            </div>
            {!isCollapsed && (
              <div className="sidebar-item-text">
                <span className="sidebar-item-label">{getTranslation(currentLanguage, 'collapse', 'Collapse')}</span>
              </div>
            )}
          </button>
        </nav>
      </div>

    </aside>
  );
}
