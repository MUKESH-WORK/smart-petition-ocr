import React, { useState } from 'react';
import { Copy, Check } from 'lucide-react';
import './Workspace.css';

function FieldCopyButton({ value }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = (e) => {
    e.stopPropagation();
    if (!value) return;
    navigator.clipboard.writeText(value);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  return (
    <button
      type="button"
      className={`field-inline-copy-btn ${copied ? 'copied' : ''}`}
      onClick={handleCopy}
      title="Copy field value"
      aria-label="Copy field value"
    >
      {copied ? (
        <>
          <Check size={12} className="copy-icon-check" />
          <span>Copied</span>
        </>
      ) : (
        <>
          <Copy size={12} />
          <span>Copy</span>
        </>
      )}
    </button>
  );
}

export default function FullDetailsFormResponse({ initialDetails }) {
  const data = {
    petitionerName: initialDetails?.petitionerName || 'R. Kumar',
    phoneNumber: initialDetails?.phoneNumber || '9876543210',
    address: initialDetails?.address || '14/2, Mariamman Kovil Street, ABC Village, Thingalur Firka, Perundurai Taluk, Erode - 638052',
    mainGrievance: initialDetails?.mainGrievance || 'Request for repair of damaged village link road with severe potholes for over 6 months.',
    location: initialDetails?.location || 'ABC Village, Perundurai Taluk, Erode District',
    referenceNumber: initialDetails?.referenceNumber || 'PET-2026-ERD-08492',
    suggestedDepartment: initialDetails?.suggestedDepartment || 'Rural Development / Road Maintenance',
    requestedAction: initialDetails?.requestedAction || 'Repair and resurface the damaged road.'
  };

  return (
    <div className="full-details-form-container">
      <div className="full-details-header-row">
        <h4 className="full-details-main-heading">FULL PETITION DETAILS</h4>
      </div>

      <div className="full-details-form-grid">
        
        {/* Row 1: Petitioner Name (Col 1) & Phone Number (Col 2) */}
        <div className="form-item-wrapper col-half">
          <label className="form-item-label">Petitioner Name</label>
          <div className="info-display-box">
            <span className="info-display-text">{data.petitionerName}</span>
            <FieldCopyButton value={data.petitionerName} />
          </div>
        </div>

        <div className="form-item-wrapper col-half">
          <label className="form-item-label">Phone Number</label>
          <div className="info-display-box">
            <span className="info-display-text">{data.phoneNumber}</span>
            <FieldCopyButton value={data.phoneNumber} />
          </div>
        </div>

        {/* Row 2: Address (Full Width) */}
        <div className="form-item-wrapper col-full">
          <label className="form-item-label">Address</label>
          <div className="info-display-box multiline-box">
            <span className="info-display-text">{data.address}</span>
            <FieldCopyButton value={data.address} />
          </div>
        </div>

        {/* Row 3: Main Grievance (Full Width) */}
        <div className="form-item-wrapper col-full">
          <label className="form-item-label">Main Grievance</label>
          <div className="info-display-box multiline-box">
            <span className="info-display-text">{data.mainGrievance}</span>
            <FieldCopyButton value={data.mainGrievance} />
          </div>
        </div>

        {/* Row 4: Location (Col 1) & Reference Number (Col 2) */}
        <div className="form-item-wrapper col-half">
          <label className="form-item-label">Location</label>
          <div className="info-display-box">
            <span className="info-display-text">{data.location}</span>
            <FieldCopyButton value={data.location} />
          </div>
        </div>

        <div className="form-item-wrapper col-half">
          <label className="form-item-label">Reference Number</label>
          <div className="info-display-box">
            <span className="info-display-text">{data.referenceNumber}</span>
            <FieldCopyButton value={data.referenceNumber} />
          </div>
        </div>

        {/* Row 5: Suggested Department (Full Width) */}
        <div className="form-item-wrapper col-full">
          <label className="form-item-label">Suggested Department</label>
          <div className="info-display-box">
            <span className="info-display-text">{data.suggestedDepartment}</span>
            <FieldCopyButton value={data.suggestedDepartment} />
          </div>
        </div>

        {/* Row 6: Requested Action (Full Width) */}
        <div className="form-item-wrapper col-full">
          <label className="form-item-label">Requested Action</label>
          <div className="info-display-box multiline-box">
            <span className="info-display-text">{data.requestedAction}</span>
            <FieldCopyButton value={data.requestedAction} />
          </div>
        </div>

      </div>
    </div>
  );
}
