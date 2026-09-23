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
  Copy,
  Check,
  Building2,
  Phone,
  MapPin,
  Clock,
  Layers,
  Languages,
  Loader2
} from 'lucide-react';
import CopyButton from '../common/CopyButton';
import FullDetailsFormResponse from './FullDetailsFormResponse';
import { 
  getSmartAssistantReply, 
  getContextualSuggestions,
  extractPetitionDetails,
  isFullDetailsQuery
} from '../../data/mockPetitions';
import { askDocumentAssistant, translateText } from '../../services/apiService';
import './Workspace.css';

export default function SummaryChatView({ petition, onLogUserMessage }) {
  // Tab states: 'details' (default: extracted portal form) | 'chat' | 'ocr'
  const [activeTab, setActiveTab] = useState('details');
  const [conversation, setConversation] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [summaryLang, setSummaryLang] = useState('ta'); // 'ta' | 'en'
  const [copiedAll, setCopiedAll] = useState(false);
  const [dynamicSummary, setDynamicSummary] = useState({});
  const [isTranslatingSummary, setIsTranslatingSummary] = useState(false);

  // Track prompts that have been clicked/asked in this session
  const [usedPrompts, setUsedPrompts] = useState(new Set());

  const conversationScrollRef = useRef(null);
  const textareaRef = useRef(null);

  // Extract structured portal details safely
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

  // Handle translation toggle with real API fallback
  const handleToggleSummaryLanguage = async (targetLang) => {
    if (targetLang === summaryLang) return;
    setSummaryLang(targetLang);

    if (targetLang === 'en') {
      if (petition?.summaryEnglish || dynamicSummary.en) return;
      const baseText = petition?.summaryTamil || petition?.summary || details.description;
      if (baseText) {
        setIsTranslatingSummary(true);
        try {
          const translated = await translateText(baseText, 'en', 'ta');
          setDynamicSummary(prev => ({ ...prev, en: translated }));
        } catch (err) {
          console.warn('Summary translation notice:', err);
        } finally {
          setIsTranslatingSummary(false);
        }
      }
    } else if (targetLang === 'ta') {
      if (petition?.summaryTamil || dynamicSummary.ta) return;
      const baseText = petition?.summaryEnglish || details.description;
      if (baseText) {
        setIsTranslatingSummary(true);
        try {
          const translated = await translateText(baseText, 'ta', 'en');
          setDynamicSummary(prev => ({ ...prev, ta: translated }));
        } catch (err) {
          console.warn('Summary translation notice:', err);
        } finally {
          setIsTranslatingSummary(false);
        }
      }
    }
  };

  const handleSendMessage = (textToSend) => {
    const query = (textToSend || inputValue).trim();
    if (!query) return;

    setActiveTab('chat');
    setUsedPrompts((prev) => new Set([...prev, query.toLowerCase().trim()]));

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
      `I) .Petitioner/மனுதாரர்`,
      `1. Name/பெயர்*: ${details.petitionerName || 'Not found'}`,
      `2. Email/மின்னஞ்சல்: ${details.email || 'Not found'}`,
      `3. Phone/தொலைபேசி*: ${details.phoneNumber || 'Not found'}`,
      `4. Is this your own number/இது தங்களது கைப்பேசி எண்ணா(yes or no): ${details.isOwnNumber || 'Not mentioned'}`,
      `5. Alternate Phone Number/மாற்று தொலைபேசி எண்: ${details.alternatePhone || 'Not found'}`,
      `6. Address*: ${details.address || 'Not found'}`,
      `7. Please enter your gender*: ${details.gender || 'Not mentioned'}`,
      `8. Are You a Differently Abled Person*(yes/no/-None-): ${details.differentlyAbled || 'No'}`,
      `9. சமூகம்/தனிப்பட்ட குறை*(Public/personal): ${details.petitionerCategory || 'Personal / தனிப்பட்ட குறை'}`,
      ``,
      `II) Grievance Details`,
      `10. Description *: ${details.description || petition?.summary || 'Not found'}`,
      `12. Grievance Source/குறைக்கான ஆதாரம்*: ${details.grievanceSource || 'Collectorate Grievance Day Petition'}`,
      `13. Ref Number: ${details.referenceNumber || 'Not found'}`,
      `14. Government Department / குறை தொடர்புடைய அரசு துறை*: ${details.governmentDepartment || 'Not found'}`,
      `15. Local Body Type*: ${details.localBodyType || 'Rural / கிராமப்புறம்'}`,
      `16. Grievance Type/குறையின் வகை*: ${details.grievanceType || 'Not found'}`,
      `17. Grievance SubType / குறையின்துணை வகை*: ${details.grievanceSubType || 'Not found'}`,
      `18. District/ மாவட்டம்*: ${details.district || 'Erode / ஈரோடு'}`,
      `19. Sub Department/குறை தொடர்புடைய துணைத்துறை*: ${details.subDepartment || 'Not found'}`,
      `20. Ward/வார்டு: ${details.ward || 'Not found'}`,
      `21. Municipality Ward/நகராட்சி வார்டு: ${details.municipalityWard || 'Not found'}`,
      `22. Block/வட்டாரம்*: ${details.block || 'Not found'}`,
      `23. Taluk/வட்டம்: ${details.taluk || 'Not found'}`,
      `24. Revenue Division/உட்கோட்டம்*: ${details.revenueDivision || 'Erode / ஈரோடு'}`,
      `25. Firka/ குறுவட்டம்: ${details.firka || 'Not found'}`,
      `26. Street Name/தெருவின் பெயர்: ${details.streetName || 'Not found'}`,
      `27. Door No/கதவு எண்: ${details.doorNumber || 'Not found'}`,
      `28. Responsible Officer/பொறுப்பு அதிகாரி*: ${details.responsibleOfficer || 'District Revenue Officer / மாவட்ட வருவாய் அலுவலர்'}`,
      `29. Fisheries Region: ${details.fisheriesRegion || 'Not found'}`,
      `30. Fisheries Division *: ${details.fisheriesDivision || 'Not found'}`,
      `31. Reason for Redirection: ${details.reasonForRedirection || 'Not applicable / பொருந்தாது'}`,
      ``,
      `III) Communication Address`,
      `32. Select if different from above/மேலே உள்ள முகவரியில் தங்கவில்லை என்றால்(yes/no): ${details.communicationAddressSame || 'No'}`,
      ``,
      `Grievance Status/குறையின் நிலை`,
      `33. Due Date/தீர்வு நாள் dd MMM yyyy hh:mm: ${details.dueDate || '31 Aug 2026 17:00'}`,
      `35. Status */நிலை*: ${details.status || 'Open / நிலுவையில் உள்ளது'}`,
      `36. Source Code: ${details.sourceCode || 'GDP - Grievance Day Petition'}`,
      `37. Grievance ID-TN/AHFISH/ERD/P/{Mode}/31AUG26/g: ${details.grievanceId || 'TN/AHFISH/ERD/P/OFFLINE/31AUG26/001'}`,
      `38. Priority: ${details.priority || 'Medium'}`,
      `39. Call Disposition: ${details.callDisposition || 'Registered / பதிவு செய்யப்பட்டது'}`,
      `40. Is Whatsapp Appeal (yes/no): ${details.isWhatsappAppeal || 'No'}`,
      `41. Is Whatsapp Tracking (yes/no): ${details.isWhatsappTracking || 'Yes'}`,
      `42. Is Whatsapp Receipt (yes/no): ${details.isWhatsappReceipt || 'Yes'}`,
      `43. Ex-Army Petition Details Relationship with Ex-servicemen(yes/no): ${details.relationshipWithExServicemen || 'No'}`,
      `=============================================`
    ];
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(lines.join('\n'));
    }
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

  let displaySummary = 'மனு விவரங்கள் பதிவு செய்யப்பட்டுள்ளன.';
  if (summaryLang === 'en') {
    displaySummary = petition?.summaryEnglish || dynamicSummary.en || petition?.summary || 'Petition details recorded.';
  } else {
    displaySummary = petition?.summaryTamil || dynamicSummary.ta || petition?.summary || details.description || 'மனு விவரங்கள் பதிவு செய்யப்பட்டுள்ளன.';
  }

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
          
          {/* Executive Summary Card */}
          <div className="executive-summary-card">
            <div className="summary-card-header">
              <div className="summary-card-title-group">
                <span className="summary-title-heading">EXECUTIVE SUMMARY</span>
              </div>
              
              <div className="summary-header-actions">
                {/* Language Translation Icon Button */}
                <div className="summary-translation-dock">
                  <button
                    type="button"
                    className="summary-trans-icon-btn"
                    onClick={() => handleToggleSummaryLanguage(summaryLang === 'ta' ? 'en' : 'ta')}
                    disabled={isTranslatingSummary}
                    title={summaryLang === 'ta' ? 'Translate Summary to English' : 'Translate Summary to தமிழ் (Tamil)'}
                    aria-label="Translate Summary"
                  >
                    {isTranslatingSummary ? (
                      <Loader2 size={14} className="spin-icon" />
                    ) : (
                      <Languages size={15} className="trans-icon" />
                    )}
                    <span className="trans-lang-pill">
                      {isTranslatingSummary ? 'Translating...' : (summaryLang === 'ta' ? 'தமிழ்' : 'English')}
                    </span>
                  </button>
                </div>
              </div>
            </div>

            {/* Summary Text Body */}
            <p className="summary-main-paragraph">
              {displaySummary}
            </p>
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
