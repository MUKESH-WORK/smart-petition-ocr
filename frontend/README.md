# Government Petition Assistant (AI Document Understanding)

A modern, responsive web application for government officers to understand, verify, and extract grievances from scanned Tamil and English citizen petitions before entering them into official grievance portals.

---

## 🏛️ Project Purpose

Government officers frequently receive scanned paper petitions from citizens during grievance days. Previously, officers had to manually read multi-page handwritten/typed petitions in Tamil/English and transcribe all fields manually into government grievance portals.

**Petition Assistant** acts as an intelligent document assistant **before** the official portal:

$$\text{Upload Petition} \longrightarrow \text{OCR Processing} \longrightarrow \text{Raw Extracted Text} \longrightarrow \text{LLM / AI Understanding} \longrightarrow \text{Summary \& Interactive Chat} \longrightarrow \text{Officer Action}$$

---

## ✨ Features

- **Document Analysis & Summary**: Automatic generation of clear petition summaries with language, page count, OCR status, and confidence metrics.
- **Raw OCR Verification**: 1-click collapsible access to view and copy full raw OCR transcripts.
- **Document Chat Assistant**: Interactive Q&A grounded strictly in the petition text with dynamic follow-up suggestions (`✦ Full Details`, `Summarize in one line`, `Which department should handle this?`, etc.).
- **Fixed Two-Panel Workspace**:
  - **Left Panel**: Scanned document preview with page navigation, zoom, and fit-page controls.
  - **Right Panel**: Natural scrolling conversation stream with stationary top metadata and bottom composer.
- **Modern Prompt Input**: Nexus-UI inspired multi-line card with circular action buttons and keyboard shortcuts (`Enter` to send, `Shift+Enter` for new line).
- **Official Government Palette**: Government Navy (`#0A2540`) & Warm Government Orange (`#D9531E`).

---

## 🚀 Getting Started

### Prerequisites

- Node.js (v18 or higher)
- npm or yarn

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd petition-assistant

# Install dependencies
npm install

# Start development server
npm run dev
```

The application will be available at `http://localhost:5173/`.

### Building for Production

```bash
npm run build
npm run preview
```

---

## 🛠️ Technology Stack

- **React 18** + **Vite**
- **Vanilla CSS** with CSS Custom Properties / Tokens
- **Lucide Icons**
- **Google Fonts**: *Plus Jakarta Sans*, *JetBrains Mono*
