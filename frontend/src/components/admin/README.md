# Admin frontend

The existing `session.role === 'admin'` selects the admin sidebar and initial Dashboard. Navigation uses the application's existing `activeModule` state. GDP Assistant, Audit Logs, Profile, the header and login retain their existing components.

## Data scope

- Accounts, hierarchy, taxonomy mappings and admin activity are explicitly labelled local previews. They start empty and are stored in `sessionStorage` under `tn_admin_preview_v1`, scoped to the current browser tab.
- Add/edit forms validate credentials visually. Passwords are discarded and never persisted or included in backups. Preview accounts do not create sign-in accounts or change authorization.
- Backups snapshot only local account details, locations and mappings. Download exports JSON; restore requires typing `RESTORE`. Neither operation touches backend records, documents or real accounts.
- Total Petitions reads the existing `/api/v1/admin/stats` endpoint. Success and Failures count distinct sources in the latest 20 history records, with that scope displayed under the cards. Unavailable requests display a dash instead of invented counts.
- Server-backed account management, full system backups and persistent configuration require API support that the current backend does not provide. No new backend routes were added.

## Verification

From the project root:

```powershell
node --test frontend/src/components/admin/adminModel.test.js
```

From `frontend`, run `npm run build`. The existing Vite configuration starts a repeating backend-port check, so the build process may remain running after Vite prints its successful build result.
