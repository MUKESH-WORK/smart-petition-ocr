import React, { useState, useRef, useEffect } from 'react';
import { UserCheck, ChevronDown, User, LogOut, Languages } from 'lucide-react';
import { getTranslation } from '../../utils/translations';
import './Header.css';

export default function Header({
  notifications,
  loginRole,
  officerProfile,
  onLogoClick,
  currentLanguage = 'en',
  onLanguageChange,
  onNavigateToProfile,
  onLogout
}) {
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const profileRef = useRef(null);

  const displayName = officerProfile?.fullName || officerProfile?.name || '';
  const displayRole = officerProfile?.designation || (loginRole === 'admin' ? 'District Administrator' : 'Department Officer');

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (profileRef.current && !profileRef.current.contains(event.target)) {
        setIsDropdownOpen(false);
      }
    };

    if (isDropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isDropdownOpen]);

  const toggleDropdown = () => {
    setIsDropdownOpen((prev) => !prev);
  };

  const handleProfileClick = () => {
    setIsDropdownOpen(false);
    if (onNavigateToProfile) {
      onNavigateToProfile();
    }
  };

  const handleLogoutClick = () => {
    setIsDropdownOpen(false);
    if (onLogout) {
      onLogout();
    }
  };

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
            <h1 className="brand-title">{getTranslation(currentLanguage, 'appTitle', 'AI Administrative Co-Pilot')}</h1>
          </div>
          <span className="brand-subtitle">{getTranslation(currentLanguage, 'appSubtitle', 'Government Grievance Pre-Processing')}</span>
        </div>
      </div>

      {/* Right: Language Switcher & Officer Profile */}
      <div className="header-right">
        {loginRole === 'admin' && notifications}

        {/* Language Translation Icon Toggle */}
        <button
          type="button"
          className="header-lang-icon-btn notranslate"
          translate="no"
          onClick={() => onLanguageChange && onLanguageChange(currentLanguage === 'en' ? 'ta' : 'en')}
          title={currentLanguage === 'en' ? 'Translate Interface to தமிழ் (Tamil)' : 'Translate Interface to English'}
          aria-label="Toggle language translation"
        >
          <Languages size={17} className="lang-icon" />
          <span className="lang-active-tag">{currentLanguage === 'en' ? 'English' : 'தமிழ்'}</span>
        </button>

        <div className="header-divider" aria-hidden="true"></div>

        {/* Officer Profile Badge & Dropdown */}
        <div className="officer-profile-wrapper" ref={profileRef}>
          <button
            type="button"
            className={`officer-profile-card clickable ${isDropdownOpen ? 'open' : ''}`}
            onClick={toggleDropdown}
            aria-expanded={isDropdownOpen}
            aria-haspopup="true"
            title="Officer Profile Menu"
          >
            <div className="officer-avatar" aria-hidden="true">
              <UserCheck size={16} />
            </div>
            <div className="officer-info">
              <span className="officer-name">{currentLanguage === 'ta' && (officerProfile?.nameTamil || officerProfile?.name_tamil) ? (officerProfile.nameTamil || officerProfile.name_tamil) : (displayName || officerProfile?.officerId || 'Officer')}</span>
              <span className="officer-role">{loginRole === 'admin' ? getTranslation(currentLanguage, 'admin', 'District Administrator') : getTranslation(currentLanguage, 'user', displayRole || 'Department Officer')}</span>
            </div>
            <ChevronDown
              size={14}
              className={`officer-chevron ${isDropdownOpen ? 'chevron-rotated' : ''}`}
            />
          </button>

          {/* Dropdown Menu (Profile View & Sign Out) */}
          {isDropdownOpen && (
            <div className="profile-dropdown-menu" role="menu" aria-label="Officer Profile Options">
              <button
                type="button"
                className="profile-dropdown-item"
                role="menuitem"
                onClick={handleProfileClick}
              >
                <User size={15} className="dropdown-item-icon" />
                <span>{getTranslation(currentLanguage, 'profileView', 'Profile View')}</span>
              </button>

              <button
                type="button"
                className="profile-dropdown-item logout-item"
                role="menuitem"
                onClick={handleLogoutClick}
              >
                <LogOut size={15} className="dropdown-item-icon" />
                <span>{getTranslation(currentLanguage, 'signOut', 'Sign Out')}</span>
              </button>
            </div>
          )}
        </div>

      </div>

    </header>
  );
}

