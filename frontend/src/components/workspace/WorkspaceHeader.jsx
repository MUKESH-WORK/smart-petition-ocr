import React from 'react';
import { FileText, PlusCircle, User, Building2, CheckCircle2 } from 'lucide-react';
import './Workspace.css';

export default function WorkspaceHeader({
  petition,
  onNewPetition
}) {
  const petitionerName = petition?.portalDetails?.petitionerName;
  const hasPetitionerName = petitionerName && petitionerName !== 'Not found';

  const department = petition?.portalDetails?.governmentDepartment;
  const hasDepartment = department && department !== 'Not found';

  return (
    <div className="workspace-header-bar">
      
      {/* Left: Identity, File Name, Key Attributes & Status */}
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

        {/* Extracted Petitioner Name Tag */}
        {hasPetitionerName && (
          <div className="header-meta-badge petitioner-badge" title={`Petitioner: ${petitionerName}`}>
            <User size={13} />
            <span className="meta-badge-text">{petitionerName}</span>
          </div>
        )}

        {/* Extracted Department Tag */}
        {hasDepartment && (
          <div className="header-meta-badge department-badge" title={`Routing Department: ${department}`}>
            <Building2 size={13} />
            <span className="meta-badge-text">{department}</span>
          </div>
        )}

        {/* Verification Status Pill */}
        <div className="petition-status-pill" title="Processing and Verification Status">
          <span className="status-dot"></span>
          <span>{petition?.status || 'Analysis Complete'}</span>
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
