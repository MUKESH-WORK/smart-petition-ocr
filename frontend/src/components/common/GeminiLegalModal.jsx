import React, { useState } from 'react';
import { Shield, Lock, FileText, Scale, CheckCircle2, AlertTriangle, X, ExternalLink } from 'lucide-react';
import './GeminiLegalModal.css';

export default function GeminiLegalModal({ isOpen, onClose, initialTab = 'privacy' }) {
  const [activeTab, setActiveTab] = useState(initialTab);

  if (!isOpen) return null;

  return (
    <div className="gemini-legal-backdrop" onClick={onClose} role="dialog" aria-modal="true">
      <div className="gemini-legal-container" onClick={(e) => e.stopPropagation()}>
        {/* Top bar with Google-like tab switch and close button */}
        <div className="gemini-legal-header">
          <div className="gemini-legal-nav">
            <button
              type="button"
              className={`gemini-tab-btn ${activeTab === 'privacy' ? 'active' : ''}`}
              onClick={() => setActiveTab('privacy')}
            >
              <Shield size={16} />
              <span>Privacy Policy</span>
            </button>
            <button
              type="button"
              className={`gemini-tab-btn ${activeTab === 'terms' ? 'active' : ''}`}
              onClick={() => setActiveTab('terms')}
            >
              <Scale size={16} />
              <span>Terms of Service</span>
            </button>
          </div>

          <button
            type="button"
            className="gemini-close-btn"
            onClick={onClose}
            aria-label="Close dialog"
          >
            <X size={18} />
          </button>
        </div>

        {/* Modal Scrollable Body */}
        <div className="gemini-legal-body">
          {activeTab === 'privacy' ? (
            <div className="gemini-content-pane">
              <div className="gemini-pill-tag">
                <Lock size={13} />
                <span>Digital Personal Data Protection (DPDP) Act, 2023 Compliant</span>
              </div>

              <h2 className="gemini-main-title">Privacy &amp; Data Governance Policy</h2>
              <p className="gemini-subtitle">
                District Revenue Administration • Government of Tamil Nadu
              </p>

              <div className="gemini-highlight-card">
                <div className="gemini-highlight-icon">
                  <Shield size={20} />
                </div>
                <div className="gemini-highlight-text">
                  <h4>Official Government Data Protection Standard</h4>
                  <p>
                    All citizen petition documents, OCR text extractions, and biometric identifiers are processed exclusively on secured government servers with AES-256 at rest and TLS 1.3 encryption in transit.
                  </p>
                </div>
              </div>

              <div className="gemini-section">
                <h3>1. Information We Collect</h3>
                <p>
                  When a grievance petition is uploaded, the automated extraction engine processes only the required administrative data fields:
                </p>
                <ul className="gemini-list">
                  <li><strong>Petitioner Identity:</strong> Full Name, Father's / Spouse's Name, Complainant Signatory.</li>
                  <li><strong>Communication Details:</strong> Phone Number, Alternate Contact, Postal Address.</li>
                  <li><strong>Jurisdiction:</strong> Revenue Village, Taluk, Firka, Corporation Ward, and Revenue Division.</li>
                  <li><strong>Grievance Classification:</strong> Category taxonomy tags and structured grievance narrative.</li>
                </ul>
              </div>

              <div className="gemini-section">
                <h3>2. How Your Data Is Processed</h3>
                <p>
                  Data extracted by the OCR pipeline is utilized solely to assist Revenue Officers in indexing, verifying, and routing petitions to the competent departmental desks. Citizen information is never sold, shared, or indexed by external advertising networks.
                </p>
              </div>

              <div className="gemini-section">
                <h3>3. Immutable Audit Logging</h3>
                <p>
                  To ensure transparency and accountability, every officer action—including document ingestion, field modifications, draft approvals, and DRO dispatches—is cryptographically recorded in the DRO Audit Ledger with timestamp and officer badge metadata.
                </p>
              </div>
            </div>
          ) : (
            <div className="gemini-content-pane">
              <div className="gemini-pill-tag green">
                <Scale size={13} />
                <span>Authorized Official Use Only</span>
              </div>

              <h2 className="gemini-main-title">Terms of Official Operation</h2>
              <p className="gemini-subtitle">
                Grievance Document Pre-Processor (GDP Assistant) • Revenue Department
              </p>

              <div className="gemini-highlight-card green">
                <div className="gemini-highlight-icon">
                  <CheckCircle2 size={20} />
                </div>
                <div className="gemini-highlight-text">
                  <h4>Statutory Officer Verification Responsibilities</h4>
                  <p>
                    The AI-assisted extraction and bounding box suggestions are intelligent decision-support aids. The reviewing Revenue Officer remains solely responsible for verifying all extracted fields before master submission.
                  </p>
                </div>
              </div>

              <div className="gemini-section">
                <h3>1. Authorized Officer Access</h3>
                <p>
                  Access is strictly restricted to designated District Revenue Officers, Revenue Inspectors, and Taluk Clerks possessing active government credentials. Account sharing or unauthorized delegation is strictly prohibited.
                </p>
              </div>

              <div className="gemini-section">
                <h3>2. Integrity of Extracted Records</h3>
                <p>
                  Officers must ensure accuracy when reviewing and approving petition drafts. Any intentional falsification or improper redaction of grievance details is subject to disciplinary action under the Tamil Nadu Government Servants Conduct Rules.
                </p>
              </div>

              <div className="gemini-section">
                <h3>3. System Availability &amp; Audit Compliance</h3>
                <p>
                  All session actions, uploads, and data mutations are subject to real-time administrative oversight and periodic state compliance audits.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="gemini-legal-footer">
          <div className="gemini-footer-links">
            <span className="gemini-version-tag">Version 2.4-GA • Erode Collectorate</span>
          </div>
          <button
            type="button"
            className="gemini-action-btn"
            onClick={onClose}
          >
            I Understand
          </button>
        </div>
      </div>
    </div>
  );
}
