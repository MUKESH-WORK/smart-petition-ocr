# GDP Assistant — Frontend

> React 19 + Vite admin portal for the AI-powered grievance redressal platform.

## Tech Stack

| Technology | Version | Purpose |
| :--- | :--- | :--- |
| **React** | 19.x | UI framework |
| **Vite** | 8.x | Build tool & dev server |
| **Vanilla CSS** | — | Design system (no Tailwind/CSS-in-JS) |
| **Lucide React** | 1.x | Icon library |
| **QRCode** | 1.x | Mobile QR capture bridge |
| **OxLint** | 1.x | Fast JavaScript linter |

## Quick Start

```bash
npm install
npm run dev        # Start dev server (http://localhost:5174)
npm run build      # Production build to dist/
npm run lint       # Run OxLint static analysis
npm run preview    # Preview production build
```

## Key Components

| Component | Path | Description |
| :--- | :--- | :--- |
| `App.jsx` | `src/App.jsx` | Root component with routing, auth, and state |
| `Header` | `src/components/layout/Header.jsx` | Navigation bar with language toggle |
| `Sidebar` | `src/components/layout/Sidebar.jsx` | Module navigation sidebar |
| `Workspace` | `src/components/workspace/` | Dual-panel petition processing |
| `AdminWorkspace` | `src/components/admin/` | Taxonomy & hierarchy management |
| `ProfileView` | `src/components/profile/ProfileView.jsx` | Officer profile (role-based editing) |
| `translations.js` | `src/utils/translations.js` | Dynamic LLM translation engine |

## Architecture Notes

- **Role-Based Access**: Profile editing restricted to admin users via `isAdmin` prop
- **Dynamic Translation**: All UI text translated via `useDynamicTranslation` hook — no hardcoded dictionaries
- **Tamil Font Stack**: Tamil inputs use `Noto Sans Tamil` / `Latha` / `Tamil Sangam MN` for proper rendering
- **21 Intake Channels**: Full CM Helpline channel integration in admin taxonomy modal

## Testing

```bash
# Unit tests (Node.js test runner)
node --test src/components/admin/adminModel.test.js

# Lint
npm run lint
```

## Sharing (Development Tunnels)

```bash
npm run tunnel     # LocalTunnel (port 5174)
npm run share      # Cloudflare Tunnel (port 5174)
```
