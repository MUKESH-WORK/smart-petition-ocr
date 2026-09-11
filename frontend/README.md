# 🏛️ GDP Assistant — Frontend Application

A high-performance, modern React 19 web application engineered for District Revenue Officers (DRO) to ingest, inspect, verify, and route handwritten and typed Tamil/English citizen petitions.

---

## 🏛️ System Purpose

Citizens submit physical petitions during weekly Grievance Day Petition (GDP) collectorate sessions. The **GDP Assistant** web portal serves as an intelligent cognitive workspace before dispatching verified records into the state grievance system:

$$\text{Upload / Mobile QR} \longrightarrow \text{Chandra OCRv2 / PaddleOCR} \longrightarrow \text{Cognitive Analysis} \longrightarrow \text{Interactive Chat \& Draft} \longrightarrow \text{DRO Portal Bridge}$$

---

## ✨ Core Features

- **Split Workspace View**:
  - **Left Panel**: High-resolution petition document viewer with multi-page navigation, zoom, and fit-page controls.
  - **Right Panel**: Real-time AI assistant chat, formal DRO Tamil grievance summary, dynamic quick-action prompts (`✦ Full Details`, `Summarize in one line`, `Which department should handle this?`), and editable grievance draft forms.
- **Mobile QR Intake Bridge**: Generates instant pairing QR codes for intake staff or citizens to capture petition photos directly via smartphone cameras over local Wi-Fi.
- **Editable Officer Profile**: Dropdown in the header enables revenue officers to manage their active identity, designation, department, and assigned taluks.
- **Comprehensive Settings Panel**: Live controls for OCR engine selection (Datalab Chandra OCRv2 vs Local PaddleOCR), LLM cognitive models, threshold parameters, and network endpoints.
- **Live Audit Logs & History**: Complete chronological history of processed petitions, processing times, confidence scores, and officer review statuses.
- **Government Design System**: Accessible, high-contrast palette adhering to state administrative portal guidelines with fluid responsiveness.

---

## 🚀 Getting Started

### Prerequisites

- **Node.js**: v18.x or v20.x LTS
- **npm**: v9.x+

### Quickstart

```bash
# 1. Navigate to the frontend directory
cd frontend

# 2. Install dependencies
npm install

# 3. Start local development server
npm run dev
```

The portal will be live at: **`http://localhost:5174`**.

### Building for Production

```bash
# Production bundle build
npm run build

# Preview production build locally
npm run preview
```

### Docker Containerization

To run using Docker:
```bash
docker build -t gdp-frontend ./frontend
docker run -p 5174:80 gdp-frontend
```

---

## 🛠️ Technology Stack

- **Framework**: React 19.x + Vite 8.x
- **Icons**: Lucide React
- **QR Engine**: qrcode
- **Styling**: Vanilla CSS with Design Token Variables (`src/styles/variables.css`)
- **Linter**: Oxlint
