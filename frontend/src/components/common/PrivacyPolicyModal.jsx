import React from 'react';
import { Shield, Lock, FileText, Check, X } from 'lucide-react';

export default function PrivacyPolicyModal({ isOpen, onClose }) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in" style={{ zIndex: 9999 }}>
      <div className="relative w-full max-w-2xl bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400 flex items-center justify-center">
              <Shield className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-900 dark:text-white">Privacy & Data Governance Policy</h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">Tamil Nadu District Grievance Redressal Administration</p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-2 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
            aria-label="Close Privacy Policy"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="px-6 py-5 overflow-y-auto space-y-4 text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
          <div className="p-3.5 bg-blue-50/80 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-900 rounded-xl text-blue-900 dark:text-blue-200 text-xs">
            <strong>Official Notice:</strong> This system is strictly intended for official government grievance pre-processing. All citizen data is protected under the Digital Personal Data Protection (DPDP) Act, 2023.
          </div>

          <section>
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white flex items-center gap-2 mb-1.5">
              <Lock className="w-4 h-4 text-emerald-500" /> 1. Information We Collect
            </h3>
            <p>
              When a grievance petition is uploaded, the OCR pipeline extracts necessary citizen details including petitioner name, contact number, Aadhaar reference (masked), village/taluk jurisdiction, and grievance grievance classification solely to route the petition to the competent desk.
            </p>
          </section>

          <section>
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white flex items-center gap-2 mb-1.5">
              <FileText className="w-4 h-4 text-blue-500" /> 2. Data Processing & Security
            </h3>
            <p>
              All petition OCR processing and NLP vectorization occur on government-hosted nodes with AES-256 encryption at rest and TLS 1.3 in transit. Biometric and sensitive citizen identifiers are never shared with unauthorized third parties.
            </p>
          </section>

          <section>
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white flex items-center gap-2 mb-1.5">
              <Shield className="w-4 h-4 text-purple-500" /> 3. Audit Logging & Retention
            </h3>
            <p>
              All officer actions (ingestion, verification, modification, export) are immutably logged with timestamp, officer badge, and client IP in the DRO Audit Ledger for accountability.
            </p>
          </section>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40">
          <span className="text-xs text-slate-400">Version 2.4 • Effective September 2026</span>
          <button
            onClick={onClose}
            className="px-5 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium transition shadow-sm"
          >
            I Understand
          </button>
        </div>
      </div>
    </div>
  );
}
