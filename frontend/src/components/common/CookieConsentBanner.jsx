import React, { useState, useEffect } from 'react';
import { ShieldCheck, Cookie, X } from 'lucide-react';

export default function CookieConsentBanner({ onOpenPrivacy }) {
  const [show, setShow] = useState(false);

  useEffect(() => {
    const consent = localStorage.getItem('gdp_cookie_consent');
    if (!consent) {
      const timer = setTimeout(() => setShow(true), 1200);
      return () => clearTimeout(timer);
    }
  }, []);

  const handleAccept = () => {
    localStorage.setItem('gdp_cookie_consent', 'accepted');
    setShow(false);
  };

  const handleDecline = () => {
    localStorage.setItem('gdp_cookie_consent', 'necessary_only');
    setShow(false);
  };

  if (!show) return null;

  return (
    <aside 
      aria-label="Security and Local Storage Notice"
      className="fixed bottom-4 left-4 right-4 md:left-auto md:right-6 md:max-w-md z-50 bg-white/95 dark:bg-slate-900/95 backdrop-blur-md rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-800 p-4 transition-all duration-300 animate-slide-up"
      style={{ zIndex: 9998 }}
    >
      <div className="flex items-start gap-3">
        <div className="w-9 h-9 rounded-xl bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0 mt-0.5">
          <ShieldCheck className="w-5 h-5" />
        </div>
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-semibold text-slate-900 dark:text-white flex items-center gap-1.5">
            Security & Session Storage
          </h4>
          <p className="text-xs text-slate-600 dark:text-slate-300 mt-1 leading-relaxed">
            This government portal uses secure session tokens and local storage for officer authentication, theme preferences, and intake queue persistence.
          </p>
          <div className="mt-3 flex items-center gap-2">
            <button
              onClick={handleAccept}
              className="px-3.5 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium transition shadow-sm"
            >
              Accept All
            </button>
            <button
              onClick={handleDecline}
              className="px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 text-xs font-medium transition"
            >
              Essential Only
            </button>
            {onOpenPrivacy && (
              <button
                onClick={onOpenPrivacy}
                className="text-xs text-blue-600 dark:text-blue-400 hover:underline ml-auto"
              >
                Privacy Policy
              </button>
            )}
          </div>
        </div>
        <button
          onClick={handleDecline}
          className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1"
          aria-label="Dismiss notice"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </aside>
  );
}
