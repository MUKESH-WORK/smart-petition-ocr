# Implementation Plan - Admin Password Management & Administrative Hierarchy Redesign with RAG Vector Storage

## Overview
Implement two core capabilities requested by the user:
1. **Admin Password Management**:
   - Only Admin can change/reset passwords (both the admin account and all departmental user accounts). Standard users cannot change passwords.
   - Enforce password hashing, systematic validation, and login verification.
2. **Administrative Hierarchy Redesign & RAG Vector Integration**:
   - Re-model the administrative hierarchy to match the official structure from the user-provided images:
     - **Erode Division** (Erode, Perundurai, Modakkurichi, Kodumudi)
     - **Gobichettipalayam Division** (Gobichettipalayam, Sathyamangalam, Bhavani, Anthiyur, Thalavadi)
     - Each Taluk contains its **Key Internal Sub-Departments**, **Available Firkas**, and **Local Body Classification**.
   - Redesign the UI: Replace the clumsy flat local-preview modal with a professional, interactive Hierarchy Management interface (Division -> Taluk Cards -> Firkas & Sub-departments).
   - Persist all hierarchy records directly to the Admin Database (`master_locations`) and compute 384-dimensional vector embeddings so the AI RAG grievance routing engine operates on this exact hierarchy.

---

## User Review Required

### Exact Administrative Hierarchy (Directly from User Images - NOT from JSON)

#### 1. Erode Division
- **Taluk: Erode**
  - Key Internal Sub-Departments: `Revenue, Civil Supplies, Land Records`
  - Available Firkas: `East, West, North, South`
  - Local Body Classification: `Erode City Municipal Corporation`
- **Taluk: Perundurai**
  - Key Internal Sub-Departments: `Revenue Admin, SIPCOT Industrial Desk`
  - Available Firkas: `Perundurai, Kanjikoil, Thingalore, Chennimalai, Vellodu`
  - Local Body Classification: `Rural Town Panchayats`
- **Taluk: Modakkurichi**
  - Key Internal Sub-Departments: `Revenue Administration`
  - Available Firkas: `Arachalur, Poondurai, Modakkurichi`
  - Local Body Classification: `Rural Town Panchayats`
- **Taluk: Kodumudi**
  - Key Internal Sub-Departments: `Revenue Administration`
  - Available Firkas: `Kodumudi, Kilambadi, Sivagiri`
  - Local Body Classification: `Rural Town Panchayats`

#### 2. Gobichettipalayam Division
- **Taluk: Gobichettipalayam**
  - Key Internal Sub-Departments: `Revenue Admin, Agricultural Extension`
  - Available Firkas: `Gobichettipalayam, Vaniputhur, Siruvalur, Kugalur, Kasipalayam`
  - Local Body Classification: `Gobichettipalayam Municipality`
- **Taluk: Sathyamangalam**
  - Key Internal Sub-Departments: `Revenue, Forest Range, Tribal Welfare`
  - Available Firkas: `Sathyamangalam, Arasur, Gudhiyalathur, Bhavanisagar, Punjai Puliyampatti`
  - Local Body Classification: `Sathyamangalam & Punjai Puliyampatti Municipalities`
- **Taluk: Bhavani**
  - Key Internal Sub-Departments: `Revenue Administration`
  - Available Firkas: `Bhavani, Kurichi, Kavindapadi`
  - Local Body Classification: `Bhavani Municipality`
- **Taluk: Anthiyur**
  - Key Internal Sub-Departments: `Revenue Administration`
  - Available Firkas: `Anthiyur, Ammapettai, Athani, Bargur`
  - Local Body Classification: `Rural Town Panchayats`
- **Taluk: Thalavadi**
  - Key Internal Sub-Departments: `Revenue, Hill Area Development Desk`
  - Available Firkas: `Thalavadi`
  - Local Body Classification: `Tribal Hill Panchayats`

### Card & Action Specifications
- **Taluk Name & Division header**
- **Sub-Departments badges** (e.g. `Revenue Admin`, `Agricultural Extension`, `Civil Supplies`)
- **Local Body Classification tag** (e.g. `Erode City Municipal Corporation`, `Bhavani Municipality`)
- **Available Firkas list tags**
- **Actions**: `"Edit Taluk"`, `"Add Firka"`, `"Remove"`
- All persisted to SQLite / PostgreSQL Admin DB (`master_locations`) with 384-dimensional RAG vector embeddings.

### Backend

