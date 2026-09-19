import React, { useState, useEffect } from 'react';
import {
  User,
  UserCheck,
  ShieldCheck,
  Mail,
  Phone,
  Building2,
  BadgeCheck,
  Briefcase,
  Check
} from 'lucide-react';
import './ProfileView.css';

function resolveInitialProfile(p) {
  let stored = {};
  try {
    const raw = localStorage.getItem('officer_profile');
    if (raw) stored = JSON.parse(raw);
  } catch {}

  const isAdm =
    p?.role === 'admin' ||
    p?.role === 'District Administrator' ||
    p?.isAdmin ||
    p?.is_admin ||
    stored.is_admin ||
    stored.isAdmin;

  const email =
    p?.email ||
    stored.email ||
    localStorage.getItem('officer_email') ||
    (isAdm ? 'collector.erode@tn.gov.in' : '');

  const phone =
    p?.phone ||
    p?.mobile ||
    stored.mobile ||
    stored.phone ||
    localStorage.getItem('officer_phone') ||
    (isAdm ? '+91 424 2262000' : '');

  const name =
    p?.fullName ||
    p?.name ||
    stored.name ||
    (isAdm ? 'Tmt. Raja Gopal Sunkara, I.A.S.' : 'Department Officer');

  const designation =
    p?.designation ||
    stored.designation ||
    (isAdm ? 'District Administrator' : 'Revenue Officer');

  const department =
    p?.department ||
    stored.department ||
    (isAdm ? 'District Administration / Collectorate' : 'Revenue Administration');

  const officerId =
    p?.officerId ||
    p?.id ||
    stored.id ||
    stored.officerId ||
    (isAdm ? 'ADM-ERODE-001' : 'OFF-USER-001');

  const role = isAdm ? 'District Administrator' : (p?.role || stored.role || 'Department User');
  const assignedOffice = p?.assignedOffice || 'Erode District Collectorate, Tamil Nadu';

  return {
    fullName: name,
    designation,
    department,
    officerId,
    email,
    phone,
    role,
    assignedOffice
  };
}

export default function ProfileView({
  officerProfile
}) {
  const [formData, setFormData] = useState(() => resolveInitialProfile(officerProfile));

  // Synchronize when officerProfile prop updates externally
  useEffect(() => {
    if (officerProfile) {
      setFormData(resolveInitialProfile(officerProfile));
    }
  }, [officerProfile]);

  return (
    <div className="profile-page" role="region" aria-label="Officer Profile">
      <div className="profile-container">

        {/* Page Header */}
        <header className="profile-header">
          <div className="profile-header-left">
            <div className="profile-title-row">
              <User size={22} className="profile-header-icon" />
              <h2 className="profile-title">Official Profile</h2>
            </div>
            <p className="profile-subtitle">
              Official credentials, contact information, and departmental assignment (Managed solely by District Administration).
            </p>
          </div>

          <div className="profile-header-actions">
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 12px',
                backgroundColor: '#f1f5f9',
                color: '#475569',
                borderRadius: '9999px',
                fontSize: '0.8rem',
                fontWeight: 600,
                border: '1px solid #cbd5e1'
              }}
            >
              <ShieldCheck size={16} style={{ color: '#047857' }} />
              <span>Admin-Managed Profile</span>
            </span>
          </div>
        </header>

        {/* Profile Details Sections */}
        <div className="profile-cards-grid">

          {/* Card 1: Officer Information */}
          <section className="profile-card">
            <div className="profile-card-header">
              <div className="profile-card-title-group">
                <UserCheck size={18} className="card-header-icon" />
                <h3 className="profile-card-title">Officer Information</h3>
              </div>
            </div>

            <div className="profile-card-body">
              <div className="profile-field-grid">

                <div className="profile-field-item">
                  <label htmlFor="field-fullName" className="field-label">Full Name</label>
                  <div className="field-value-group">
                    <User size={15} className="field-icon" />
                    <input
                      id="field-fullName"
                      type="text"
                      className="field-input highlight"
                      value={formData.fullName}
                      readOnly
                    />
                  </div>
                </div>

                <div className="profile-field-item">
                  <label htmlFor="field-designation" className="field-label">Designation</label>
                  <div className="field-value-group">
                    <Briefcase size={15} className="field-icon" />
                    <input
                      id="field-designation"
                      type="text"
                      className="field-input"
                      value={formData.designation}
                      readOnly
                    />
                  </div>
                </div>

                <div className="profile-field-item">
                  <label htmlFor="field-department" className="field-label">Department / Unit</label>
                  <div className="field-value-group">
                    <Building2 size={15} className="field-icon" />
                    <input
                      id="field-department"
                      type="text"
                      className="field-input"
                      value={formData.department}
                      readOnly
                    />
                  </div>
                </div>

                <div className="profile-field-item">
                  <label htmlFor="field-officerId" className="field-label">Officer ID</label>
                  <div className="field-value-group">
                    <BadgeCheck size={15} className="field-icon" />
                    <input
                      id="field-officerId"
                      type="text"
                      className="field-input code-font"
                      value={formData.officerId}
                      readOnly
                    />
                  </div>
                </div>

                <div className="profile-field-item">
                  <label htmlFor="field-email" className="field-label">Official Email</label>
                  <div className="field-value-group">
                    <Mail size={15} className="field-icon" />
                    <input
                      id="field-email"
                      type="email"
                      className="field-input"
                      value={formData.email}
                      readOnly
                      placeholder="officer@tn.gov.in"
                    />
                  </div>
                </div>

                <div className="profile-field-item">
                  <label htmlFor="field-phone" className="field-label">Official Phone Number</label>
                  <div className="field-value-group">
                    <Phone size={15} className="field-icon" />
                    <input
                      id="field-phone"
                      type="text"
                      className="field-input"
                      value={formData.phone}
                      readOnly
                      placeholder="+91 94431 00000"
                    />
                  </div>
                </div>

              </div>
            </div>
          </section>

          {/* Card 2: Assigned Office & Department */}
          <section className="profile-card">
            <div className="profile-card-header">
              <div className="profile-card-title-group">
                <Building2 size={18} className="card-header-icon" />
                <h3 className="profile-card-title">Assigned Office & Department</h3>
              </div>
            </div>

            <div className="profile-card-body">
              <div className="profile-field-grid">

                <div className="profile-field-item span-full">
                  <label htmlFor="field-assignedOffice" className="field-label">Assigned Department / Office</label>
                  <div className="field-value-group">
                    <Building2 size={15} className="field-icon" />
                    <input
                      id="field-assignedOffice"
                      type="text"
                      className="field-input"
                      value={formData.assignedOffice}
                      readOnly
                    />
                  </div>
                </div>

              </div>
            </div>
          </section>

        </div>

      </div>
    </div>
  );
}
