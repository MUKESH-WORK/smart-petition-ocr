import React from 'react';

export default function StatusBadge({ state, confidence, showConfidence = false }) {
  if (state === 'extracted') {
    return (
      <span className="status-badge badge-extracted" title="Directly extracted from document text">
        <span className="badge-icon">✓</span>
        <span className="badge-label">Extracted</span>
        {showConfidence && confidence && (
          <span className="badge-confidence">• {confidence}%</span>
        )}
      </span>
    );
  }

  if (state === 'suggested') {
    return (
      <span className="status-badge badge-suggested" title="Inferred or classified by AI based on context">
        <span className="badge-icon">◇</span>
        <span className="badge-label">AI Suggested</span>
        {showConfidence && confidence && (
          <span className="badge-confidence">• {confidence}%</span>
        )}
      </span>
    );
  }

  // Not found / Not available
  return (
    <span className="status-badge badge-notfound" title="Not available in scanned document">
      <span className="badge-icon">—</span>
      <span className="badge-label">Not Found</span>
    </span>
  );
}
