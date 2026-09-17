import React, { useState, useEffect } from 'react';
import { 
  Settings, 
  Shield, 
  Database, 
  Cpu, 
  Check, 
  RotateCcw, 
  UserCheck, 
  Sliders, 
  FileText, 
  Languages, 
  Download, 
  Trash2, 
  Sparkles,
  Lock,
  Layers
} from 'lucide-react';
import './SettingsView.css';

const DEFAULT_SETTINGS = {
  // 1. Officer Profile & Interface
  officerName: 'S. Ramanathan',
  officerRole: 'Tahsildar • Grievance Cell',
  workingLanguage: 'bilingual',
  fontSizeScale: '16px',

  // 2. OCR & Document Engine
  ocrEngine: 'tesseract_vision',
  scriptMode: 'auto',
  autoDeskew: true,
  enhanceLowLight: true,
  confidenceThreshold: 92,

  // 3. Grievance & AI Analysis
  targetPortal: 'tn_edistrict',
  summaryDepth: 'bulleted',
  bilingualSummary: true,
  highlightPriority: true,
  autoExtractAddresses: true,

  // 4. Security & Privacy
  retentionMode: 'memory_only',
  auditLoggingLevel: 'all',
  autoClearSession: true
};

const STORAGE_KEY = 'tn_gdp_administrative_settings';

