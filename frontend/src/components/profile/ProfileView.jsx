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
  Check,
  Pencil,
  X,
  Lock,
  AlertCircle
} from 'lucide-react';
import { updateMyProfile } from '../../services/apiService';
import './ProfileView.css';

function resolveInitialProfile(p) {
  let stored = {};
  try {
    const raw = localStorage.getItem('officer_profile') || localStorage.getItem('tn_gdp_officer_profile');
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

  const nameTamil = p?.nameTamil || p?.name_tamil || stored.nameTamil || stored.name_tamil || '';

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
    nameTamil,
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
  officerProfile,
  onSaveProfile,
  isAdmin = false,
  loginRole,
  currentLanguage
}) {
  const [initialData, setInitialData] = useState(() => resolveInitialProfile(officerProfile));
  const [formData, setFormData] = useState(() => resolveInitialProfile(officerProfile));
  const [isEditing, setIsEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState(null);

  // Synchronize when officerProfile prop updates externally
  useEffect(() => {
    if (officerProfile) {
      const resolved = resolveInitialProfile(officerProfile);
      setInitialData(resolved);
      if (!isEditing) {
        setFormData(resolved);
      }
    }
  }, [officerProfile, isEditing]);

  const handleStartEdit = () => {
    setFormData({ ...initialData });
    setFeedback(null);
    setIsEditing(true);
  };

  const handleCancelEdit = () => {
    setFormData({ ...initialData });
    setFeedback(null);
    setIsEditing(false);
  };

  const handleSave = async (e) => {
    if (e) e.preventDefault();
    setFeedback(null);

    // Validation
    if (!formData.fullName.trim()) {
      setFeedback({ type: 'error', message: 'Full name is required.' });
      return;
    }
    if (formData.email && !formData.email.includes('@')) {
      setFeedback({ type: 'error', message: 'Please enter a valid email address.' });
      return;
    }

    try {
      setSaving(true);
      const updated = {
        ...formData,
        name: formData.fullName.trim(),
        fullName: formData.fullName.trim(),
        nameTamil: formData.nameTamil ? formData.nameTamil.trim() : '',
        name_tamil: formData.nameTamil ? formData.nameTamil.trim() : '',
        phone: formData.phone.trim(),
        mobile: formData.phone.trim(),
        email: formData.email.trim(),
        department: formData.department.trim()
      };

      if (onSaveProfile) {
        await onSaveProfile(updated);
      } else {
        await updateMyProfile({
          name: updated.fullName,
          name_tamil: updated.nameTamil,
          mobile: updated.phone,
          email: updated.email,
          department: updated.department
        });
        localStorage.setItem('officer_profile', JSON.stringify(updated));
        localStorage.setItem('tn_gdp_officer_profile', JSON.stringify(updated));
      }

      setInitialData(updated);
      setFormData(updated);
      setIsEditing(false);
      setFeedback({ type: 'success', message: 'User profile data saved to database successfully.' });
    } catch (err) {
      console.error('Failed to update profile:', err);
      setFeedback({ type: 'error', message: err.message || 'Failed to save profile changes.' });
    } finally {
      setSaving(false);
    }
  };

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
              Official credentials, contact information, and departmental assignment.
            </p>
          </div>

          <div className="profile-header-actions">
            {isAdmin ? (
              !isEditing ? (
                <button
                  type="button"
                  className="profile-edit-btn"
                  onClick={handleStartEdit}
                  title="Edit user data (Admin only)"
                >
                  <Pencil size={15} />
                  <span>Edit User Data</span>
                </button>
              ) : (
                <div className="profile-editing-actions">
                  <button
                    type="button"
                    className="profile-cancel-btn"
                    onClick={handleCancelEdit}
                    disabled={saving}
                  >
                    <X size={15} />
                    <span>Cancel</span>
                  </button>
                  <button
                    type="button"
                    className="profile-save-btn"
                    onClick={handleSave}
                    disabled={saving}
                  >
                    {saving ? (
                      <span>Saving...</span>
                    ) : (
                      <>
                        <Check size={15} />
                        <span>Save Changes</span>
                      </>
                    )}
                  </button>
                </div>
              )
            ) : (
              <span className="restricted-badge" title="Only administrators can edit user profiles">
                <Lock size={12} />
                <span>View Only</span>
              </span>
            )}
          </div>
        </header>

        {/* Feedback Alert */}
        {feedback && (
          <div className={`profile-feedback-banner ${feedback.type}`}>
            {feedback.type === 'error' ? <AlertCircle size={16} /> : <Check size={16} />}
            <span>{feedback.message}</span>
            <button
              type="button"
              className="feedback-dismiss"
              onClick={() => setFeedback(null)}
            >
              <X size={14} />
            </button>
          </div>
        )}

        {/* Profile Details Sections */}
        <form onSubmit={handleSave} className="profile-cards-grid">

          {/* Card 1: Officer Information (User Data - Editable) */}
          <section className="profile-card">
            <div className="profile-card-header">
              <div className="profile-card-title-group">
                <UserCheck size={18} className="card-header-icon" />
                <h3 className="profile-card-title">User Data</h3>
              </div>
              <span className="profile-editable-indicator">
                {isEditing ? (
                  <span className="mode-pill editable-mode">Editing Enabled</span>
                ) : isAdmin ? (
                  <span className="mode-pill view-mode">Click Edit to modify</span>
                ) : (
                  <span className="mode-pill view-mode">Read Only</span>
                )}
              </span>
            </div>

            <div className="profile-card-body">
              <div className="profile-field-grid">

                <div className="profile-field-item">
                  <label htmlFor="field-fullName" className="field-label">
                    Full Name (English) *
                  </label>
                  <div className={`field-value-group ${isEditing && isAdmin ? 'is-editable' : 'is-readonly'}`}>
                    <User size={15} className="field-icon" />
                    <input
                      id="field-fullName"
                      type="text"
                      className="field-input highlight"
                      value={formData.fullName}
                      onChange={(e) => setFormData({ ...formData, fullName: e.target.value })}
                      readOnly={!isEditing || !isAdmin}
                      required
                      placeholder="Officer Full Name"
                    />
                  </div>
                </div>

                <div className="profile-field-item">
                  <label htmlFor="field-nameTamil" className="field-label">
                    Full Name (Tamil - optional)
                  </label>
                  <div className={`field-value-group ${isEditing && isAdmin ? 'is-editable' : 'is-readonly'}`}>
                    <User size={15} className="field-icon" />
                    <input
                      id="field-nameTamil"
                      type="text"
                      className="field-input field-input-tamil"
                      value={formData.nameTamil || ''}
                      onChange={(e) => setFormData({ ...formData, nameTamil: e.target.value })}
                      readOnly={!isEditing || !isAdmin}
                      placeholder="எ.கா. சு. இராமநாதன்"
                    />
                  </div>
                </div>

                <div className="profile-field-item">
                  <label htmlFor="field-email" className="field-label">Official Email *</label>
                  <div className={`field-value-group ${isEditing && isAdmin ? 'is-editable' : 'is-readonly'}`}>
                    <Mail size={15} className="field-icon" />
                    <input
                      id="field-email"
                      type="email"
                      className="field-input"
                      value={formData.email}
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                      readOnly={!isEditing || !isAdmin}
                      required
                      placeholder="officer@tn.gov.in"
                    />
                  </div>
                </div>

                <div className="profile-field-item">
                  <label htmlFor="field-phone" className="field-label">Official Mobile / Phone Number</label>
                  <div className={`field-value-group ${isEditing && isAdmin ? 'is-editable' : 'is-readonly'}`}>
                    <Phone size={15} className="field-icon" />
                    <input
                      id="field-phone"
                      type="tel"
                      className="field-input"
                      value={formData.phone}
                      onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                      readOnly={!isEditing || !isAdmin}
                      placeholder="+91 94431 00000"
                    />
                  </div>
                </div>

                <div className="profile-field-item">
                  <label htmlFor="field-department" className="field-label">Department / Unit</label>
                  <div className={`field-value-group ${isEditing && isAdmin ? 'is-editable' : 'is-readonly'}`}>
                    <Building2 size={15} className="field-icon" />
                    <input
                      id="field-department"
                      type="text"
                      className="field-input"
                      value={formData.department}
                      onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                      readOnly={!isEditing || !isAdmin}
                      placeholder="e.g. Revenue Administration"
                    />
                  </div>
                </div>

                <div className="profile-field-item">
                  <label htmlFor="field-designation" className="field-label">Designation</label>
                  <div className={`field-value-group ${isEditing && isAdmin ? 'is-editable' : 'is-readonly'}`}>
                    <Briefcase size={15} className="field-icon" />
                    <input
                      id="field-designation"
                      type="text"
                      className="field-input"
                      value={formData.designation}
                      onChange={(e) => setFormData({ ...formData, designation: e.target.value })}
                      readOnly={!isEditing || !isAdmin}
                      placeholder="e.g. Revenue Officer"
                    />
                  </div>
                </div>

              </div>
            </div>
          </section>

          {/* Card 2: System-Restricted Administrative Assignment (Locked) */}
          <section className="profile-card restricted-card">
            <div className="profile-card-header">
              <div className="profile-card-title-group">
                <ShieldCheck size={18} className="card-header-icon" />
                <h3 className="profile-card-title">System & Administrative Assignment</h3>
              </div>
              <span className="restricted-badge" title="Managed solely by District Administration">
                <Lock size={12} />
                <span>System Restricted</span>
              </span>
            </div>

            <div className="profile-card-body">
              <div className="profile-field-grid">

                <div className="profile-field-item">
                  <label htmlFor="field-officerId" className="field-label">Officer ID</label>
                  <div className="field-value-group is-restricted">
                    <BadgeCheck size={15} className="field-icon" />
                    <input
                      id="field-officerId"
                      type="text"
                      className="field-input code-font"
                      value={formData.officerId}
                      readOnly
                    />
                    <Lock size={13} className="lock-icon" />
                  </div>
                </div>

                <div className="profile-field-item">
                  <label htmlFor="field-role" className="field-label">Access Role</label>
                  <div className="field-value-group is-restricted">
                    <ShieldCheck size={15} className="field-icon" />
                    <input
                      id="field-role"
                      type="text"
                      className="field-input"
                      value={formData.role}
                      readOnly
                    />
                    <Lock size={13} className="lock-icon" />
                  </div>
                </div>

                <div className="profile-field-item span-full">
                  <label htmlFor="field-assignedOffice" className="field-label">Assigned Department / Office</label>
                  <div className="field-value-group is-restricted">
                    <Building2 size={15} className="field-icon" />
                    <input
                      id="field-assignedOffice"
                      type="text"
                      className="field-input"
                      value={formData.assignedOffice}
                      readOnly
                    />
                    <Lock size={13} className="lock-icon" />
                  </div>
                </div>

              </div>
            </div>
          </section>

        </form>

      </div>
    </div>
  );
}

