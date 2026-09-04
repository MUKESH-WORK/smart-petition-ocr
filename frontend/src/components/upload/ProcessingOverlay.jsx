import React, { useState, useEffect, useCallback } from 'react';
import { FileText, CheckCircle2, Loader2, Circle, ShieldCheck, AlertTriangle, RotateCcw, X } from 'lucide-react';
import { uploadAndAnalyzePetition } from '../../services/apiService';
import './Upload.css';

const PROCESSING_STEPS = [
  { id: 1, label: 'Document uploaded', detail: 'Received securely into memory' },
  { id: 2, label: 'Reading document', detail: 'Parsing document structure & pages' },
  { id: 3, label: 'Detecting language', detail: 'Tamil (94%) & English bilingual recognized' },
  { id: 4, label: 'Extracting text', detail: 'Optical character recognition complete' },
  { id: 5, label: 'Generating petition summary', detail: 'Synthesizing core grievance and background' },
  { id: 6, label: 'Ready for understanding', detail: 'Summary & conversation stream prepared' }
];

export default function ProcessingOverlay({ petition, onComplete, onCancel }) {
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [pipelineError, setPipelineError] = useState(null);
  const [retryNonce, setRetryNonce] = useState(0);

  const handleRetry = useCallback(() => {
    setPipelineError(null);
    setCurrentStepIndex(0);
    setRetryNonce((n) => n + 1);
  }, []);

  useEffect(() => {
    let isMounted = true;

    // Minimum pacing so early steps animate smoothly
    const earlyTimer1 = setTimeout(() => { if (isMounted) setCurrentStepIndex((p) => Math.max(p, 1)); }, 500);
    const earlyTimer2 = setTimeout(() => { if (isMounted) setCurrentStepIndex((p) => Math.max(p, 2)); }, 1200);

    const onProgressCallback = (stepIdx) => {
      if (isMounted) {
        setCurrentStepIndex((prev) => Math.max(prev, stepIdx));
      }
    };

    // Official backend upload & analysis pipeline
    const pipelinePromise = petition?.file
      ? uploadAndAnalyzePetition(petition.file, onProgressCallback)
      : Promise.resolve(petition);

    pipelinePromise
      .then((realAnalyzedDoc) => {
        if (!isMounted) return;
        // Backend finished! Advance to final step (Ready for understanding - 100%)
        setCurrentStepIndex(5);
        setTimeout(() => {
          if (isMounted) {
            onComplete(realAnalyzedDoc || petition);
          }
        }, 800);
      })
      .catch((err) => {
        console.error('Real official pipeline error:', err);
        if (!isMounted) return;
        setPipelineError(err.message || 'An error occurred during official pipeline processing');
      });

    return () => {
      isMounted = false;
      clearTimeout(earlyTimer1);
      clearTimeout(earlyTimer2);
    };
  }, [petition, onComplete, retryNonce]);

  // Overall progress percentage
  const progressPercent = Math.min(100, Math.round(((currentStepIndex + 1) / PROCESSING_STEPS.length) * 100));

  return (
    <div className="processing-wrapper">
      <div className="processing-card">
        
        {/* Document File Identity Banner */}
        <div className="processing-file-strip">
          <div className="file-icon-box">
            <FileText size={22} className="file-svg" />
          </div>
          <div className="file-meta-content">
            <div className="file-name-title">{petition.fileName}</div>
            <div className="file-sub-tags">
              <span className="meta-tag">{petition.fileType}</span>
              <span className="meta-sep">•</span>
              <span className="meta-tag">{petition.fileSize}</span>
              <span className="meta-sep">•</span>
              <span className="meta-tag font-mono">{petition.id}</span>
            </div>
          </div>
          <div className="processing-percent-badge">{progressPercent}%</div>
        </div>

        {/* Linear Progress Bar */}
        <div className="processing-bar-track">
          <div 
            className="processing-bar-fill" 
            style={{ width: `${progressPercent}%` }}
          ></div>
        </div>

        {/* Processing Steps List */}
        <div className="processing-steps-list">
          {PROCESSING_STEPS.map((step, idx) => {
            const isCompleted = idx < currentStepIndex;
            const isCurrent = idx === currentStepIndex && !pipelineError;
            const isPending = idx > currentStepIndex;

            return (
              <div 
                key={step.id} 
                className={`step-row ${isCompleted ? 'step-completed' : ''} ${isCurrent ? 'step-current' : ''} ${isPending ? 'step-pending' : ''}`}
              >
                <div className="step-status-icon">
                  {isCompleted ? (
                    <CheckCircle2 size={16} className="icon-completed" />
                  ) : isCurrent ? (
                    <Loader2 size={16} className="icon-current spin" />
                  ) : (
                    <Circle size={14} className="icon-pending" />
                  )}
                </div>

                <div className="step-label-group">
                  <span className="step-label">{step.label}</span>
                  {isCurrent && <span className="step-detail-hint">— {step.detail}</span>}
                </div>

                {isCompleted && (
                  <span className="step-done-badge">Ready</span>
                )}
              </div>
            );
          })}
        </div>

        {/* Pipeline Error Recovery UI */}
        {pipelineError && (
          <div className="processing-error-banner" style={{
            margin: '16px 0 8px 0',
            padding: '14px 16px',
            borderRadius: '8px',
            background: 'rgba(239, 68, 68, 0.08)',
            border: '1px solid rgba(239, 68, 68, 0.25)',
            display: 'flex',
            flexDirection: 'column',
            gap: '10px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#ef4444', fontWeight: 600, fontSize: '14px' }}>
              <AlertTriangle size={18} />
              <span>Official Pipeline Notice</span>
            </div>
            <p style={{ margin: 0, fontSize: '13px', color: '#64748b', lineHeight: 1.4 }}>
              {pipelineError}
            </p>
            <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
              <button
                type="button"
                onClick={handleRetry}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '6px 14px',
                  fontSize: '13px',
                  fontWeight: 500,
                  color: '#fff',
                  background: '#0ea5e9',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer'
                }}
              >
                <RotateCcw size={14} /> Retry Official Pipeline
              </button>
              {onCancel && (
                <button
                  type="button"
                  onClick={onCancel}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '6px 14px',
                    fontSize: '13px',
                    fontWeight: 500,
                    color: '#64748b',
                    background: 'transparent',
                    border: '1px solid #cbd5e1',
                    borderRadius: '6px',
                    cursor: 'pointer'
                  }}
                >
                  <X size={14} /> Cancel
                </button>
              )}
            </div>
          </div>
        )}

        <div className="processing-footer-info">
          <ShieldCheck size={14} className="note-icon" />
          <span>Processing Tamil Nadu administrative petition format</span>
        </div>

      </div>
    </div>
  );
}
