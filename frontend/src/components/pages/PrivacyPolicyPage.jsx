import React from 'react';
import { Shield, Lock, FileText, ArrowLeft } from 'lucide-react';
import './PolicyPages.css';

export default function PrivacyPolicyPage({ onBack }) {
  return (
    <div className="policy-page-container">
      <header className="policy-page-header">
        <div className="policy-header-inner">
          <div className="policy-brand">
            <img src="/tn-emblem.png" alt="Tamil Nadu State Emblem" className="policy-emblem" />
            <div>
              <h1>Government of Tamil Nadu</h1>
              <p>District Revenue Administration • Public Grievance Pre-Processing Portal</p>
            </div>
          </div>
          <button 
            type="button" 
            onClick={onBack || (() => window.history.back())}
            className="policy-back-btn"
          >
            <ArrowLeft size={16} />
            <span>Return to Sign in</span>
          </button>
        </div>
      </header>

      <main className="policy-page-content">
        <article className="policy-card">
          <div className="policy-title-badge">
            <Shield size={20} className="text-blue-600" />
            <span>DPDP Act, 2023 Compliant</span>
          </div>

          <h2>Privacy &amp; Data Governance Policy</h2>
          <p className="policy-meta">Effective Date: September 2026 • Document Version: 2.4-GA</p>

          <div className="policy-notice-box">
            <strong>Official Notice:</strong> This system is strictly intended for official government grievance pre-processing. All citizen data is protected under the Digital Personal Data Protection (DPDP) Act, 2023, and official confidentiality frameworks.
          </div>

          <section className="policy-section">
            <h3><Lock size={18} /> 1. Information We Collect</h3>
            <p>
              When a citizen grievance petition is uploaded, the OCR and automated extraction pipeline parses only necessary fields:
            </p>
            <ul>
              <li>Petitioner Name and Father's/Spouse's Name</li>
              <li>Contact Number and Alternate Contact Details</li>
              <li>Village, Taluk, Firka, and Revenue Division Jurisdiction</li>
              <li>Grievance narrative classification according to State Taxonomy</li>
              <li>Masked identity reference identifiers for verification</li>
            </ul>
          </section>

          <section className="policy-section">
            <h3><FileText size={18} /> 2. Data Processing, Storage &amp; Encryption</h3>
            <p>
              All petition OCR operations and vector embeddings execute exclusively on secured government-operated nodes. Data at rest is encrypted using AES-256 and data in transit is protected with TLS 1.3 encryption. Biometric and sensitive citizen identifiers are never shared with unauthorized third parties.
            </p>
          </section>

          <section className="policy-section">
            <h3><Shield size={18} /> 3. Immutable Audit Logging</h3>
            <p>
              Every officer action—including document ingestion, field modifications, draft approval, and DRO dispatch—is immutably logged with timestamp, officer identity, and client IP in the DRO Audit Ledger.
            </p>
          </section>
        </article>
      </main>

      <footer className="policy-page-footer">
        <p>Erode Collectorate • Revenue &amp; Disaster Management Department, Government of Tamil Nadu</p>
      </footer>
    </div>
  );
}
