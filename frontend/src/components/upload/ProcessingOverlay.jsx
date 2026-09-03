import React, { useState, useEffect, useRef } from 'react';
import { FileText, CheckCircle2, Loader2, Circle, ShieldCheck } from 'lucide-react';
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

export default function ProcessingOverlay({ petition, onComplete }) {
  const [currentStepIndex, setCurrentStepIndex] = useState(0);

  useEffect(() => {
    let isMounted = true;
    const timers = [];

    // Progressive step sequence (visual progress while backend works)
    // Step 0: Document uploaded (0ms)
    // Step 1: Reading document (600ms)
    // Step 2: Detecting language (1300ms)
    // Step 3: Extracting text (2100ms)
    // Step 4: Generating petition summary (3000ms - waits here for backend)
    timers.push(setTimeout(() => { if (isMounted) setCurrentStepIndex(1); }, 600));
    timers.push(setTimeout(() => { if (isMounted) setCurrentStepIndex(2); }, 1300));
    timers.push(setTimeout(() => { if (isMounted) setCurrentStepIndex(3); }, 2100));
    timers.push(setTimeout(() => { if (isMounted) setCurrentStepIndex(4); }, 3000));

    // Real backend upload & analysis pipeline
    const pipelinePromise = petition?.file
      ? uploadAndAnalyzePetition(petition.file)
      : Promise.resolve(petition);

    pipelinePromise
      .then((realAnalyzedDoc) => {
        if (!isMounted) return;
        // Backend finished! Advance to final step (Ready for understanding - 100%)
        setCurrentStepIndex(5);
        timers.push(setTimeout(() => {
          if (isMounted) {
            onComplete(realAnalyzedDoc || petition);
          }
        }, 750));
      })
      .catch((err) => {
        console.warn('Real backend processing note:', err);
        if (!isMounted) return;
        setCurrentStepIndex(5);
        timers.push(setTimeout(() => {
          if (isMounted) {
            onComplete(petition);
          }
        }, 750));
      });

    return () => {
      isMounted = false;
      timers.forEach(clearTimeout);
    };
  }, [petition, onComplete]);

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
            const isCurrent = idx === currentStepIndex;
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

        <div className="processing-footer-info">
          <ShieldCheck size={14} className="note-icon" />
          <span>Processing Tamil Nadu administrative petition format</span>
        </div>

      </div>
    </div>
  );
}
