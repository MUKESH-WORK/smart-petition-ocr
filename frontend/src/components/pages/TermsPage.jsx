import React from 'react';
import { Scale, CheckCircle2, AlertTriangle, ArrowLeft } from 'lucide-react';
import './PolicyPages.css';

export default function TermsPage({ onBack }) {
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
            <Scale size={20} className="text-emerald-600" />
            <span>Official Government Operations</span>
          </div>

          <h2>Terms of Official Operation</h2>
          <p className="policy-meta">Effective Date: September 2026 • Document Version: 2.4-GA</p>

          <section className="policy-section">
            <h3><CheckCircle2 size={18} /> 1. Authorized Officer Access</h3>
            <p>
              Access to this system is strictly limited to authorized District Revenue Officers, Revenue Inspectors, Taluk Clerks, and District Administrators. Officers must maintain the confidentiality of their credentials and operate strictly within designated administrative boundaries.
            </p>
          </section>

          <section className="policy-section">
            <h3><AlertTriangle size={18} /> 2. AI Pre-Processing &amp; Officer Responsibility</h3>
            <p>
              The automated extraction and OCR bounding box annotations provided by the system are designed as intelligent decision-support aids. The reviewing officer retains statutory responsibility for verifying citizen details, jurisdiction mapping, and taxonomy tags before final dispatch into the Master DRO grievance system.
            </p>
          </section>

          <section className="policy-section">
            <h3><Scale size={18} /> 3. Code of Conduct &amp; Prohibited Actions</h3>
            <p>
              Unauthorized extraction, manipulation of citizen data, or attempting to circumvent audit logging mechanisms is strictly forbidden under the Tamil Nadu Government Servants Conduct Rules and the IT Act, 2000.
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
