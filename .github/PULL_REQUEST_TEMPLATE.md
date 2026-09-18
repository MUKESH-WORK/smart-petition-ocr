## Description

Please include a summary of the change, the problem it solves, and the relevant issue number (e.g. `Fixes #123`).

## Type of Change

- [ ] 🐛 Bug fix (non-breaking change fixing an issue)
- [ ] ✨ New feature (non-breaking change adding functionality)
- [ ] ⚡ Performance optimization
- [ ] 🛡️ Security / PII hardening
- [ ] 📚 Documentation update
- [ ] 🧪 Tests / Test matrix additions
- [ ] 🔄 Database migration / Schema update

## Key Changes & Architectural Integrity

- **Backend Changes**:
  - 
- **Frontend Changes**:
  - 
- **Database / Schema Updates**:
  - 

## Verification & Testing

Please describe the tests executed to verify your changes:

- [ ] Automated tests pass: `pytest backend/tests/`
- [ ] Zero citizen PII leaked in logs or error traces
- [ ] Frontend builds without syntax errors: `npm run build` or Vite HMR validated
- [ ] API endpoints verified with appropriate authentication headers (`X-Officer-Id` / Bearer token)
- [ ] Zero hardcoded fallback values for taxonomy, officers, or administrative locations

## Checklist

- [ ] My code adheres to the project's [Coding Standards](CONTRIBUTING.md).
- [ ] I have performed a self-review of my own code.
- [ ] I have added appropriate comments to complex logic.
- [ ] I have not committed any large model files, database files, or secrets (verified via `.gitignore`).
- [ ] My changes generate no new warnings or regressions.
