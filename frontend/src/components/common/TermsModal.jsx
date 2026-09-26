import React from 'react';
import { Scale, CheckCircle2, AlertTriangle, X } from 'lucide-react';

export default function TermsModal({ isOpen, onClose }) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in" style={{ zIndex: 9999 }}>
      <div className="relative w-full max-w-2xl bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-emerald-100 dark:bg-emerald-900/40 text-emerald-600 dark:text-emerald-400 flex items-center justify-center">
              <Scale className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-900 dark:text-white">Terms of Official Operation</h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">Grievance Document Pre-Processor (GDP)</p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-2 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
            aria-label="Close Terms of Service"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="px-6 py-5 overflow-y-auto space-y-4 text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
          <section>
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white flex items-center gap-2 mb-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-500" /> 1. Authorized Officer Usage
            </h3>
            <p>
              Access to this system is restricted to designated Revenue Officers, Desk Attendants, and District Administrators. Officers must use their assigned government credentials and maintain secrecy of their passwords.
            </p>
          </section>

          <section>
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white flex items-center gap-2 mb-1.5">
              <AlertTriangle className="w-4 h-4 text-amber-500" /> 2. AI Pre-Processing & Verification
            </h3>
            <p>
              AI extraction and OCR bounding boxes serve as an intelligent intake assistant. The reviewing officer remains solely responsible for verifying extracted petitioner names, phone numbers, survey numbers, and jurisdiction allocations before final DRO master dispatch.
            </p>
          </section>

          <section>
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white flex items-center gap-2 mb-1.5">
              <Scale className="w-4 h-4 text-blue-500" /> 3. Data Integrity & Prohibited Actions
            </h3>
            <p>
              Tampering with OCR extracted records, unauthorized export of citizen records, or attempting to bypass audit logging is strictly prohibited and subject to administrative disciplinary proceedings.
            </p>
          </section>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40">
          <span className="text-xs text-slate-400">Department of Revenue Administration</span>
          <button
            onClick={onClose}
            className="px-5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium transition shadow-sm"
          >
            Accept & Continue
          </button>
        </div>
      </div>
    </div>
  );
}
