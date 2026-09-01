import React from 'react';
import { FileText, PlusCircle, CheckCircle2 } from 'lucide-react';
import './Workspace.css';

export default function WorkspaceHeader({
  petition,
  onNewPetition
}) {
  return (
    <div className="workspace-header-bar">
      
      {/* Left: Petition Meta Identity */}
      <div className="workspace-header-left">
        <div className="petition-id-chip">
          <span className="id-label">Petition</span>
          <span className="id-number font-mono">#{petition.id}</span>
        </div>

        <div className="petition-file-name" title={petition.fileName}>
          <FileText size={15} className="file-icon" />
          <span className="file-name-text">{petition.fileName}</span>
        </div>

        <div className="petition-status-pill" title="Optical Character Recognition & Document Understanding Completed">
          <span className="status-dot"></span>
          <span className="status-text">{petition.status}</span>
        </div>
      </div>

      {/* Right: New Petition Action */}
      <div className="workspace-header-right">
        <button 
          type="button" 
          className="new-petition-btn"
          onClick={onNewPetition}
          title="Upload or switch to another petition"
        >
          <PlusCircle size={14} />
          <span>New Petition</span>
        </button>
      </div>

    </div>
  );
}
