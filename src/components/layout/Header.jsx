import React from 'react';
import { UserCheck } from 'lucide-react';
import './Header.css';

export default function Header({ 
  onLogoClick,
  currentLanguage = 'en',
  onLanguageChange
}) {
  return (
    <header className="app-header">
      
      {/* Left: Emblem & Administrative Co-Pilot Branding */}
      <div className="header-left">
        <div 
          className="govt-emblem-badge" 
          title="Government of Tamil Nadu - Grievance Cell"
          onClick={onLogoClick}
          style={{ cursor: 'pointer' }}
        >
          <img 
            src="/tn-emblem.png" 
            alt="Government of Tamil Nadu Official Emblem" 
            className="govt-emblem-img" 
          />
        </div>

        <div className="brand-title-group" onClick={onLogoClick} role="button" tabIndex={0}>
          <div className="brand-title-row">
            <h1 className="brand-title">Administrative Co-Pilot</h1>
          </div>
          <span className="brand-subtitle">Government Grievance Pre-Processing</span>
        </div>
      </div>

      {/* Right: Language Switcher & Officer Profile */}
      <div className="header-right">
        
        {/* Language Toggle: EN / தமிழ் */}
        <div className="header-lang-toggle" title="Select Interface Language / மொழி">
          <button 
            type="button" 
            className={`lang-option-btn ${currentLanguage === 'en' ? 'active' : ''}`}
            onClick={() => onLanguageChange && onLanguageChange('en')}
          >
            English
          </button>
          <span className="lang-sep">|</span>
          <button 
            type="button" 
            className={`lang-option-btn ${currentLanguage === 'ta' ? 'active' : ''}`}
            onClick={() => onLanguageChange && onLanguageChange('ta')}
          >
            தமிழ்
          </button>
        </div>

        <div className="header-divider" aria-hidden="true"></div>

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

      </div>

    </header>
  );
}
