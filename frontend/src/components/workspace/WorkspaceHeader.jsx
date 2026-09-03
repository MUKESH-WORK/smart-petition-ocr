import React from 'react';
import { FileText, PlusCircle } from 'lucide-react';
import './Workspace.css';

export default function WorkspaceHeader({
  petition,
  onNewPetition
}) {
  return (
    <div className="workspace-header-bar">
      
      {/* Left: Document Name Only */}
      <div className="workspace-header-left">
        <div className="petition-file-name" title={petition?.fileName}>
          <FileText size={16} className="file-icon" />
          <span className="file-name-text">{petition?.fileName}</span>
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
