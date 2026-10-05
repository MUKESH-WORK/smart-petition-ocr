import React from 'react';
import { FileText, PlusCircle } from 'lucide-react';
import './Workspace.css';

export default function WorkspaceHeader({
  petition,
  onNewPetition
}) {
  return (
    <div className="workspace-header-bar">
      
      {/* Left: Identity & File Name */}
      <div className="workspace-header-left">
        {/* Petition Reference ID */}
        <div className="petition-id-chip" title="Official Petition Reference">
          <span className="id-label">PETITION ID</span>
          <span className="id-number">{petition?.id || 'TN-GDP-NEW'}</span>
        </div>

        {/* File Name */}
        <div className="petition-file-name" title={petition?.fileName}>
          <FileText size={15} className="file-icon" />
          <span className="file-name-text">{petition?.fileName}</span>
        </div>
      </div>

      {/* Right: Actions */}
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
