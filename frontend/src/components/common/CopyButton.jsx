import React, { useState } from 'react';
import { Copy, Check } from 'lucide-react';

export default function CopyButton({ textToCopy, label = 'Copy', onCopied, className = '' }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async (e) => {
    e.stopPropagation();
    if (!textToCopy) return;

    try {
      await navigator.clipboard.writeText(textToCopy);
      setCopied(true);
      if (onCopied) {
        onCopied(textToCopy);
      }
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy: ', err);
    }
  };

  return (
    <button
      type="button"
      onClick={handleCopy}
      title={copied ? 'Copied to clipboard!' : `Copy ${label}`}
      className={`copy-btn ${copied ? 'copied' : ''} ${className}`}
      aria-label={`Copy ${label}`}
    >
      {copied ? (
        <>
          <Check size={13} className="copy-icon check-icon" />
          <span className="copy-btn-text">Copied</span>
        </>
      ) : (
        <>
          <Copy size={13} className="copy-icon" />
          <span className="copy-btn-text">{label}</span>
        </>
      )}
    </button>
  );
}