#### 1. Models & Database Schema
- [backend/models/orm.py](file:///d:/GDP-Assisant/smart-petition-ocr/backend/models/orm.py):
  - Ensure `admin_users` has `password_hash` column.
  - Update `master_locations` table to support `sub_departments` column.
- [backend/models/database.py](file:///d:/GDP-Assisant/smart-petition-ocr/backend/models/database.py):
  - Ensure `sub_departments` column exists in `master_locations` in SQLite / Postgres.

#### 2. Password Management API
- [backend/app/routers/admin.py](file:///d:/GDP-Assisant/smart-petition-ocr/backend/app/routers/admin.py):
  - Add `POST /api/v1/admin/users/{user_id}/password`:
    - Enforce admin authentication (`is_admin: True` / `x-role: admin`).
    - Validate password minimum length (8 chars) and complexity.
    - Hash password using `hashlib.sha256` or `bcrypt` and store in `admin_users.password_hash`.
    - Log audit entry in `admin_activity_log`.
  - Update `POST /api/v1/admin/session/login`:
    - Verify password: if `password_hash` is set, verify incoming password against hash; if not set, compare against default `Govt@2024`.

#### 3. Administrative Hierarchy API & RAG Vector Sync
- [backend/app/routers/admin.py](file:///d:/GDP-Assisant/smart-petition-ocr/backend/app/routers/admin.py):
  - `GET /api/v1/admin/hierarchy`: Returns nested hierarchy structure (Divisions -> Taluks -> Sub-Departments, Firkas, Local Body).
  - `POST /api/v1/admin/hierarchy/taluk`: Create or update a Taluk's details (firkas, sub-departments, local body), update `master_locations`, and compute 384-d embeddings using `vector_store.encode()`.
  - `DELETE /api/v1/admin/hierarchy/taluk`: Delete Taluk or Firka and clean vector records.
- [backend/services/master_data_seeder.py](file:///d:/GDP-Assisant/smart-petition-ocr/backend/services/master_data_seeder.py):
  - Seed the exact 2 Divisions, 9 Taluks, and 28 Firkas with sub-departments and local body classifications from the images into `master_locations` with 384-d vector embeddings.

---

### Frontend

#### 4. Password Management in UserManagement & ProfileView
- [frontend/src/components/admin/UserManagement.jsx](file:///d:/GDP-Assisant/smart-petition-ocr/frontend/src/components/admin/UserManagement.jsx):
  - In `UserDialog`, add a dedicated "Change Password" section allowing Admin to reset/update password for the selected account (admin or user).
  - Includes password strength indicator, visibility toggle, confirmation validation, and API call to `/api/v1/admin/users/{user_id}/password`.
- [frontend/src/components/profile/ProfileView.jsx](file:///d:/GDP-Assisant/smart-petition-ocr/frontend/src/components/profile/ProfileView.jsx):
  - Only show active password change controls if user `isAdmin` is true.
  - For standard users, show an informative locked badge: *"Password modifications are restricted to the District Administrator."*

#### 5. Redesigned Administrative Hierarchy Management
- [frontend/src/components/admin/AdminHierarchyModal.jsx](file:///d:/GDP-Assisant/smart-petition-ocr/frontend/src/components/admin/AdminHierarchyModal.jsx) (NEW):
  - Beautiful, accessible, professional hierarchy management view matching `/ui-ux-pro-max` standards:
    - Tab / Switcher for **Erode Division** and **Gobichettipalayam Division**.
    - Summary badges: Total Taluks, Total Firkas, Local Bodies, AI Vector Status.
    - Responsive card grid of **Operational Taluks**:
      - Taluk Name & Division header
      - Sub-Departments badges (e.g. `Revenue Admin`, `Agricultural Extension`, `Civil Supplies`)
      - Local Body Classification tag (e.g. `Erode City Municipal Corporation`, `Bhavani Municipality`)
      - Available Firkas list tags
      - Actions: "Edit Taluk", "Add Firka", "Remove"
    - Modal form to Add / Edit Taluk:
      - Division selector
      - Taluk Name (English & Tamil)
      - Key Internal Sub-Departments (comma-separated or tags)
      - Local Body Classification selector
      - Available Firkas (tag input / comma-separated)
    - Directly saves to backend `/api/v1/admin/hierarchy/taluk`, updating DB and re-indexing RAG embeddings.
- [frontend/src/components/admin/AdminDashboard.jsx](file:///d:/GDP-Assisant/smart-petition-ocr/frontend/src/components/admin/AdminDashboard.jsx):
  - Replace the old local preview modal with `AdminHierarchyModal`.

---

## Verification Plan

### Automated & API Verification
1. Test Password Update API:
   - Change Admin password to `Admin@New2026` via API -> Login with new password -> verify 200 OK.
   - Change User password for `ramanathan@tn.gov.in` to `Raman@New2026` -> Login -> verify 200 OK.
2. Test Hierarchy & Vector Storage:
   - Query `GET /api/v1/admin/hierarchy` -> verify 2 divisions, 9 taluks, and all firkas match the images.
   - Query `master_locations` in Admin DB -> verify records have non-null 384-d `embedding` and `sub_departments`.
   - Test vector semantic search on firka and sub-department keywords.

### Manual / UI Verification
1. Open Admin Dashboard -> Click "Manage Hierarchy" -> Verify neat, structured Division & Taluk cards matching the user's images.
2. Edit a Taluk's firkas or sub-departments -> Click Save -> Verify live update in DB and RAG vector store.
3. Open User Management -> Select a user -> Change password -> Verify successful save.
4. Verify standard user ProfileView has password change locked.
