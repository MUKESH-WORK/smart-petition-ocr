import React, { useState, useRef, useEffect } from 'react';
import { 
  ArrowUp,
  Square,
  Bot, 
  User, 
  RotateCcw
} from 'lucide-react';
import CopyButton from '../common/CopyButton';
import FullDetailsFormResponse from './FullDetailsFormResponse';
import { 
  getSmartAssistantReply, 
  getContextualSuggestions,
  extractPetitionDetails,
  isFullDetailsQuery
} from '../../data/mockPetitions';
import './Workspace.css';

export default function SummaryChatView({ petition }) {
  const [conversation, setConversation] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  
  // Track prompts that have been clicked/asked in this session
  const [usedPrompts, setUsedPrompts] = useState(new Set());
  
  const conversationScrollRef = useRef(null);
  const textareaRef = useRef(null);

  // Auto-scroll ONLY when new messages arrive (does not force-scroll on initial load)
  useEffect(() => {
    if (conversationScrollRef.current && (conversation.length > 0 || isTyping)) {
      conversationScrollRef.current.scrollTo({
        top: conversationScrollRef.current.scrollHeight,
        behavior: 'smooth'
      });
    }
  }, [conversation, isTyping]);

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

    // Record this query as used to avoid repeating chips
    setUsedPrompts((prev) => new Set([...prev, query.toLowerCase().trim()]));

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

    // Fast simulated AI document understanding response
    setTimeout(() => {
      if (isFullDetails) {
        const details = extractPetitionDetails(petition);
        const assistantMessage = {
          id: `msg-ai-${Date.now()}`,
          sender: 'assistant',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          isFullDetails: true,
          details: details
        };
        setConversation((prev) => [...prev, assistantMessage]);
      } else {
        const replyText = getSmartAssistantReply(query, petition);
        const assistantMessage = {
          id: `msg-ai-${Date.now()}`,
          sender: 'assistant',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          isFullDetails: false,
          text: replyText
        };
        setConversation((prev) => [...prev, assistantMessage]);
      }
      setIsTyping(false);
    }, 380);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleChipClick = (suggestion) => {
    if (suggestion === 'Full Details') {
      handleSendMessage('Give me the full details.');
    } else {
      handleSendMessage(suggestion);
    }
  };

  const handleClearConversation = () => {
    setConversation([]);
    setUsedPrompts(new Set());
  };

  // Helper to render bold text and clean linebreaks
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

  const isInitialState = conversation.length === 0;

  return (
    <div className="workspace-ai-panel-inner">
      
      {/* SCROLLABLE CONVERSATION AREA (Contains Summary as First Message + All Chat Messages) */}
      <div className="conversation-messages-scroll-area" ref={conversationScrollRef}>
        <div className="conversation-stream">
          
          {/* 1. FIRST AI MESSAGE: Clean Simple Summary Card */}
          <div className="conversation-summary-message">
            <div className="compact-summary-card">
              <div className="summary-title-label">SUMMARY</div>
              <p className="summary-main-text">{petition.summary}</p>
            </div>
          </div>

          {/* Reset Chat Control when conversation has started */}
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

          {/* 2. SUBSEQUENT OFFICER & ASSISTANT MESSAGES */}
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

      {/* 3. BOTTOM SECTION: Stationary Nexus-UI Style Prompt Input & Contextual Chips */}
      <div className="workspace-bottom-composer-dock">
        
        {/* Dynamic Contextual Prompt Chips */}
        {activeSuggestions.length > 0 && (
          <div className="contextual-prompts-row">
            {isInitialState ? (
              <button
                type="button"
                className="full-details-action-chip"
                onClick={() => handleChipClick('Full Details')}
                disabled={isTyping}
                title="Request full structured petition details"
              >
                <span>Full Details</span>
              </button>
            ) : (
              activeSuggestions.map((suggestion, idx) => (
                <button
                  key={idx}
                  type="button"
                  className="contextual-followup-chip"
                  onClick={() => handleChipClick(suggestion)}
                  disabled={isTyping}
                >
                  {suggestion}
                </button>
              ))
            )}
          </div>
        )}

        {/* Modern Nexus-UI Style Prompt Input Box */}
        <div className="prompt-input-container">
          <div className="prompt-input-card">
            
            {/* Textarea Area */}
            <textarea
              ref={textareaRef}
              className="prompt-input-textarea"
              placeholder="Ask anything about this petition..."
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isTyping}
              rows={2}
            />

            {/* Bottom Actions Bar with Circular Action Button */}
            <div className="prompt-input-actions-bar">
              <div className="prompt-actions-left"></div>
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
  );
}
