import React from 'react';
import { 
  FileText, 
  History, 
  Settings, 
  ChevronLeft, 
  ChevronRight 
} from 'lucide-react';
import './Sidebar.css';

export default function Sidebar({
  activeModule = 'gdp',
  onSelectModule,
  isCollapsed = false,
  onToggleCollapse
}) {
  return (
    <aside 
      className={`app-sidebar ${isCollapsed ? 'sidebar-collapsed' : 'sidebar-expanded'}`} 
      aria-label="Administrative Navigation Sidebar"
    >
      
      {/* 1. TOP / MAIN MODULE AREA */}
      <div className="sidebar-top-section">
        <nav className="sidebar-nav-list" aria-label="Main Modules">
          {/* GDP Assistant - Primary Module */}
          <button
            type="button"
            className={`sidebar-nav-item ${activeModule === 'gdp' ? 'active' : ''}`}
            onClick={() => onSelectModule('gdp')}
            title="GDP Assistant (Grievance Document Processing)"
            aria-current={activeModule === 'gdp' ? 'page' : undefined}
          >
            <div className="sidebar-item-icon">
              <FileText size={18} />
            </div>
            {!isCollapsed && (
              <div className="sidebar-item-text">
                <span className="sidebar-item-label">GDP Assistant</span>
                <span className="sidebar-item-sub">Grievance Processing</span>
              </div>
            )}
            {!isCollapsed && activeModule === 'gdp' && (
              <span className="active-dot-indicator" aria-hidden="true"></span>
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
            title="Audit Logs (Processed Petitions History)"
            aria-current={activeModule === 'audit' ? 'page' : undefined}
          >
            <div className="sidebar-item-icon">
              <History size={18} />
            </div>
            {!isCollapsed && (
              <div className="sidebar-item-text">
                <span className="sidebar-item-label">Audit Logs</span>
              </div>
            )}
            {!isCollapsed && activeModule === 'audit' && (
              <span className="active-dot-indicator" aria-hidden="true"></span>
            )}
          </button>

          {/* Settings */}
          <button
            type="button"
            className={`sidebar-nav-item ${activeModule === 'settings' ? 'active' : ''}`}
            onClick={() => onSelectModule('settings')}
            title="Settings"
            aria-current={activeModule === 'settings' ? 'page' : undefined}
          >
            <div className="sidebar-item-icon">
              <Settings size={18} />
            </div>
            {!isCollapsed && (
              <div className="sidebar-item-text">
                <span className="sidebar-item-label">Settings</span>
              </div>
            )}
            {!isCollapsed && activeModule === 'settings' && (
              <span className="active-dot-indicator" aria-hidden="true"></span>
            )}
          </button>

          {/* Collapse / Expand Toggle */}
          <button
            type="button"
            className="sidebar-nav-item collapse-item"
            onClick={onToggleCollapse}
            title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
            aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            <div className="sidebar-item-icon">
              {isCollapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
            </div>
            {!isCollapsed && (
              <div className="sidebar-item-text">
                <span className="sidebar-item-label">Collapse</span>
              </div>
            )}
          </button>
        </nav>
      </div>

    </aside>
  );
}
