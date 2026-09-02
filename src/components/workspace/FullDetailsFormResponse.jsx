import React, { useState } from 'react';
import { Copy, Check } from 'lucide-react';
import './Workspace.css';

function FieldCopyButton({ value, disabled }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = (e) => {
    e.stopPropagation();
    if (disabled || !value || value === 'Not found') return;
    navigator.clipboard.writeText(value);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  if (disabled || !value || value === 'Not found') {
    return (
      <button
        type="button"
        className="field-inline-copy-btn disabled-copy-btn"
        disabled
        title="Field is not found"
        aria-label="Field is not found"
      >
        <Copy size={11} />
        <span>Copy</span>
      </button>
    );
  }

  return (
    <button
      type="button"
      className={`field-inline-copy-btn ${copied ? 'copied' : ''}`}
      onClick={handleCopy}
      title={`Copy ${value}`}
      aria-label={`Copy value`}
    >
      {copied ? (
        <>
          <Check size={11} className="copy-icon-check" />
          <span>Copied</span>
        </>
      ) : (
        <>
          <Copy size={11} />
          <span>Copy</span>
        </>
      )}
    </button>
  );
}

function FieldDisplayBox({ label, value, isFullWidth = false, isMultiline = false }) {
  const isNotFound = !value || value.toString().toLowerCase() === 'not found';
  const displayValue = value || 'Not found';

  return (
    <div className={`form-item-wrapper ${isFullWidth ? 'col-full' : 'col-half'}`}>
      <label className="form-item-label">{label}</label>
      <div className={`info-display-box ${isMultiline ? 'multiline-box' : ''} ${isNotFound ? 'box-not-found' : ''}`}>
        <span className={`info-display-text ${isNotFound ? 'text-not-found' : ''}`}>
          {displayValue}
        </span>
        <FieldCopyButton value={displayValue} disabled={isNotFound} />
      </div>
    </div>
  );
}

export default function FullDetailsFormResponse({ initialDetails }) {
  const data = initialDetails || {};

  return (
    <div className="full-details-form-container" role="region" aria-label="Full Petition Details">
      
      {/* Response Main Title */}
      <div className="full-details-header-row">
        <h4 className="full-details-main-heading">FULL PETITION DETAILS</h4>
      </div>

      {/* =========================================================================
          1. PETITIONER INFORMATION
          ========================================================================= */}
      <div className="portal-sub-section">
        <div className="portal-sub-section-header">
          <span className="portal-section-badge">1</span>
          <h5 className="portal-section-title">PETITIONER INFORMATION</h5>
        </div>

        <div className="full-details-form-grid">
          <FieldDisplayBox label="Petitioner Name" value={data.petitionerName} />
          <FieldDisplayBox label="Email" value={data.email} />
          
          <FieldDisplayBox label="Phone Number" value={data.phoneNumber} />
          <FieldDisplayBox label="Is this your own number" value={data.isOwnNumber} />
          
          <FieldDisplayBox label="Alternate Phone Number" value={data.alternatePhone} />
          <FieldDisplayBox label="Gender" value={data.gender} />

          <FieldDisplayBox label="Address" value={data.address} isFullWidth isMultiline />

          <FieldDisplayBox label="Differently Abled Person" value={data.differentlyAbled} />
          <FieldDisplayBox label="Petitioner Category" value={data.petitionerCategory} />
        </div>
      </div>

      {/* =========================================================================
          2. GRIEVANCE DETAILS
          ========================================================================= */}
      <div className="portal-sub-section">
        <div className="portal-sub-section-header">
          <span className="portal-section-badge">2</span>
          <h5 className="portal-section-title">GRIEVANCE DETAILS</h5>
        </div>

        <div className="full-details-form-grid">
          <FieldDisplayBox label="Description" value={data.description} isFullWidth isMultiline />
          
          <FieldDisplayBox label="Grievance Source" value={data.grievanceSource} />
          <FieldDisplayBox label="Reference Number" value={data.referenceNumber} />

          <FieldDisplayBox label="Government Department" value={data.governmentDepartment} />
          <FieldDisplayBox label="Local Body Type" value={data.localBodyType} />

          <FieldDisplayBox label="Grievance Type" value={data.grievanceType} />
          <FieldDisplayBox label="Grievance Sub Type" value={data.grievanceSubType} />

          <FieldDisplayBox label="District" value={data.district} />
          <FieldDisplayBox label="Sub Department" value={data.subDepartment} />

          <FieldDisplayBox label="Ward" value={data.ward} />
          <FieldDisplayBox label="Municipality Ward" value={data.municipalityWard} />

          <FieldDisplayBox label="Block" value={data.block} />
          <FieldDisplayBox label="Taluk" value={data.taluk} />

          <FieldDisplayBox label="Revenue Division" value={data.revenueDivision} />
          <FieldDisplayBox label="Firka" value={data.firka} />

          <FieldDisplayBox label="Street Name" value={data.streetName} />
          <FieldDisplayBox label="Door Number" value={data.doorNumber} />

          <FieldDisplayBox label="Responsible Officer" value={data.responsibleOfficer} isFullWidth />

          <FieldDisplayBox label="Fisheries Region" value={data.fisheriesRegion} />
          <FieldDisplayBox label="Fisheries Division" value={data.fisheriesDivision} />

          <FieldDisplayBox label="Reason for Redirection" value={data.reasonForRedirection} isFullWidth isMultiline />
        </div>
      </div>

      {/* =========================================================================
          3. COMMUNICATION ADDRESS
          ========================================================================= */}
      <div className="portal-sub-section">
        <div className="portal-sub-section-header">
          <span className="portal-section-badge">3</span>
          <h5 className="portal-section-title">COMMUNICATION ADDRESS</h5>
        </div>

        <div className="full-details-form-grid">
          <FieldDisplayBox 
            label="Communication Address Same as Petitioner Address" 
            value={data.communicationAddressSame} 
            isFullWidth
          />
          <FieldDisplayBox 
            label="Communication Address" 
            value={data.communicationAddress} 
            isFullWidth 
            isMultiline
          />
        </div>
      </div>

      {/* =========================================================================
          4. GRIEVANCE STATUS
          ========================================================================= */}
      <div className="portal-sub-section">
        <div className="portal-sub-section-header">
          <span className="portal-section-badge">4</span>
          <h5 className="portal-section-title">GRIEVANCE STATUS</h5>
        </div>

        <div className="full-details-form-grid">
          <FieldDisplayBox label="Due Date" value={data.dueDate} />
          <FieldDisplayBox label="Status" value={data.status} />

          <FieldDisplayBox label="Source Code" value={data.sourceCode} />
          <FieldDisplayBox label="Grievance ID" value={data.grievanceId} />

          <FieldDisplayBox label="Priority" value={data.priority} />
          <FieldDisplayBox label="Call Disposition" value={data.callDisposition} />

          <FieldDisplayBox label="Is WhatsApp Appeal" value={data.isWhatsappAppeal} />
          <FieldDisplayBox label="Is WhatsApp Tracking" value={data.isWhatsappTracking} />

          <FieldDisplayBox label="Is WhatsApp Receipt" value={data.isWhatsappReceipt} />
        </div>
      </div>

      {/* =========================================================================
          5. EX-ARMY PETITION DETAILS
          ========================================================================= */}
      <div className="portal-sub-section">
        <div className="portal-sub-section-header">
          <span className="portal-section-badge">5</span>
          <h5 className="portal-section-title">EX-ARMY PETITION DETAILS</h5>
        </div>

        <div className="full-details-form-grid">
          <FieldDisplayBox label="Relationship with Ex-Servicemen" value={data.relationshipWithExServicemen} />
        </div>
      </div>

    </div>
  );
}