export default function SettingsView({ onNotify }) {
  // Persistent Settings State
  const [settings, setSettings] = useState(() => {
    if (typeof window !== 'undefined') {
      try {
        const saved = localStorage.getItem(STORAGE_KEY);
        if (saved) return { ...DEFAULT_SETTINGS, ...JSON.parse(saved) };
      } catch (err) {
        console.warn('Failed to parse saved settings:', err);
      }
    }
    return DEFAULT_SETTINGS;
  });

  // Active Category Filter: 'all' | 'ocr' | 'ai' | 'officer' | 'security'
  const [activeTab, setActiveTab] = useState('all');
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  const updateSetting = (key, value) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
    setHasUnsavedChanges(true);
  };

  const handleSave = () => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
      setHasUnsavedChanges(false);
      if (onNotify) onNotify('Administrative parameters saved successfully');
    } catch (err) {
      console.error('Failed to save settings:', err);
      if (onNotify) onNotify('Error saving settings to storage');
    }
  };

  const handleResetDefaults = () => {
    setSettings(DEFAULT_SETTINGS);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(DEFAULT_SETTINGS));
      setHasUnsavedChanges(false);
      if (onNotify) onNotify('Settings restored to official defaults');
    } catch (err) {
      console.error('Failed to reset defaults:', err);
    }
  };

  const handleExportConfig = () => {
    try {
      const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(settings, null, 2));
      const downloadAnchor = document.createElement('a');
      downloadAnchor.setAttribute("href", dataStr);
      downloadAnchor.setAttribute("download", `gdp_assistant_config_${new Date().toISOString().slice(0,10)}.json`);
      document.body.appendChild(downloadAnchor);
      downloadAnchor.click();
      downloadAnchor.remove();
      if (onNotify) onNotify('Configuration exported as JSON');
    } catch (err) {
      console.error('Failed to export configuration:', err);
    }
  };

  const handleClearCache = () => {
    if (onNotify) onNotify('Local in-memory session cache purged');
  };

  const showSection = (category) => activeTab === 'all' || activeTab === category;

  return (
    <div className="settings-page" role="region" aria-label="Administrative Settings">
      <div className="settings-container">
        
        {/* 1. Page Header */}
        <header className="settings-header">
          <div className="settings-header-left">
            <div className="settings-title-row">
              <Settings size={22} className="settings-header-icon" />
              <h2 className="settings-title">Administrative Settings</h2>
            </div>
            <p className="settings-subtitle">
              Configure OCR engine, grievance portal schemas, officer credentials, and security parameters.
            </p>
          </div>

          <div className="settings-header-actions">
            <button 
              type="button" 
              className="settings-reset-btn"
              onClick={handleResetDefaults}
              title="Reset all settings to government defaults"
            >
              <RotateCcw size={15} />
              <span>Reset Defaults</span>
            </button>

            <button 
              type="button" 
              className="settings-save-btn"
              onClick={handleSave}
            >
              <Check size={16} />
              <span>{hasUnsavedChanges ? 'Save Changes' : 'Save Settings'}</span>
            </button>
          </div>
        </header>

        {/* 2. Category Tab Navigation */}
        <nav className="settings-nav-tabs" aria-label="Settings Categories">
          <button 
            type="button"
            className={`settings-tab-btn ${activeTab === 'all' ? 'active' : ''}`}
            onClick={() => setActiveTab('all')}
          >
            <Layers size={16} className="tab-icon" />
            <span>All Settings</span>
          </button>
          <button 
            type="button"
            className={`settings-tab-btn ${activeTab === 'ocr' ? 'active' : ''}`}
            onClick={() => setActiveTab('ocr')}
          >
            <Cpu size={16} className="tab-icon" />
            <span>OCR & Document Engine</span>
          </button>
          <button 
            type="button"
            className={`settings-tab-btn ${activeTab === 'ai' ? 'active' : ''}`}
            onClick={() => setActiveTab('ai')}
          >
            <Database size={16} className="tab-icon" />
            <span>Grievance & Portal AI</span>
          </button>
          <button 
            type="button"
            className={`settings-tab-btn ${activeTab === 'officer' ? 'active' : ''}`}
            onClick={() => setActiveTab('officer')}
          >
            <UserCheck size={16} className="tab-icon" />
            <span>Officer Profile</span>
          </button>
          <button 
            type="button"
            className={`settings-tab-btn ${activeTab === 'security' ? 'active' : ''}`}
            onClick={() => setActiveTab('security')}
          >
            <Shield size={16} className="tab-icon" />
            <span>Security & Privacy</span>
          </button>
        </nav>

        {/* 3. Settings Cards */}

        {/* SECTION A: OCR & DOCUMENT ENGINE */}
        {showSection('ocr') && (
          <section className="settings-section-card" aria-label="OCR & Document Engine">
            <div className="settings-section-header">
              <div className="settings-section-icon-box">
                <Cpu size={20} />
              </div>
              <div className="settings-section-title-wrap">
                <h3 className="settings-section-title">OCR & Document Recognition Engine</h3>
                <p className="settings-section-desc">Tune text recognition for scanned Tamil & English citizen petitions.</p>
              </div>
            </div>

            <div className="settings-items-list">
              
              {/* Item 1: Engine Pipeline */}
              <div className="settings-item-row">
                <div className="settings-item-info">
                  <div className="settings-item-title">
                    <span>Optical Character Recognition Pipeline</span>
                    <span className="settings-item-badge">Primary</span>
                  </div>
                  <p className="settings-item-help">
                    Select the dual-engine pipeline used for extracting handwritten and typed Tamil petitions.
                  </p>
                </div>
                <div className="settings-item-control">
                  <select 
                    className="settings-select"
                    value={settings.ocrEngine}
                    onChange={(e) => updateSetting('ocrEngine', e.target.value)}
                  >
                    <option value="tesseract_vision">Google Vision + Tesseract (Deep Bilingual)</option>
                    <option value="tesseract_fast">Tesseract Fast OCR Engine</option>
                    <option value="local_lightweight">Local In-Memory Lightweight Engine</option>
                  </select>
                </div>
              </div>

              {/* Item 2: Script Recognition Mode */}
              <div className="settings-item-row">
                <div className="settings-item-info">
                  <div className="settings-item-title">
                    <span>Language & Script Mode</span>
                  </div>
                  <p className="settings-item-help">
                    Configure language models loaded for script deciphering and bilingual token recognition.
                  </p>
                </div>
                <div className="settings-item-control">
                  <select 
                    className="settings-select"
                    value={settings.scriptMode}
                    onChange={(e) => updateSetting('scriptMode', e.target.value)}
                  >
                    <option value="auto">Auto-detect (Tamil + English)</option>
                    <option value="tamil_only">Force Tamil Unicode (தமிழ்)</option>
                    <option value="english_only">Force English Standard</option>
                  </select>
                </div>
              </div>

              {/* Item 3: Minimum Confidence Threshold Slider */}
              <div className="settings-item-row">
                <div className="settings-item-info">
                  <div className="settings-item-title">
                    <span>Confidence Highlighting Threshold</span>
                  </div>
                  <p className="settings-item-help">
                    Fields extracted with confidence below this threshold will display yellow verification chips for officer review.
                  </p>
                </div>
                <div className="settings-item-control">
                  <div className="settings-range-wrap">
                    <input 
                      type="range"
                      min="75"
                      max="98"
                      step="1"
                      className="settings-range-input"
                      value={settings.confidenceThreshold}
                      onChange={(e) => updateSetting('confidenceThreshold', parseInt(e.target.value, 10))}
                    />
                    <span className="settings-range-badge">{settings.confidenceThreshold}%</span>
                  </div>
                </div>
              </div>

              {/* Item 4: Auto-Deskew Switch */}
              <div className="settings-item-row">
                <div className="settings-item-info">
                  <div className="settings-item-title">
                    <span>Automatic Document Deskew & Rotation</span>
                  </div>
                  <p className="settings-item-help">
                    Automatically straightens tilted smartphone photos and corrects orientation before OCR.
                  </p>
                </div>
                <div className="settings-item-control">
                  <label className="settings-switch">
                    <input 
                      type="checkbox"
                      checked={settings.autoDeskew}
                      onChange={(e) => updateSetting('autoDeskew', e.target.checked)}
                    />
                    <span className="settings-slider"></span>
                  </label>
                </div>
              </div>

              {/* Item 5: Low-Light Enhancement Switch */}
              <div className="settings-item-row">
                <div className="settings-item-info">
                  <div className="settings-item-title">
                    <span>Adaptive Contrast & Low-Light Enhancement</span>
                  </div>
                  <p className="settings-item-help">
                    Enhances faint pen ink and shadows captured under indoor fluorescent and natural lighting.
                  </p>
                </div>
                <div className="settings-item-control">
                  <label className="settings-switch">
                    <input 
                      type="checkbox"
                      checked={settings.enhanceLowLight}
                      onChange={(e) => updateSetting('enhanceLowLight', e.target.checked)}
                    />
                    <span className="settings-slider"></span>
                  </label>
                </div>
              </div>

            </div>
          </section>
        )}

        {/* SECTION B: GRIEVANCE PORTAL & AI ANALYSIS */}
        {showSection('ai') && (
          <section className="settings-section-card" aria-label="Grievance Portal & AI Analysis">
            <div className="settings-section-header">
              <div className="settings-section-icon-box">
                <Database size={20} />
              </div>
              <div className="settings-section-title-wrap">
                <h3 className="settings-section-title">Grievance Portal & AI Analysis</h3>
                <p className="settings-section-desc">Align summaries and structured extraction to Monday Grievance Day administrative formats.</p>
              </div>
            </div>

            <div className="settings-items-list">
              
              {/* Item 1: Target Portal Schema */}
              <div className="settings-item-row">
                <div className="settings-item-info">
                  <div className="settings-item-title">
                    <span>Government Portal Target Schema</span>
                    <span className="settings-item-badge">Active</span>
                  </div>
                  <p className="settings-item-help">
                    Maps extracted metadata directly into official Tamil Nadu online grievance portal entry schemas.
                  </p>
                </div>
                <div className="settings-item-control">
                  <select 
                    className="settings-select"
                    value={settings.targetPortal}
                    onChange={(e) => updateSetting('targetPortal', e.target.value)}
                  >
                    <option value="tn_edistrict">TN e-District / Collectorate Cell</option>
                    <option value="cm_cell">Chief Minister Special Cell (Mudhalvarin Mugavari)</option>
                    <option value="revenue_dept">Revenue & Disaster Management Cell</option>
                    <option value="taluk_office">Taluk / DRO Grievance Desk</option>
                  </select>
                </div>
              </div>

              {/* Item 2: Summarization Format Pill Group */}
              <div className="settings-item-row">
                <div className="settings-item-info">
                  <div className="settings-item-title">
                    <span>Default Petition Summary Format</span>
                  </div>
                  <p className="settings-item-help">
                    Determines structure of initial AI summary generated upon document upload.
                  </p>
                </div>
                <div className="settings-item-control">
                  <div className="settings-pill-group">
                    <button
                      type="button"
                      className={`settings-pill-btn ${settings.summaryDepth === 'bulleted' ? 'active' : ''}`}
                      onClick={() => updateSetting('summaryDepth', 'bulleted')}
                    >
                      5-Point Brief
                    </button>
                    <button
                      type="button"
                      className={`settings-pill-btn ${settings.summaryDepth === 'executive' ? 'active' : ''}`}
                      onClick={() => updateSetting('summaryDepth', 'executive')}
                    >
                      Executive Summary
                    </button>
                    <button
                      type="button"
                      className={`settings-pill-btn ${settings.summaryDepth === 'raw' ? 'active' : ''}`}
                      onClick={() => updateSetting('summaryDepth', 'raw')}
                    >
                      Key-Value Matrix
                    </button>
                  </div>
                </div>
              </div>

              {/* Item 3: Bilingual Summary Switch */}
              <div className="settings-item-row">
                <div className="settings-item-info">
                  <div className="settings-item-title">
                    <span>Dual Language Synthesis (Tamil + English)</span>
                  </div>
                  <p className="settings-item-help">
                    Generates petition summary in both Tamil and English simultaneously for bilingual administrative filing.
                  </p>
                </div>
                <div className="settings-item-control">
                  <label className="settings-switch">
                    <input 
                      type="checkbox"
                      checked={settings.bilingualSummary}
                      onChange={(e) => updateSetting('bilingualSummary', e.target.checked)}
                    />
                    <span className="settings-slider"></span>
                  </label>
                </div>
              </div>

              {/* Item 4: Highlight Critical Grievances Switch */}
              <div className="settings-item-row">
                <div className="settings-item-info">
                  <div className="settings-item-title">
                    <span>Urgent Grievance Priority Flagging</span>
                  </div>
                  <p className="settings-item-help">
                    Automatically tags senior citizen, differently-abled, flood relief, and emergency land petitions with high priority.
                  </p>
                </div>
                <div className="settings-item-control">
                  <label className="settings-switch">
                    <input 
                      type="checkbox"
                      checked={settings.highlightPriority}
                      onChange={(e) => updateSetting('highlightPriority', e.target.checked)}
                    />
                    <span className="settings-slider"></span>
                  </label>
                </div>
              </div>

              {/* Item 5: Auto-extract addresses Switch */}
              <div className="settings-item-row">
                <div className="settings-item-info">
                  <div className="settings-item-title">
                    <span>Revenue Hierarchy Extraction</span>
                  </div>
                  <p className="settings-item-help">
                    Parses District, Taluk, Firka, Village, and Door Number into discrete copyable fields.
                  </p>
                </div>
                <div className="settings-item-control">
                  <label className="settings-switch">
                    <input 
                      type="checkbox"
                      checked={settings.autoExtractAddresses}
                      onChange={(e) => updateSetting('autoExtractAddresses', e.target.checked)}
                    />
                    <span className="settings-slider"></span>
                  </label>
                </div>
              </div>

            </div>
          </section>
        )}

        {/* SECTION C: OFFICER PROFILE & WORKSTATION */}
        {showSection('officer') && (
          <section className="settings-section-card" aria-label="Officer Profile & Workstation">
            <div className="settings-section-header">
              <div className="settings-section-icon-box">
                <UserCheck size={20} />
              </div>
              <div className="settings-section-title-wrap">
                <h3 className="settings-section-title">Officer Profile & Workstation</h3>
                <p className="settings-section-desc">Manage officer identity display, language preferences, and interface ergonomics.</p>
              </div>
            </div>

            <div className="settings-items-list">
              
              {/* Item 1: Officer Name */}
              <div className="settings-item-row">
                <div className="settings-item-info">
                  <div className="settings-item-title">
                    <span>Officer Name</span>
                  </div>
                  <p className="settings-item-help">
                    Displayed in the top navigation header and attached to official audit log entries.
                  </p>
                </div>
                <div className="settings-item-control">
                  <input 
                    type="text"
                    className="settings-text-input"
                    value={settings.officerName}
                    onChange={(e) => updateSetting('officerName', e.target.value)}
                    placeholder="Officer Name"
                  />
                </div>
              </div>

              {/* Item 2: Designation */}
              <div className="settings-item-row">
                <div className="settings-item-info">
                  <div className="settings-item-title">
                    <span>Designation & Department</span>
                  </div>
                  <p className="settings-item-help">
                    Official title and administrative section for audit attribution.
                  </p>
                </div>
                <div className="settings-item-control">
                  <input 
                    type="text"
                    className="settings-text-input"
                    value={settings.officerRole}
                    onChange={(e) => updateSetting('officerRole', e.target.value)}
                    placeholder="Designation • Cell"
                  />
                </div>
              </div>

              {/* Item 3: Default Language Toggle */}
              <div className="settings-item-row">
                <div className="settings-item-info">
                  <div className="settings-item-title">
                    <span>Default Workstation Interface Language</span>
                  </div>
                  <p className="settings-item-help">
                    Sets default UI label language on launch. Can also be toggled anytime from the top bar.
                  </p>
                </div>
                <div className="settings-item-control">
                  <select 
                    className="settings-select"
                    value={settings.workingLanguage}
                    onChange={(e) => updateSetting('workingLanguage', e.target.value)}
                  >
                    <option value="bilingual">Bilingual (English + தமிழ்)</option>
                    <option value="ta">தமிழ் (Tamil Only)</option>
                    <option value="en">English (English Only)</option>
                  </select>
                </div>
              </div>

              {/* Item 4: Interface Font Size Scale */}
              <div className="settings-item-row">
                <div className="settings-item-info">
                  <div className="settings-item-title">
                    <span>Workstation Font Sizing (Legibility Standard)</span>
                  </div>
                  <p className="settings-item-help">
                    Adjusts text scaling across petition summaries, OCR panels, and chat streams.
                  </p>
                </div>
                <div className="settings-item-control">
                  <div className="settings-pill-group">
                    <button
                      type="button"
                      className={`settings-pill-btn ${settings.fontSizeScale === '15px' ? 'active' : ''}`}
                      onClick={() => updateSetting('fontSizeScale', '15px')}
                    >
                      Compact
                    </button>
                    <button
                      type="button"
                      className={`settings-pill-btn ${settings.fontSizeScale === '16px' ? 'active' : ''}`}
                      onClick={() => updateSetting('fontSizeScale', '16px')}
                    >
                      Standard (16px)
                    </button>
                    <button
                      type="button"
                      className={`settings-pill-btn ${settings.fontSizeScale === '18px' ? 'active' : ''}`}
                      onClick={() => updateSetting('fontSizeScale', '18px')}
                    >
                      Large (18px)
                    </button>
                  </div>
                </div>
              </div>

            </div>
          </section>
        )}

        {/* SECTION D: SECURITY & PRIVACY */}
        {showSection('security') && (
          <section className="settings-section-card" aria-label="Security & Privacy">
            <div className="settings-section-header">
              <div className="settings-section-icon-box">
                <Shield size={20} />
              </div>
              <div className="settings-section-title-wrap">
                <h3 className="settings-section-title">Data Privacy, Memory & Security</h3>
                <p className="settings-section-desc">Manage document retention, in-memory isolation, and session audits.</p>
              </div>
            </div>

            <div className="settings-items-list">
              
              {/* Item 1: Retention Mode */}
              <div className="settings-item-row">
                <div className="settings-item-info">
                  <div className="settings-item-title">
                    <span>Document Retention Policy</span>
                    <span className="settings-item-badge">Isolated</span>
                  </div>
                  <p className="settings-item-help">
                    All scanned citizen documents are maintained strictly in local RAM and discarded upon session completion.
                  </p>
                </div>
                <div className="settings-item-control">
                  <select 
                    className="settings-select"
                    value={settings.retentionMode}
                    onChange={(e) => updateSetting('retentionMode', e.target.value)}
                  >
                    <option value="memory_only">Ephemeral In-Memory Only (Recommended)</option>
                    <option value="session_encrypted">Encrypted Session Cache</option>
                  </select>
                </div>
              </div>

              {/* Item 2: Audit Logging Level */}
              <div className="settings-item-row">
                <div className="settings-item-info">
                  <div className="settings-item-title">
                    <span>Audit Trail Recording Level</span>
                  </div>
                  <p className="settings-item-help">
                    Controls granularity of actions recorded in the local administrative audit history.
                  </p>
                </div>
                <div className="settings-item-control">
                  <select 
                    className="settings-select"
                    value={settings.auditLoggingLevel}
                    onChange={(e) => updateSetting('auditLoggingLevel', e.target.value)}
                  >
                    <option value="all">Full Audit Trail (Queries & Uploads)</option>
                    <option value="uploads_only">Document Upload Events Only</option>
                    <option value="minimal">Minimal Timestamps Only</option>
                  </select>
                </div>
              </div>

              {/* Item 3: Auto-clear on petition switch */}
              <div className="settings-item-row">
                <div className="settings-item-info">
                  <div className="settings-item-title">
                    <span>Auto-Purge Document Memory on "New Petition"</span>
                  </div>
                  <p className="settings-item-help">
                    Frees browser blob memory and cleans memory handles immediately when clicking "New Petition".
                  </p>
                </div>
                <div className="settings-item-control">
                  <label className="settings-switch">
                    <input 
                      type="checkbox"
                      checked={settings.autoClearSession}
                      onChange={(e) => updateSetting('autoClearSession', e.target.checked)}
                    />
                    <span className="settings-slider"></span>
                  </label>
                </div>
              </div>

              {/* Item 4: Maintenance Actions (Export & Clear) */}
              <div className="settings-item-row">
                <div className="settings-item-info">
                  <div className="settings-item-title">
                    <span>Maintenance & Backup Operations</span>
                  </div>
                  <p className="settings-item-help">
                    Export configuration parameters as JSON or manually clear local temporary cache.
                  </p>
                </div>
                <div className="settings-item-control" style={{ gap: '10px' }}>
                  <button
                    type="button"
                    className="settings-action-btn-secondary"
                    onClick={handleExportConfig}
                    title="Export system configuration to JSON"
                  >
                    <Download size={15} />
                    <span>Export Config</span>
                  </button>

                  <button
                    type="button"
                    className="settings-action-btn-danger"
                    onClick={handleClearCache}
                    title="Purge in-memory document blobs immediately"
                  >
                    <Trash2 size={15} />
                    <span>Clear Cache</span>
                  </button>
                </div>
              </div>

            </div>
          </section>
        )}

      </div>
    </div>
  );
}
