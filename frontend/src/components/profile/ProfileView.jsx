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

export default function ProfileView({
  officerProfile,
  onSaveProfile,
  onNotify
}) {
  const [formData, setFormData] = useState(() => ({
    fullName: officerProfile?.fullName || 'S. Ramanathan',
    designation: officerProfile?.designation || 'Tahsildar',
    department: officerProfile?.department || 'Grievance Cell',
    officerId: officerProfile?.officerId || 'TN-GRIEV-2024-8842',
    email: officerProfile?.email || 's.ramanathan@tn.gov.in',
    phone: officerProfile?.phone || '+91 44 2530 1000',
    role: officerProfile?.role || 'Tahsildar',
    assignedOffice: officerProfile?.assignedOffice || 'Revenue & Disaster Management Department, Chennai District',
    accessLevel: officerProfile?.accessLevel || 'Level 2 Administrative Access (Grievance Pre-Processing & Approval)'
  }));

  // Synchronize when officerProfile prop updates externally
  useEffect(() => {
    if (officerProfile) {
      setFormData({
        fullName: officerProfile.fullName || '',
        designation: officerProfile.designation || '',
        department: officerProfile.department || '',
        officerId: officerProfile.officerId || '',
        email: officerProfile.email || '',
        phone: officerProfile.phone || '',
        role: officerProfile.role || '',
        assignedOffice: officerProfile.assignedOffice || '',
        accessLevel: officerProfile.accessLevel || ''
      });
    }
  }, [officerProfile]);

  // Check if user has made any changes compared to current saved profile
  const hasUnsavedChanges = Object.keys(formData).some((key) => {
    return formData[key] !== (officerProfile?.[key] || '');
  });

  const handleChange = (field, value) => {
    setFormData((prev) => ({
      ...prev,
      [field]: value
    }));
  };

  const handleSave = (e) => {
    e.preventDefault();
    if (onSaveProfile) {
      onSaveProfile(formData);
    }
    if (onNotify) {
      onNotify('Officer profile updated successfully');
    }
  };

  return (
    <div className="profile-page" role="region" aria-label="Officer Profile">
      <form className="profile-container" onSubmit={handleSave}>
        
        {/* Page Header */}
        <header className="profile-header">
          <div className="profile-header-left">
            <div className="profile-title-row">
              <User size={22} className="profile-header-icon" />
              <h2 className="profile-title">My Profile</h2>
            </div>
            <p className="profile-subtitle">
              View and manage your officer profile information.
            </p>
          </div>

          {/* Show Save Changes button ONLY IF user has made changes */}
          {hasUnsavedChanges && (
            <div className="profile-header-actions">
              <button 
                type="submit" 
                className="profile-save-btn"
                title="Save updated profile information"
              >
                <Check size={16} />
                <span>Save Changes</span>
              </button>
            </div>
          )}
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
                      onChange={(e) => handleChange('fullName', e.target.value)}
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
                      onChange={(e) => handleChange('designation', e.target.value)}
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
                      onChange={(e) => handleChange('department', e.target.value)}
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
                      onChange={(e) => handleChange('officerId', e.target.value)}
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
                      onChange={(e) => handleChange('email', e.target.value)}
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
                      onChange={(e) => handleChange('phone', e.target.value)}
                    />
                  </div>
                </div>

              </div>
            </div>
          </section>

          {/* Card 2: Role & Access */}
          <section className="profile-card">
            <div className="profile-card-header">
              <div className="profile-card-title-group">
                <ShieldCheck size={18} className="card-header-icon" />
                <h3 className="profile-card-title">Role & Access</h3>
              </div>
            </div>

            <div className="profile-card-body">
              <div className="profile-field-grid">
                
                <div className="profile-field-item">
                  <label htmlFor="field-role" className="field-label">Role</label>
                  <div className="field-value-group">
                    <Briefcase size={15} className="field-icon" />
                    <input
                      id="field-role"
                      type="text"
                      className="field-input"
                      value={formData.role}
                      onChange={(e) => handleChange('role', e.target.value)}
                    />
                  </div>
                </div>

                <div className="profile-field-item span-full">
                  <label htmlFor="field-assignedOffice" className="field-label">Assigned Department / Office</label>
                  <div className="field-value-group">
                    <Building2 size={15} className="field-icon" />
                    <input
                      id="field-assignedOffice"
                      type="text"
                      className="field-input"
                      value={formData.assignedOffice}
                      onChange={(e) => handleChange('assignedOffice', e.target.value)}
                    />
                  </div>
                </div>

                <div className="profile-field-item span-full">
                  <label htmlFor="field-accessLevel" className="field-label">Access Level & Permissions</label>
                  <div className="field-value-group">
                    <ShieldCheck size={15} className="field-icon" />
                    <input
                      id="field-accessLevel"
                      type="text"
                      className="field-input badge-access"
                      value={formData.accessLevel}
                      onChange={(e) => handleChange('accessLevel', e.target.value)}
                    />
                  </div>
                </div>

              </div>
            </div>
          </section>

        </div>

      </form>
    </div>
  );
}
