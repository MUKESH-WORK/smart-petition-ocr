import React from 'react';
import { FilePlus2, History, Settings, UserCheck, ShieldCheck } from 'lucide-react';
import './Header.css';

export default function Header({ 
  onNewPetition, 
  onOpenHistory, 
  onOpenSettings,
  activeView, // 'landing' | 'processing' | 'workspace'
  historyCount = 3
}) {
  return (
    <header className="app-header">
      <div className="header-left">
        {/* Government Emblem Placeholder / SVG */}
        <div className="govt-emblem-badge" title="Government of Tamil Nadu - Grievance Cell">
          <svg className="emblem-svg" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="20" cy="20" r="19" stroke="#E4EFFB" strokeWidth="1.5" fill="#0E3052" />
            <path d="M20 7L24 15H16L20 7Z" fill="#D9531E" />
            <path d="M12 17H28V20C28 24.4183 24.4183 28 20 28C15.5817 28 12 24.4183 12 20V17Z" fill="#CBE1F7" />
            <path d="M15 20V25M20 20V26M25 20V25" stroke="#0A2540" strokeWidth="1.5" strokeLinecap="round" />
            <path d="M16 32H24" stroke="#D9531E" strokeWidth="2" strokeLinecap="round" />
          </svg>
        </div>

        <div className="brand-title-group" onClick={onNewPetition} role="button" tabIndex={0}>
          <div className="brand-title-row">
            <h1 className="brand-title">Petition Assistant</h1>
            <span className="brand-badge">Official</span>
          </div>
          <span className="brand-subtitle">Government Grievance Pre-Processing</span>
        </div>

        {/* Navigation */}
        <nav className="header-nav">
          <button 
            type="button" 
            className={`nav-link ${activeView === 'landing' ? 'active' : ''}`}
            onClick={onNewPetition}
            title="Upload a new petition"
          >
            <FilePlus2 size={15} />
            <span>New Petition</span>
          </button>

          <button 
            type="button" 
            className="nav-link"
            onClick={onOpenHistory}
            title="View recently processed petitions"
          >
            <History size={15} />
            <span>History</span>
            {historyCount > 0 && <span className="nav-counter">{historyCount}</span>}
          </button>
        </nav>
      </div>

      <div className="header-right">
        {/* Officer Profile Badge */}
        <div className="officer-profile-card">
          <div className="officer-avatar" aria-hidden="true">
            <UserCheck size={16} />
          </div>
          <div className="officer-info">
            <span className="officer-name">S. Ramanathan</span>
            <span className="officer-role">Tahsildar • Grievance Cell</span>
          </div>
        </div>

        <div className="header-divider" aria-hidden="true"></div>

        {/* Settings Button */}
        <button 
          type="button" 
          className="header-icon-btn" 
          onClick={onOpenSettings}
          title="Assistant Settings"
          aria-label="Settings"
        >
          <Settings size={17} />
        </button>
      </div>
    </header>
  );
}
