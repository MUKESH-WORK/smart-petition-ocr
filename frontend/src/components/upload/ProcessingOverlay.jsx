import React, { useState, useEffect, useCallback, useRef } from 'react';
import { FileText, CheckCircle2, Loader2, Circle, ShieldCheck, AlertTriangle, RotateCcw, X } from 'lucide-react';
import { uploadAndAnalyzePetition } from '../../services/apiService';
import './Upload.css';

const PROCESSING_STEPS = [
  { id: 1, label: 'Document Received', detail: 'Received securely and validated into memory' },
  { id: 2, label: 'Optical Character Recognition', detail: 'High-precision bilingual Tamil & English OCR' },
  { id: 3, label: 'Semantic Vector Indexing', detail: 'Generating 384-d dense embeddings & chunking' },
  { id: 4, label: 'Entity & Location Resolution', detail: 'Extracting petitioner info & mapping to official taluk/block' },
  { id: 5, label: 'CM Grievance RAG Mapping', detail: 'Deterministic 3-tier routing across 40 departments' },
  { id: 6, label: 'Dossier Ready for Review', detail: 'Structured grievance draft synthesized for officer sign-off' }
];

export default function ProcessingOverlay({ petition, onComplete, onCancel }) {
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [pipelineError, setPipelineError] = useState(null);
  const [retryNonce, setRetryNonce] = useState(0);
  const [telemetry, setTelemetry] = useState({
    stageName: 'uploaded',
    stageLabel: 'Document Received',
    pageCount: 1,
    chunkCount: 0,
    entityCount: 0,
    ocrConfidence: null
  });

  const handleRetry = useCallback(() => {
    setPipelineError(null);
    setCurrentStepIndex(0);
    setRetryNonce((n) => n + 1);
  }, []);

  useEffect(() => {
    let isMounted = true;
    const abortController = new AbortController();

    // Pure server-driven progress callback — ZERO artificial timers
    const onProgressCallback = (data) => {
      if (!isMounted) return;
      if (typeof data === 'object' && data !== null) {
        if (typeof data.stepIndex === 'number') {
          setCurrentStepIndex((prev) => Math.max(prev, data.stepIndex));
        }
        setTelemetry((prev) => ({
          ...prev,
          stageName: data.stageName || prev.stageName,
          stageLabel: data.stageLabel || prev.stageLabel,
          pageCount: data.pageCount || prev.pageCount,
          chunkCount: data.chunkCount !== undefined ? data.chunkCount : prev.chunkCount,
          entityCount: data.entityCount !== undefined ? data.entityCount : prev.entityCount,
          ocrConfidence: data.ocrConfidence !== undefined ? data.ocrConfidence : prev.ocrConfidence
        }));
      } else if (typeof data === 'number') {
        setCurrentStepIndex((prev) => Math.max(prev, data));
      }
    };

    // Official backend upload & analysis pipeline
    const pipelinePromise = petition?.file
      ? uploadAndAnalyzePetition(petition.file, onProgressCallback, abortController.signal)
      : Promise.resolve(petition);

    pipelinePromise
      .then((realAnalyzedDoc) => {
        if (!isMounted) return;
        // Backend finished — advance to final step (Ready for understanding — 100%)
        setCurrentStepIndex(PROCESSING_STEPS.length - 1);
        setTimeout(() => {
          if (isMounted) {
            onComplete(realAnalyzedDoc || petition);
          }
        }, 500);
      })
      .catch((err) => {
        if (!isMounted || abortController.signal.aborted) return;
        console.error('Official pipeline error:', err);
        setPipelineError(err.message || 'An error occurred during processing');
      });

    return () => {
      isMounted = false;
      abortController.abort();
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [petition, retryNonce]);

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

        {/* Real-time Server Stage Telemetry Banner */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '8px',
          padding: '8px 12px',
          background: 'rgba(16, 44, 87, 0.04)',
          border: '1px solid var(--border-subtle)',
          borderRadius: '6px',
          margin: '10px 0 14px 0',
          fontSize: '0.75rem',
          color: 'var(--text-secondary)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 600, color: '#102C57' }}>
            <span style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              background: pipelineError ? '#ef4444' : '#10b981',
              display: 'inline-block',
              boxShadow: pipelineError ? 'none' : '0 0 6px #10b981'
            }} />
            <span>Server Stage: {telemetry.stageLabel}</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span>Pages: <strong>{telemetry.pageCount}</strong></span>
            <span>Chunks: <strong>{telemetry.chunkCount}</strong></span>
            <span>Entities: <strong>{telemetry.entityCount}</strong></span>
            {telemetry.ocrConfidence !== null && (
              <span style={{ color: '#047857', fontWeight: 600 }}>Confidence: <strong>{telemetry.ocrConfidence}%</strong></span>
            )}
          </div>
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
                  fontWeight: 600,
                  color: '#FEFAF6',
                  background: '#102C57',
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
                    color: 'var(--text-secondary)',
                    background: 'transparent',
                    border: '1px solid var(--border-medium)',
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
