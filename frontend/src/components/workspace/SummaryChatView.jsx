import React, { useState, useRef, useEffect } from 'react';
import { 
  ArrowUp,
  Square,
  Bot, 
  User, 
  RotateCcw,
  FileText,
  MessageSquare,
  FileCheck2,
  CheckCircle2,
  Sparkles,
  Copy,
  Check,
  ShieldCheck,
  Building2,
  Phone,
  MapPin,
  Clock,
  Layers,
  ListOrdered
} from 'lucide-react';
import CopyButton from '../common/CopyButton';
import FullDetailsFormResponse from './FullDetailsFormResponse';
import { 
  getSmartAssistantReply, 
  getContextualSuggestions,
  extractPetitionDetails,
  isFullDetailsQuery
} from '../../data/mockPetitions';
import { askDocumentAssistant } from '../../services/apiService';
import './Workspace.css';

export default function SummaryChatView({ petition, onLogUserMessage }) {
  // Tab states: 'details' (default: extracted portal form) | 'chat' | 'ocr'
  const [activeTab, setActiveTab] = useState('details');
  const [conversation, setConversation] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [summaryLang, setSummaryLang] = useState('ta'); // 'ta' | 'en'
  const [copiedAll, setCopiedAll] = useState(false);

  // Track prompts that have been clicked/asked in this session
  const [usedPrompts, setUsedPrompts] = useState(new Set());
  
  const conversationScrollRef = useRef(null);
  const textareaRef = useRef(null);

  // Extract structured portal details
  const details = petition ? (petition.portalDetails || extractPetitionDetails(petition) || {}) : {};

  // Auto-scroll ONLY when new messages arrive in chat tab
  useEffect(() => {
    if (activeTab === 'chat' && conversationScrollRef.current && (conversation.length > 0 || isTyping)) {
      conversationScrollRef.current.scrollTo({
        top: conversationScrollRef.current.scrollHeight,
        behavior: 'smooth'
      });
    }
  }, [conversation, isTyping, activeTab]);

  // Adjust textarea height on input change
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  }, [inputValue]);

  // Compute active contextual suggestions dynamically
  const lastUserMessage = conversation
    .filter((m) => m.sender === 'officer')
    .slice(-1)[0]?.text || '';

  const activeSuggestions = getContextualSuggestions(lastUserMessage, usedPrompts);

  const handleSendMessage = (textToSend) => {
    const query = (textToSend || inputValue).trim();
    if (!query) return;

    // Switch to chat tab to view interaction immediately
    setActiveTab('chat');

    // Record this query as used to avoid repeating chips
    setUsedPrompts((prev) => new Set([...prev, query.toLowerCase().trim()]));

    // Log user message to Audit Trail
    if (onLogUserMessage) {
      onLogUserMessage(query, petition);
    }

    const userMessage = {
      id: `msg-user-${Date.now()}`,
      sender: 'officer',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      text: query
    };

    setConversation((prev) => [...prev, userMessage]);
    setInputValue('');
    setIsTyping(true);

    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }

    const isFullDetails = isFullDetailsQuery(query);

    if (isFullDetails) {
      setTimeout(() => {
        const fullDetailsData = extractPetitionDetails(petition);
        const assistantMessage = {
          id: `msg-ai-${Date.now()}`,
          sender: 'assistant',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          isFullDetails: true,
          details: fullDetailsData
        };
        setConversation((prev) => [...prev, assistantMessage]);
        setIsTyping(false);
      }, 350);
    } else {
      askDocumentAssistant(petition?.source_id, query, petition)
        .then((replyText) => {
          const assistantMessage = {
            id: `msg-ai-${Date.now()}`,
            sender: 'assistant',
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            isFullDetails: false,
            text: replyText
          };
          setConversation((prev) => [...prev, assistantMessage]);
        })
        .catch(() => {
          const fallbackText = getSmartAssistantReply(query, petition);
          const assistantMessage = {
            id: `msg-ai-${Date.now()}`,
            sender: 'assistant',
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            isFullDetails: false,
            text: fallbackText
          };
          setConversation((prev) => [...prev, assistantMessage]);
        })
        .finally(() => {
          setIsTyping(false);
        });
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleChipClick = (suggestion) => {
    if (suggestion === 'Full Details') {
      setActiveTab('details');
    } else {
      handleSendMessage(suggestion);
    }
  };

  const handleClearConversation = () => {
    setConversation([]);
    setUsedPrompts(new Set());
  };

  // Copy full structured petition fields summary to clipboard
  const handleCopyAllDetails = () => {
    const lines = [
      `=== TAMIL NADU GRIEVANCE PETITION DETAILS ===`,
      `Reference ID: ${petition?.id || 'Not found'}`,
      `Petitioner Name: ${details.petitionerName || 'Not found'}`,
      `Father/Husband: ${details.fatherHusbandName || 'Not found'}`,
      `Phone Number: ${details.phoneNumber || 'Not found'}`,
      `Address: ${details.address || 'Not found'}`,
      `Taluk: ${details.taluk || 'Not found'}`,
      `Village: ${details.village || 'Not found'}`,
      `District: ${details.district || 'Not found'}`,
      `Department: ${details.governmentDepartment || 'Not found'}`,
      `Grievance Type: ${details.grievanceType || 'Not found'}`,
      `Sub-Type: ${details.grievanceSubType || 'Not found'}`,
      `Responsible Officer: ${details.responsibleOfficer || 'Not found'}`,
      `Priority: ${details.priority || 'Medium'}`,
      `Due Date: ${details.dueDate || '15 Days'}`,
      `Description: ${details.description || petition?.summary || 'Not found'}`,
      `=============================================`
    ];
    navigator.clipboard.writeText(lines.join('\n'));
    setCopiedAll(true);
    setTimeout(() => setCopiedAll(false), 2000);
  };

  // Helper to render bold text and linebreaks
  const renderMessageContent = (text) => {
    if (!text) return null;
    const lines = text.split('\n');
    return lines.map((line, lineIdx) => {
      const parts = line.split(/(\*\*.*?\*\*)/g);
      const renderedLine = parts.map((part, i) => {
        if (part.startsWith('**') && part.endsWith('**')) {
          return <strong key={i}>{part.slice(2, -2)}</strong>;
        }
        return part;
      });

      return (
        <React.Fragment key={lineIdx}>
          {renderedLine}
          {lineIdx < lines.length - 1 && <br />}
        </React.Fragment>
      );
    });
  };

  const hasActionItems = Array.isArray(petition?.actionItems) && petition.actionItems.length > 0;
  const displaySummary = summaryLang === 'en' && petition?.summaryEnglish 
    ? petition.summaryEnglish 
    : (petition?.summaryTamil || petition?.summary || details.description || 'மனு விவரங்கள் பதிவு செய்யப்பட்டுள்ளன.');

  return (
    <div className="workspace-ai-panel-inner">
      
      {/* 1. TOP WORKSPACE TAB BAR */}
      <div className="workspace-tabs-bar" role="tablist" aria-label="Workspace Views">
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'details'}
          className={`workspace-tab-btn ${activeTab === 'details' ? 'active-tab' : ''}`}
          onClick={() => setActiveTab('details')}
          title="View structured extraction results and government portal fields"
        >
          <FileCheck2 size={16} />
          <span>Extracted Form Details</span>
          <span className="tab-pill-ready">Ready</span>
        </button>

        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'chat'}
          className={`workspace-tab-btn ${activeTab === 'chat' ? 'active-tab' : ''}`}
          onClick={() => setActiveTab('chat')}
          title="Chat with AI Document Assistant"
        >
          <MessageSquare size={16} />
          <span>AI Assistant & Chat</span>
          {conversation.length > 0 && (
            <span className="tab-count-badge">{conversation.length}</span>
          )}
        </button>

        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'ocr'}
          className={`workspace-tab-btn ${activeTab === 'ocr' ? 'active-tab' : ''}`}
          onClick={() => setActiveTab('ocr')}
          title="Inspect raw extracted OCR text"
        >
          <FileText size={16} />
          <span>Verbatim OCR Text</span>
        </button>
      </div>

      {/* =====================================================================
          TAB 1: EXTRACTED FORM DETAILS (DEFAULT ACTIVE RESULT DISPLAY)
          ===================================================================== */}
      {activeTab === 'details' && (
        <div className="tab-pane-container scrollable-tab-pane">
          
          {/* Executive Highlights Ribbon */}
          <div className="executive-highlights-ribbon">
            <div className="highlight-cell">
              <span className="highlight-label">PETITIONER</span>
              <span className="highlight-val font-semibold">{details.petitionerName || 'Not found'}</span>
            </div>
            <div className="highlight-cell">
              <span className="highlight-label">DEPARTMENT</span>
              <span className="highlight-val">{details.governmentDepartment || 'Not found'}</span>
            </div>
            <div className="highlight-cell">
              <span className="highlight-label">GRIEVANCE TYPE</span>
              <span className="highlight-val">{details.grievanceType || 'Not found'}</span>
            </div>
            <div className="highlight-cell">
              <span className="highlight-label">TALUK / JURISDICTION</span>
              <span className="highlight-val">{details.taluk || details.district || 'Not found'}</span>
            </div>
            <div className="highlight-cell">
              <span className="highlight-label">PRIORITY</span>
              <span className={`priority-tag-pill priority-${(details.priority || 'medium').toLowerCase()}`}>
                {details.priority || 'Medium'}
              </span>
            </div>
          </div>

          {/* Executive Summary & AI Insights Card */}
          <div className="executive-summary-card">
            <div className="summary-card-header">
              <div className="summary-card-title-group">
                <Sparkles size={16} className="summary-sparkle-icon" />
                <span className="summary-title-heading">EXECUTIVE SUMMARY & ACTION ITEMS</span>
              </div>
              
              <div className="summary-header-actions">
                {/* Language Toggle if English summary is available */}
                {petition?.summaryEnglish && (
                  <div className="summary-lang-toggle">
                    <button
                      type="button"
                      className={`lang-toggle-btn ${summaryLang === 'ta' ? 'active' : ''}`}
                      onClick={() => setSummaryLang('ta')}
                    >
                      தமிழ்
                    </button>
                    <button
                      type="button"
                      className={`lang-toggle-btn ${summaryLang === 'en' ? 'active' : ''}`}
                      onClick={() => setSummaryLang('en')}
                    >
                      English
                    </button>
                  </div>
                )}
                
                {/* Verification Score Badge */}
                <div className="verification-grounding-badge" title="Verified against optical character scan">
                  <ShieldCheck size={13} className="grounding-shield-icon" />
                  <span>{petition?.confidenceScore ? `${petition.confidenceScore}% Confident` : 'Verified Grounded'}</span>
                </div>
              </div>
            </div>

            {/* Summary Text Body */}
            <p className="summary-main-paragraph">
              {displaySummary}
            </p>

            {/* Action Items Checklist */}
            {hasActionItems && (
              <div className="summary-action-items-section">
                <div className="action-items-title">
                  <ListOrdered size={14} />
                  <span>RECOMMENDED ACTION ITEMS / நடவடிக்கை பரிந்துரைகள்</span>
                </div>
                <ul className="action-items-list">
                  {petition.actionItems.map((item, idx) => {
                    const actionText = typeof item === 'string'
                      ? item
                      : (item?.action || item?.text || (typeof item === 'object' ? JSON.stringify(item) : String(item)));
                    const dept = typeof item === 'object' ? item?.department : null;
                    const deadline = typeof item === 'object' ? item?.deadline_hint : null;

                    return (
                      <li key={idx} className="action-item-row">
                        <CheckCircle2 size={14} className="action-check-icon" />
                        <div className="action-item-content">
                          <span className="action-text">{actionText}</span>
                          {(dept || deadline) && (
                            <div className="action-meta-tags" style={{ display: 'flex', gap: '6px', marginTop: '2px', fontSize: '0.78rem', color: '#64748B' }}>
                              {dept && <span className="action-dept-tag" style={{ background: '#F1F5F9', padding: '1px 6px', borderRadius: '4px' }}>{dept}</span>}
                              {deadline && <span className="action-deadline-tag" style={{ color: '#D97706' }}>⏱ {deadline}</span>}
                            </div>
                          )}
                        </div>
                      </li>
                    );
                  })}
                </ul>
              </div>
            )}
          </div>

          {/* Structured Official Form Details */}
          <div className="portal-form-wrapper">
            <div className="portal-form-section-banner">
              <div className="banner-left">
                <Layers size={16} />
                <span>OFFICIAL PORTAL REGISTRATION FIELDS (VERIFIED FROM PETITION)</span>
              </div>
              <button
                type="button"
                className={`quick-copy-all-btn ${copiedAll ? 'copied' : ''}`}
                onClick={handleCopyAllDetails}
                title="Copy all extracted petition fields formatted"
              >
                {copiedAll ? <Check size={13} /> : <Copy size={13} />}
                <span>{copiedAll ? 'Copied to Clipboard' : 'Copy All Fields'}</span>
              </button>
            </div>

            {/* Full 5-Section Details Form */}
            <FullDetailsFormResponse initialDetails={details} />
          </div>

          {/* Bottom Callout Bar: Switch to AI Chat */}
          <div className="details-tab-bottom-cta">
            <div className="cta-text-group">
              <span className="cta-headline">Have a specific question about this petition?</span>
              <span className="cta-sub">Ask the bilingual AI assistant with page citations and legal routing rules.</span>
            </div>
            <button
              type="button"
              className="cta-chat-switch-btn"
              onClick={() => setActiveTab('chat')}
            >
              <MessageSquare size={14} />
              <span>Open Document Chat</span>
            </button>
          </div>

        </div>
      )}

      {/* =====================================================================
          TAB 2: AI ASSISTANT CHAT
          ===================================================================== */}
      {activeTab === 'chat' && (
        <div className="tab-pane-container chat-tab-pane">
          
          {/* SCROLLABLE CONVERSATION STREAM */}
          <div className="conversation-messages-scroll-area" ref={conversationScrollRef}>
            <div className="conversation-stream">
              
              {/* Compact Summary Anchor at Top of Chat */}
              <div className="conversation-summary-message">
                <div className="compact-summary-card">
                  <div className="summary-title-label">EXECUTIVE SUMMARY</div>
                  <p className="summary-main-text">{displaySummary}</p>
                </div>
              </div>

              {/* Chat Header Actions */}
              {conversation.length > 0 && (
                <div className="conversation-header-actions">
                  <span className="conversation-label">DOCUMENT CHAT</span>
                  <button 
                    type="button" 
                    className="clear-chat-link-btn"
                    onClick={handleClearConversation}
                    title="Clear conversation and reset recommendations"
                  >
                    <RotateCcw size={11} />
                    <span>Reset Chat</span>
                  </button>
                </div>
              )}

              {/* Conversation Messages */}
              {conversation.map((msg) => {
                const isOfficer = msg.sender === 'officer';
                return (
                  <div 
                    key={msg.id} 
                    className={`conversation-row ${isOfficer ? 'row-officer' : 'row-assistant'}`}
                  >
                    <div className={`row-avatar ${isOfficer ? 'avatar-officer' : 'avatar-ai'}`}>
                      {isOfficer ? <User size={13} /> : <Bot size={13} />}
                    </div>

                    <div className="row-content-body">
                      <div className="row-meta-line">
                        <span className="meta-sender">
                          {isOfficer ? 'Officer' : 'Petition Assistant'}
                        </span>
                        <span className="meta-time">{msg.timestamp}</span>
                      </div>

                      {msg.isFullDetails ? (
                        <div className="message-bubble bubble-ai full-details-bubble">
                          <FullDetailsFormResponse initialDetails={msg.details} />
                        </div>
                      ) : (
                        <div className={`message-bubble ${isOfficer ? 'bubble-officer' : 'bubble-ai'}`}>
                          <div className="bubble-text">
                            {renderMessageContent(msg.text)}
                          </div>
                          {!isOfficer && (
                            <div className="bubble-footer-actions">
                              <CopyButton textToCopy={msg.text} label="Copy Answer" className="compact-copy-btn" />
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}

              {isTyping && (
                <div className="conversation-row row-assistant">
                  <div className="row-avatar avatar-ai">
                    <Bot size={13} />
                  </div>
                  <div className="typing-indicator-box">
                    <span className="dot"></span>
                    <span className="dot"></span>
                    <span className="dot"></span>
                  </div>
                </div>
              )}

            </div>
          </div>

          {/* BOTTOM CHAT COMPOSER DOCK */}
          <div className="workspace-bottom-composer-dock">
            
            {/* Dynamic Contextual Prompt Chips */}
            {activeSuggestions.length > 0 && (
              <div className="contextual-prompts-row">
                <button
                  type="button"
                  className="full-details-action-chip"
                  onClick={() => setActiveTab('details')}
                  disabled={isTyping}
                  title="View full structured portal details form"
                >
                  <FileCheck2 size={13} />
                  <span>View Full Form</span>
                </button>
                {activeSuggestions.map((suggestion, idx) => (
                  <button
                    key={idx}
                    type="button"
                    className="contextual-followup-chip"
                    onClick={() => handleChipClick(suggestion)}
                    disabled={isTyping}
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            )}

            {/* Modern Nexus-UI Style Prompt Input Box */}
            <div className="prompt-input-container">
              <div className="prompt-input-card">
                
                <textarea
                  ref={textareaRef}
                  className="prompt-input-textarea"
                  placeholder="Ask anything about this petition (Tamil or English)..."
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyDown={handleKeyDown}
                  disabled={isTyping}
                  rows={2}
                />

                <div className="prompt-input-actions-bar">
                  <div className="prompt-actions-left">
                    <span className="prompt-hint-text">Enter to send • Shift+Enter for new line</span>
                  </div>
                  <div className="prompt-actions-right">
                    <button
                      type="button"
                      className={`prompt-submit-circle-btn ${inputValue.trim() || isTyping ? 'btn-active' : 'btn-disabled'}`}
                      onClick={() => handleSendMessage()}
                      disabled={(!inputValue.trim() && !isTyping)}
                      title={isTyping ? "Generating response..." : "Send message (Enter)"}
                      aria-label={isTyping ? "Generating response" : "Send message"}
                    >
                      {isTyping ? (
                        <Square size={13} className="fill-current" />
                      ) : (
                        <ArrowUp size={16} strokeWidth={2.2} />
                      )}
                    </button>
                  </div>
                </div>

              </div>
            </div>

          </div>

        </div>
      )}

      {/* =====================================================================
          TAB 3: VERBATIM OCR SCANNED TEXT
          ===================================================================== */}
      {activeTab === 'ocr' && (
        <div className="tab-pane-container scrollable-tab-pane">
          <div className="ocr-text-viewer-card">
            <div className="ocr-viewer-header">
              <div className="ocr-header-title">
                <FileText size={16} />
                <span>RAW EXTRACTED OCR TEXT ({petition?.rawOcrText ? petition.rawOcrText.length : 0} CHARACTERS)</span>
              </div>
              <CopyButton 
                textToCopy={petition?.rawOcrText || ''} 
                label="Copy Raw Text" 
                className="compact-copy-btn" 
              />
            </div>
            <pre className="ocr-raw-preformatted-block">
              {petition?.rawOcrText || 'No OCR text extracted for this document.'}
            </pre>
          </div>
        </div>
      )}

    </div>
  );
}
