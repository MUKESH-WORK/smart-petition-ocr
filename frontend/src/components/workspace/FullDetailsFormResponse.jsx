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
          I) .Petitioner/மனுதாரர்
          ========================================================================= */}
      <div className="portal-sub-section">
        <div className="portal-sub-section-header">
          <span className="portal-section-badge">I</span>
          <h5 className="portal-section-title">.Petitioner/மனுதாரர்</h5>
        </div>

        <div className="full-details-form-grid">
          {/* Row 1: Left: 1.Name/பெயர்*, Right: 2.Email/மின்னஞ்சல் */}
          <FieldDisplayBox label="1.Name/பெயர்*" value={data.petitionerName} />
          <FieldDisplayBox label="2.Email/மின்னஞ்சல்" value={data.email} />

          {/* Row 2: Left: 3.Phone/தொலைபேசி*, Right: 4 .Is this your own number/இது தங்களது கைப்பேசி எண்ணா(yes or no) */}
          <FieldDisplayBox label="3.Phone/தொலைபேசி*" value={data.phoneNumber} />
          <FieldDisplayBox label="4 .Is this your own number/இது தங்களது கைப்பேசி எண்ணா(yes or no)" value={data.isOwnNumber} />

          {/* Row 3: Left: 5.Alternate Phone Number/மாற்று தொலைபேசி எண், Right: 6.Address* */}
          <FieldDisplayBox label="5.Alternate Phone Number/மாற்று தொலைபேசி எண்" value={data.alternatePhone} />
          <FieldDisplayBox label="6.Address*" value={data.address} isMultiline />

          {/* Row 4: Left: 7.Please enter your gender*, Right: 8.Are You a Differently Abled Person*(yes/no/-None-) */}
          <FieldDisplayBox label="7.Please enter your gender*" value={data.gender} />
          <FieldDisplayBox label="8.Are You a Differently Abled Person*(yes/no/-None-)" value={data.differentlyAbled} />

          {/* Row 5: Left: 9.சமூகம்/தனிப்பட்ட குறை*(Public/personal) */}
          <FieldDisplayBox label="9.சமூகம்/தனிப்பட்ட குறை*(Public/personal)" value={data.petitionerCategory} />
        </div>
      </div>

      {/* =========================================================================
          II) Grievance Details
          ========================================================================= */}
      <div className="portal-sub-section">
        <div className="portal-sub-section-header">
          <span className="portal-section-badge">II</span>
          <h5 className="portal-section-title"> Grievance Details</h5>
        </div>

        <div className="full-details-form-grid">
          {/* Row 1: Left: 10 .Description *, Right: 12.Grievance Source/குறைக்கான ஆதாரம்* */}
          <FieldDisplayBox label="10 .Description *" value={data.description} isMultiline />
          <FieldDisplayBox label="12.Grievance Source/குறைக்கான ஆதாரம்*" value={data.grievanceSource} />

          {/* Row 2: Left: 13.Ref Number, Right: 14. Government Department / குறை தொடர்புடைய அரசு துறை* */}
          <FieldDisplayBox label="13.Ref Number" value={data.referenceNumber} />
          <FieldDisplayBox label="14. Government Department / குறை தொடர்புடைய அரசு துறை*" value={data.governmentDepartment} />

          {/* Row 3: Left: 15 .Local Body Type*, Right: 16 .Grievance Type/குறையின் வகை* */}
          <FieldDisplayBox label="15 .Local Body Type*" value={data.localBodyType} />
          <FieldDisplayBox label="16 .Grievance Type/குறையின் வகை*" value={data.grievanceType} />

          {/* Row 4: Left: 17 .Grievance SubType / குறையின்துணை வகை*, Right: 18.District/ மாவட்டம்* */}
          <FieldDisplayBox label="17 .Grievance SubType / குறையின்துணை வகை*" value={data.grievanceSubType} />
          <FieldDisplayBox label="18.District/ மாவட்டம்*" value={data.district} />

          {/* Row 5: Left: 19.Sub Department/குறை தொடர்புடைய துணைத்துறை*, Right: 20.Ward/வார்டு */}
          <FieldDisplayBox label="19.Sub Department/குறை தொடர்புடைய துணைத்துறை*" value={data.subDepartment} />
          <FieldDisplayBox label="20.Ward/வார்டு" value={data.ward} />

          {/* Row 6: Left: 21 .Municipality Ward/நகராட்சி வார்டு, Right: 22.Block/வட்டாரம்* */}
          <FieldDisplayBox label="21 .Municipality Ward/நகராட்சி வார்டு" value={data.municipalityWard} />
          <FieldDisplayBox label="22.Block/வட்டாரம்*" value={data.block} />

          {/* Row 7: Left: 23.Taluk/வட்டம், Right: 24 .Revenue Division/உட்கோட்டம்* */}
          <FieldDisplayBox label="23.Taluk/வட்டம்" value={data.taluk} />
          <FieldDisplayBox label="24 .Revenue Division/உட்கோட்டம்*" value={data.revenueDivision} />

          {/* Row 8: Left: 25 .Firka/ குறுவட்டம், Right: 26 .Street Name/தெருவின் பெயர் */}
          <FieldDisplayBox label="25 .Firka/ குறுவட்டம்" value={data.firka} />
          <FieldDisplayBox label="26 .Street Name/தெருவின் பெயர்" value={data.streetName} />

          {/* Row 9: Left: 27.Door No/கதவு எண், Right: 28.Responsible Officer/பொறுப்பு அதிகாரி* */}
          <FieldDisplayBox label="27.Door No/கதவு எண்" value={data.doorNumber} />
          <FieldDisplayBox label="28.Responsible Officer/பொறுப்பு அதிகாரி*" value={data.responsibleOfficer} />

          {/* Row 10: Left: 29.Fisheries Region, Right: 30 .Fisheries Division * */}
          <FieldDisplayBox label="29.Fisheries Region" value={data.fisheriesRegion} />
          <FieldDisplayBox label="30 .Fisheries Division *" value={data.fisheriesDivision} />

          {/* Row 11: Left: 31.Reason for Redirection */}
          <FieldDisplayBox label="31.Reason for Redirection" value={data.reasonForRedirection} isMultiline />
        </div>
      </div>

      {/* =========================================================================
          III) Communication Address
          ========================================================================= */}
      <div className="portal-sub-section">
        <div className="portal-sub-section-header">
          <span className="portal-section-badge">III</span>
          <h5 className="portal-section-title"> Communication Address</h5>
        </div>

        <div className="full-details-form-grid">
          {/* 32.Select if different from above/மேலே உள்ள முகவரியில் தங்கவில்லை என்றால்(yes/no) */}
          <FieldDisplayBox
            label="32.Select if different from above/மேலே உள்ள முகவரியில் தங்கவில்லை என்றால்(yes/no)"
            value={data.communicationAddressSame}
            isFullWidth
          />
        </div>
      </div>

      {/* =========================================================================
          Grievance Status/குறையின் நிலை
          ========================================================================= */}
      <div className="portal-sub-section">
        <div className="portal-sub-section-header">
          <span className="portal-section-badge">IV</span>
          <h5 className="portal-section-title">Grievance Status/குறையின் நிலை</h5>
        </div>

        <div className="full-details-form-grid">
          {/* Row 1: Left: 33. Due Date, Right: 35. Status */}
          <FieldDisplayBox label="33.Due Date/தீர்வு நாள் dd MMM yyyy hh:mm" value={data.dueDate} />
          <FieldDisplayBox label="35. Status */நிலை*" value={data.status} />

          {/* Row 2: Left: 36 .Source Code, Right: 37.Grievance ID-TN/AHFISH/ERD/P/{Mode}/31AUG26/g */}
          <FieldDisplayBox label="36 .Source Code" value={data.sourceCode} />
          <FieldDisplayBox label="37.Grievance ID-TN/AHFISH/ERD/P/{Mode}/31AUG26/g" value={data.grievanceId} />

          {/* Row 3: Left: 38.Priority, Right: 39. Call Disposition */}
          <FieldDisplayBox label="38.Priority" value={data.priority} />
          <FieldDisplayBox label="39. Call Disposition" value={data.callDisposition} />

          {/* Row 4: Left: 40.Is Whatsapp Appeal (yes/no), Right: 41.Is Whatsapp Tracking (yes/no) */}
          <FieldDisplayBox label="40.Is Whatsapp Appeal (yes/no)" value={data.isWhatsappAppeal} />
          <FieldDisplayBox label="41.Is Whatsapp Tracking (yes/no)" value={data.isWhatsappTracking} />

          {/* Row 5: Left: 42.Is Whatsapp Receipt (yes/no), Right: 43 .Ex-Army Petition Details Relationship with Ex-servicemen(yes/no) */}
          <FieldDisplayBox label="42.Is Whatsapp Receipt (yes/no)" value={data.isWhatsappReceipt} />
          <FieldDisplayBox label="43 .Ex-Army Petition Details Relationship with Ex-servicemen(yes/no)" value={data.relationshipWithExServicemen} />
        </div>
      </div>

    </div>
  );
}
