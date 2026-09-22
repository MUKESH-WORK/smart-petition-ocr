# Security Policy

The GDP Assistant team takes the security of our platform and the protection of citizen data extremely seriously. This document outlines our security policies, supported versions, and the procedure for disclosing potential vulnerabilities.

---

## 1. Supported Versions

We provide security updates and patches for the following versions:

| Version | Supported          | Security Maintenance Status |
| ------- | ------------------ | --------------------------- |
| 1.x     | :white_check_mark: | Active (Current Stable)     |
| < 1.0   | :x:                | Deprecated                  |

---

## 2. Core Security & Privacy Commitments

GDP Assistant processes citizen grievance petitions for revenue administration. Because citizen documents contain sensitive personal information, the following core constraints are enforced across the entire codebase:

1. **Aadhaar & PII Masking**:
   - Aadhaar numbers (`\b\d{4}[ -]?\d{4}[ -]?\d{4}\b`) must be redacted at intake into masked format (`XXXX-XXXX-1234`) prior to database persistence or vector embedding.
   - Citizen phone numbers, addresses, and family details must never be output to standard logging streams (`stdout`/`stderr`) or public error dumps.
2. **Horizontal & Vertical Privilege Separation**:
   - Administrative endpoints (`/api/v1/admin/*`) require verified Officer Session Authentication (`X-Officer-Id` and Bearer JWT) with role validation (`is_admin: true`).
   - Regular department users cannot create or modify system-wide taxonomy mappings, officer accounts, or administrative hierarchy definitions.
3. **Database Security**:
   - In offline/local mode, SQLite databases (`dro_admin.db`, `dro_user.db`) must reside in restricted directories (`temp_cache/`) excluded from Git tracking via `.gitignore`.
   - In enterprise production mode, PostgreSQL 16 connections must use SSL (`sslmode=require`) with non-root roles.
4. **Air-Gapped & Offline Safety**:
   - OCR, vector embedding generation, and entity parsing are designed to run fully offline without exfiltrating document images or text chunks to third-party public cloud APIs.
5. **Role-Based Access Control (RBAC)**:
   - Profile editing is restricted to users with `is_admin: true` (District Administrator role).
   - Non-admin users (Department Users, Field Officers) see all profile data in read-only mode.
   - Taxonomy and hierarchy management endpoints require admin role verification.
6. **Dynamic Translation Security**:
   - Translation requests are processed server-side via the LLM engine; no citizen PII should be included in translation payloads.
   - Translation responses are cached in-memory (LRU) and never persisted to disk or logs.

---

## 3. Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

If you discover a potential vulnerability, data leak, privilege escalation, or security weakness:

1. **Email Us Privately**: Send full technical details, proof-of-concept steps, and affected components to:
   **`security@gdp-assistant.org`** (or contact the repository maintainers directly).
2. **Information to Include**:
   - Description of the issue (e.g., SQL injection, unauthorized access, PII disclosure, broken authorization).
   - Step-by-step instructions to reproduce the vulnerability.
   - Any sample files or API payloads used (please use mock/synthetic petitions, **never** real citizen data).
   - Potential impact of the vulnerability.

---

## 4. Response Timeline & Disclosure Process

- **Acknowledgment**: Within **48 hours**, we will confirm receipt of your report and begin verification.
- **Triage & Fix**: We will collaborate with you to develop and test a fix in a private branch.
- **Release**: A patched release will be issued promptly.
- **Credit**: We will publicly acknowledge your contribution in our security advisories and release notes (unless you prefer to remain anonymous).

---

## 5. Security Best Practices for Operators

When deploying GDP Assistant in a District Collectorate or administrative office:
- Keep `.env` secure and restrict file permissions (`chmod 600 .env`).
- Never disable `X-Officer-Id` or JWT authentication in production.
- Use the provided `scripts/manage_db.py` tool to create password-protected or checksum-verified backups when migrating databases between workstations.
