import {
  Document,
  Paragraph,
  TextRun,
  Table,
  TableRow,
  TableCell,
  WidthType,
  AlignmentType,
  BorderStyle,
  HeadingLevel,
  Packer,
  Header,
  Footer,
  PageNumber,
  ShadingType
} from 'docx';

const COLOR_NAVY = '102C57';
const COLOR_GOLD = 'DAC0A3';
const COLOR_SLATE = '475569';
const COLOR_LIGHT_BG = 'F8FAFC';
const COLOR_LABEL_BG = 'EDF2F7';
const COLOR_BORDER = 'CBD5E1';

const FONT_LATIN = 'Bookman Old Style';
const FONT_TAMIL = 'Marudham';

/**
 * Creates a text run with Bookman Old Style and Marudham font definitions
 */
function createTextRun(text, { bold = false, italic = false, size = 20, color = '1E293B' } = {}) {
  return new TextRun({
    text: String(text !== undefined && text !== null ? text : '—'),
    bold,
    italics: italic,
    size, // in half-points (20 = 10pt)
    color,
    font: {
      name: FONT_LATIN,
      ascii: FONT_LATIN,
      hAnsi: FONT_LATIN,
      cs: FONT_TAMIL,
      eastAsia: FONT_TAMIL
    }
  });
}

/**
 * Creates a styled table cell with padding and borders
 */
function createStyledCell(text, {
  isHeader = false,
  isLabel = false,
  widthPercent = 25,
  align = AlignmentType.LEFT,
  bold = false,
  color = null,
  size = 19
} = {}) {
  let bgColor = 'FFFFFF';
  let textColor = color || '1E293B';
  let isBold = bold;

  if (isHeader) {
    bgColor = COLOR_NAVY;
    textColor = 'FFFFFF';
    isBold = true;
    size = 19; // 9.5pt
  } else if (isLabel) {
    bgColor = COLOR_LABEL_BG;
    textColor = COLOR_NAVY;
    isBold = true;
    size = 18; // 9pt
  }

  const lines = String(text !== undefined && text !== null ? text : '—').split('\n');

  return new TableCell({
    width: { size: widthPercent, type: WidthType.PERCENTAGE },
    shading: {
      type: ShadingType.CLEAR,
      fill: bgColor
    },
    margins: { top: 120, bottom: 120, left: 140, right: 140 },
    borders: {
      top: { style: BorderStyle.SINGLE, size: 4, color: COLOR_BORDER },
      bottom: { style: BorderStyle.SINGLE, size: 4, color: COLOR_BORDER },
      left: { style: BorderStyle.SINGLE, size: 4, color: COLOR_BORDER },
      right: { style: BorderStyle.SINGLE, size: 4, color: COLOR_BORDER }
    },
    children: lines.map(line => new Paragraph({
      alignment: align,
      spacing: { before: 20, after: 20, line: 240 },
      children: [
        createTextRun(line, { bold: isBold, size, color: textColor })
      ]
    }))
  });
}

/**
 * Helper to download docx blob in browser
 */
async function downloadDocxBlob(doc, filename) {
  const blob = await Packer.toBlob(doc);
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  return filename;
}

/**
 * 1. Officer Performance & Processed Petition Counts Report (DOCX)
 */
export async function generateOfficerPerformanceDocx(reportData, selectedOfficerId = 'all') {
  const meta = reportData.reportMetadata || {};
  let officers = reportData.officersDirectory || [];

  if (selectedOfficerId && selectedOfficerId !== 'all') {
    officers = officers.filter(o => String(o.id) === String(selectedOfficerId));
  }

  const generatedDateStr = new Date(meta.generatedAt || Date.now()).toLocaleString('en-IN', {
    dateStyle: 'full',
    timeStyle: 'medium'
  });

  const doc = new Document({
    sections: [{
      properties: {
        page: {
          margin: { top: 1000, bottom: 1000, left: 1000, right: 1000 }
        }
      },
      headers: {
        default: new Header({
          children: [
            new Paragraph({
              alignment: AlignmentType.CENTER,
              children: [
                createTextRun('GOVERNMENT OF TAMIL NADU • ERODE DISTRICT COLLECTORATE', { bold: true, size: 18, color: COLOR_NAVY }),
                createTextRun('  |  Public Grievance Pre-Processing Cell', { size: 16, color: COLOR_SLATE })
              ]
            })
          ]
        })
      },
      footers: {
        default: new Footer({
          children: [
            new Paragraph({
              alignment: AlignmentType.RIGHT,
              children: [
                createTextRun('Official Government Record • Page ', { size: 16, color: COLOR_SLATE }),
                new TextRun({ children: [PageNumber.CURRENT], size: 16, font: FONT_LATIN }),
                createTextRun(' of ', { size: 16, color: COLOR_SLATE }),
                new TextRun({ children: [PageNumber.TOTAL_PAGES], size: 16, font: FONT_LATIN })
              ]
            })
          ]
        })
      },
      children: [
        // Title Block
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { before: 100, after: 60 },
          children: [
            createTextRun('GOVERNMENT OF TAMIL NADU', { bold: true, size: 26, color: COLOR_NAVY })
          ]
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { after: 60 },
          children: [
            createTextRun('REVENUE & DISASTER MANAGEMENT DEPARTMENT • ERODE DISTRICT COLLECTORATE', { bold: true, size: 18, color: COLOR_SLATE })
          ]
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { after: 180 },
          children: [
            createTextRun('OFFICER PETITION PROCESSING & RESOLUTION AUDIT REPORT', { bold: true, size: 22, color: COLOR_NAVY })
          ]
        }),

        // Metadata Box Table
        new Table({
          width: { size: 100, type: WidthType.PERCENTAGE },
          rows: [
            new TableRow({
              children: [
                createStyledCell('District / Office:', { isLabel: true, widthPercent: 25 }),
                createStyledCell('Erode District Collectorate (Public Grievance Cell)', { widthPercent: 25 }),
                createStyledCell('Generated By:', { isLabel: true, widthPercent: 25 }),
                createStyledCell(meta.generatedBy || 'District Administrator', { widthPercent: 25 })
              ]
            }),
            new TableRow({
              children: [
                createStyledCell('Generated Date & Time:', { isLabel: true, widthPercent: 25 }),
                createStyledCell(generatedDateStr, { widthPercent: 25 }),
                createStyledCell('Security Level:', { isLabel: true, widthPercent: 25 }),
                createStyledCell('OFFICIAL / RESTRICTED', { widthPercent: 25, bold: true, color: '166534' })
              ]
            })
          ]
        }),

        // Section 1: KPI Cards
        new Paragraph({
          spacing: { before: 200, after: 100 },
          children: [
            createTextRun('1. Executive Overview & Key Metrics', { bold: true, size: 22, color: COLOR_NAVY })
          ]
        }),
        new Table({
          width: { size: 100, type: WidthType.PERCENTAGE },
          rows: [
            new TableRow({
              children: [
                createStyledCell('Total Officers Registered', { isHeader: true, widthPercent: 25, align: AlignmentType.CENTER }),
                createStyledCell('Active Officer Sessions', { isHeader: true, widthPercent: 25, align: AlignmentType.CENTER }),
                createStyledCell('Total Petitions Processed', { isHeader: true, widthPercent: 25, align: AlignmentType.CENTER }),
                createStyledCell('Total Approved / Resolved', { isHeader: true, widthPercent: 25, align: AlignmentType.CENTER })
              ]
            }),
            new TableRow({
              children: [
                createStyledCell(String(meta.totalOfficers || officers.length), { widthPercent: 25, align: AlignmentType.CENTER, bold: true, size: 24, color: COLOR_NAVY }),
                createStyledCell(String(meta.activeOfficers || 0), { widthPercent: 25, align: AlignmentType.CENTER, bold: true, size: 24, color: COLOR_NAVY }),
                createStyledCell(String(meta.totalPetitions || 0), { widthPercent: 25, align: AlignmentType.CENTER, bold: true, size: 24, color: COLOR_NAVY }),
                createStyledCell(String(meta.totalApproved || 0), { widthPercent: 25, align: AlignmentType.CENTER, bold: true, size: 24, color: '166534' })
              ]
            })
          ]
        }),

        // Section 2: Officer Performance Table
        new Paragraph({
          spacing: { before: 260, after: 100 },
          children: [
            createTextRun('2. Officer-Wise Petition Redressal Performance Breakdown', { bold: true, size: 22, color: COLOR_NAVY })
          ]
        }),
        new Table({
          width: { size: 100, type: WidthType.PERCENTAGE },
          rows: [
            new TableRow({
              children: [
                createStyledCell('Officer ID', { isHeader: true, widthPercent: 14 }),
                createStyledCell('Official Name', { isHeader: true, widthPercent: 22 }),
                createStyledCell('Department & Role', { isHeader: true, widthPercent: 24 }),
                createStyledCell('Total', { isHeader: true, widthPercent: 10, align: AlignmentType.CENTER }),
                createStyledCell('Approved', { isHeader: true, widthPercent: 10, align: AlignmentType.CENTER }),
                createStyledCell('In Review', { isHeader: true, widthPercent: 10, align: AlignmentType.CENTER }),
                createStyledCell('Pending', { isHeader: true, widthPercent: 10, align: AlignmentType.CENTER })
              ]
            }),
            ...officers.map(off => new TableRow({
              children: [
                createStyledCell(off.id, { widthPercent: 14, isLabel: true }),
                createStyledCell(`${off.name}\n${off.nameTamil || ''}`, { widthPercent: 22, bold: true }),
                createStyledCell(`${off.department}\n${off.designation}`, { widthPercent: 24 }),
                createStyledCell(String(off.totalProcessed || 0), { widthPercent: 10, align: AlignmentType.CENTER, bold: true }),
                createStyledCell(String(off.approved || 0), { widthPercent: 10, align: AlignmentType.CENTER, color: '166534', bold: true }),
                createStyledCell(String(off.inProgress || 0), { widthPercent: 10, align: AlignmentType.CENTER }),
                createStyledCell(String(off.pending || 0), { widthPercent: 10, align: AlignmentType.CENTER })
              ]
            }))
          ]
        }),

        // Sign-off
        new Paragraph({
          spacing: { before: 300, after: 60 },
          children: [
            createTextRun('Certified Official Document — Government of Tamil Nadu', { bold: true, size: 18, color: COLOR_NAVY })
          ]
        }),
        new Paragraph({
          children: [
            createTextRun('This report is generated by the AI Administrative Co-Pilot under the authority of District Collectorate, Erode. All records are cryptographically verified in the system audit database.', { size: 16, color: COLOR_SLATE })
          ]
        })
      ]
    }]
  });

  const filename = `Officer_Performance_Report_${new Date().toISOString().slice(0, 10)}.docx`;
  return await downloadDocxBlob(doc, filename);
}

/**
 * 2. Full Audit Log History Report (DOCX)
 */
export async function generateAuditLogsDocx(reportData, filterOfficerId = 'all') {
  const meta = reportData.reportMetadata || {};
  let logs = reportData.recentAuditLogs || [];

  if (filterOfficerId && filterOfficerId !== 'all') {
    logs = logs.filter(l => String(l.officer_id || '').toLowerCase() === String(filterOfficerId).toLowerCase());
  }

  const doc = new Document({
    sections: [{
      properties: {
        page: {
          margin: { top: 1000, bottom: 1000, left: 1000, right: 1000 }
        }
      },
      headers: {
        default: new Header({
          children: [
            new Paragraph({
              alignment: AlignmentType.CENTER,
              children: [
                createTextRun('GOVERNMENT OF TAMIL NADU • SYSTEM AUDIT & SECURITY TRAIL', { bold: true, size: 18, color: COLOR_NAVY })
              ]
            })
          ]
        })
      },
      children: [
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { before: 100, after: 60 },
          children: [
            createTextRun('OFFICIAL SYSTEM AUDIT LOG HISTORY REPORT', { bold: true, size: 26, color: COLOR_NAVY })
          ]
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { after: 180 },
          children: [
            createTextRun(`Filter: ${filterOfficerId === 'all' ? 'All Officers & Modules' : `Officer ID: ${filterOfficerId}`}  |  Total Entries: ${logs.length}`, { size: 18, color: COLOR_SLATE })
          ]
        }),
        new Table({
          width: { size: 100, type: WidthType.PERCENTAGE },
          rows: [
            new TableRow({
              children: [
                createStyledCell('Timestamp', { isHeader: true, widthPercent: 20 }),
                createStyledCell('Officer ID', { isHeader: true, widthPercent: 16 }),
                createStyledCell('Category / Module', { isHeader: true, widthPercent: 18 }),
                createStyledCell('Action / Type', { isHeader: true, widthPercent: 16 }),
                createStyledCell('Audit Event Details', { isHeader: true, widthPercent: 30 })
              ]
            }),
            ...logs.slice(0, 150).map(l => new TableRow({
              children: [
                createStyledCell(l.timestamp ? new Date(l.timestamp).toLocaleString('en-IN') : '—', { widthPercent: 20 }),
                createStyledCell(l.officer_id || 'SYSTEM', { widthPercent: 16, isLabel: true }),
                createStyledCell(l.category || 'GDP Assistant', { widthPercent: 18 }),
                createStyledCell(l.action || l.type || 'ACTIVITY', { widthPercent: 16 }),
                createStyledCell(l.details || '—', { widthPercent: 30 })
              ]
            }))
          ]
        })
      ]
    }]
  });

  const filename = `System_Audit_Log_${filterOfficerId === 'all' ? 'All_Officers' : filterOfficerId}_${new Date().toISOString().slice(0, 10)}.docx`;
  return await downloadDocxBlob(doc, filename);
}

/**
 * 3. Particular Petition Full Form Details Dossier (DOCX)
 */
export async function generateSinglePetitionDocx(petition) {
  if (!petition) throw new Error('Petition details not provided.');

  const petNumber = petition.petitionNumber || petition.id || 'PET-DOCUMENT';

  const doc = new Document({
    sections: [{
      properties: {
        page: {
          margin: { top: 1000, bottom: 1000, left: 1000, right: 1000 }
        }
      },
      headers: {
        default: new Header({
          children: [
            new Paragraph({
              alignment: AlignmentType.CENTER,
              children: [
                createTextRun('GOVERNMENT OF TAMIL NADU • REVENUE & DISASTER MANAGEMENT DEPARTMENT', { bold: true, size: 18, color: COLOR_NAVY })
              ]
            })
          ]
        })
      },
      children: [
        // Title
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { before: 80, after: 40 },
          children: [
            createTextRun('GOVERNMENT OF TAMIL NADU', { bold: true, size: 26, color: COLOR_NAVY })
          ]
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { after: 40 },
          children: [
            createTextRun('ERODE DISTRICT COLLECTORATE • PUBLIC GRIEVANCE PRE-PROCESSING CELL', { bold: true, size: 18, color: COLOR_SLATE })
          ]
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { after: 180 },
          children: [
            createTextRun(`PETITION DOSSIER & RECORD OF GRIEVANCE — ${petNumber}`, { bold: true, size: 22, color: COLOR_NAVY })
          ]
        }),

        // Key Summary Table
        new Table({
          width: { size: 100, type: WidthType.PERCENTAGE },
          rows: [
            new TableRow({
              children: [
                createStyledCell('Petition Number:', { isLabel: true, widthPercent: 25 }),
                createStyledCell(petNumber, { widthPercent: 25, bold: true }),
                createStyledCell('Current Status:', { isLabel: true, widthPercent: 25 }),
                createStyledCell(petition.status || 'Approved', { widthPercent: 25, bold: true, color: petition.status === 'Approved' ? '166534' : 'B45309' })
              ]
            }),
            new TableRow({
              children: [
                createStyledCell('Assigned Officer:', { isLabel: true, widthPercent: 25 }),
                createStyledCell(`${petition.officerName || 'Assigned Officer'} (${petition.officerId || '—'})`, { widthPercent: 25 }),
                createStyledCell('Submission Date:', { isLabel: true, widthPercent: 25 }),
                createStyledCell(petition.createdAt ? new Date(petition.createdAt).toLocaleString('en-IN') : 'Recent', { widthPercent: 25 })
              ]
            })
          ]
        }),

        // 1. Applicant Identity & Location
        new Paragraph({
          spacing: { before: 200, after: 80 },
          children: [
            createTextRun('1. Applicant Identity & Geographic Hierarchy', { bold: true, size: 22, color: COLOR_NAVY })
          ]
        }),
        new Table({
          width: { size: 100, type: WidthType.PERCENTAGE },
          rows: [
            new TableRow({
              children: [
                createStyledCell('Petitioner Name', { isLabel: true, widthPercent: 25 }),
                createStyledCell(petition.applicantName || '—', { widthPercent: 25, bold: true }),
                createStyledCell('District', { isLabel: true, widthPercent: 25 }),
                createStyledCell(petition.district || 'Erode', { widthPercent: 25 })
              ]
            }),
            new TableRow({
              children: [
                createStyledCell('Mobile Number', { isLabel: true, widthPercent: 25 }),
                createStyledCell(petition.mobile || '—', { widthPercent: 25 }),
                createStyledCell('Taluk / Firka', { isLabel: true, widthPercent: 25 }),
                createStyledCell(`${petition.taluk || 'Erode'} / ${petition.firka || 'Erode Urban'}`, { widthPercent: 25 })
              ]
            }),
            new TableRow({
              children: [
                createStyledCell('Email Address', { isLabel: true, widthPercent: 25 }),
                createStyledCell(petition.email || '—', { widthPercent: 25 }),
                createStyledCell('Village / Block', { isLabel: true, widthPercent: 25 }),
                createStyledCell(`${petition.village || 'Surampatti'} / ${petition.block || 'Erode'}`, { widthPercent: 25 })
              ]
            }),
            new TableRow({
              children: [
                createStyledCell('Residential Address', { isLabel: true, widthPercent: 25 }),
                createStyledCell(petition.address || 'Erode District, Tamil Nadu', { widthPercent: 75 })
              ]
            })
          ]
        }),

        // 2. Administrative Grievance Classification
        new Paragraph({
          spacing: { before: 200, after: 80 },
          children: [
            createTextRun('2. Administrative Grievance Classification', { bold: true, size: 22, color: COLOR_NAVY })
          ]
        }),
        new Table({
          width: { size: 100, type: WidthType.PERCENTAGE },
          rows: [
            new TableRow({
              children: [
                createStyledCell('Assigned Department', { isLabel: true, widthPercent: 25 }),
                createStyledCell(petition.department || 'Revenue Administration', { widthPercent: 25, bold: true }),
                createStyledCell('Intake Channel', { isLabel: true, widthPercent: 25 }),
                createStyledCell(petition.intakeChannel || 'Collectorate Counter', { widthPercent: 25 })
              ]
            }),
            new TableRow({
              children: [
                createStyledCell('Grievance Category', { isLabel: true, widthPercent: 25 }),
                createStyledCell(petition.category || 'Patta & Land Records', { widthPercent: 25 }),
                createStyledCell('Grievance Sub-Category', { isLabel: true, widthPercent: 25 }),
                createStyledCell(petition.subCategory || 'Patta Transfer', { widthPercent: 25 })
              ]
            })
          ]
        }),

        // 3. AI Grievance Summary
        new Paragraph({
          spacing: { before: 200, after: 80 },
          children: [
            createTextRun('3. AI Grievance Summary & Action Trail', { bold: true, size: 22, color: COLOR_NAVY })
          ]
        }),
        new Table({
          width: { size: 100, type: WidthType.PERCENTAGE },
          rows: [
            new TableRow({
              children: [
                createStyledCell('Summary in Tamil\n(மனு சுருக்கம்)', { isLabel: true, widthPercent: 30 }),
                createStyledCell(petition.summaryTamil || petition.description || 'மனு விவரங்கள் பதிவு செய்யப்பட்டுள்ளன.', { widthPercent: 70 })
              ]
            }),
            new TableRow({
              children: [
                createStyledCell('English Synopsis', { isLabel: true, widthPercent: 30 }),
                createStyledCell(petition.summaryEnglish || 'Grievance recorded in registry for processing.', { widthPercent: 70 })
              ]
            }),
            new TableRow({
              children: [
                createStyledCell('Recommended Action Points', { isLabel: true, widthPercent: 30 }),
                createStyledCell(
                  Array.isArray(petition.actionItems) && petition.actionItems.length
                    ? petition.actionItems.map(a => typeof a === 'object' ? (a.action || a.description || JSON.stringify(a)) : a).join('; ')
                    : '1. Field verification by Revenue Inspector\n2. Verification of Village Records\n3. Issuance of DRO Order',
                  { widthPercent: 70 }
                )
              ]
            })
          ]
        }),

        // Sign-off
        new Paragraph({
          spacing: { before: 260, after: 60 },
          children: [
            createTextRun('Certified Official Document — Government of Tamil Nadu', { bold: true, size: 18, color: COLOR_NAVY })
          ]
        }),
        new Paragraph({
          children: [
            createTextRun(`Certified true record as registered in the District Grievance Pre-Processing System • Date: ${new Date().toLocaleDateString('en-IN')}`, { size: 16, color: COLOR_SLATE })
          ]
        })
      ]
    }]
  });

  const filename = `Petition_Dossier_${petNumber}_${new Date().toISOString().slice(0, 10)}.docx`;
  return await downloadDocxBlob(doc, filename);
}

/**
 * 4. Total Petitions Received & Intake Analysis Report (DOCX)
 */
export async function generateIntakeReportDocx(reportData) {
  const meta = reportData.reportMetadata || {};
  const analysis = reportData.intakeAnalysis || {};
  const petitions = reportData.petitionProcessingHistory || [];

  const byChannel = analysis.byChannel || {};
  const byDept = analysis.byDepartment || {};
  const byTaluk = analysis.byTaluk || {};

  const doc = new Document({
    sections: [{
      properties: {
        page: {
          margin: { top: 1000, bottom: 1000, left: 1000, right: 1000 }
        }
      },
      headers: {
        default: new Header({
          children: [
            new Paragraph({
              alignment: AlignmentType.CENTER,
              children: [
                createTextRun('GOVERNMENT OF TAMIL NADU • TOTAL PETITIONS RECEIVED & INTAKE ANALYSIS', { bold: true, size: 18, color: COLOR_NAVY })
              ]
            })
          ]
        })
      },
      children: [
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { before: 100, after: 60 },
          children: [
            createTextRun('TOTAL PETITIONS RECEIVED & MULTI-CHANNEL INTAKE REPORT', { bold: true, size: 26, color: COLOR_NAVY })
          ]
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { after: 180 },
          children: [
            createTextRun(`Total Petitions: ${meta.totalPetitions || petitions.length}  |  Approved: ${meta.totalApproved || 0}  |  Pending: ${meta.totalPending || 0}`, { bold: true, size: 20, color: COLOR_NAVY })
          ]
        }),

        // 1. Intake Channels Table
        new Paragraph({
          spacing: { before: 180, after: 80 },
          children: [
            createTextRun('1. Ingestion Breakdown by CM Grievance Intake Channel', { bold: true, size: 22, color: COLOR_NAVY })
          ]
        }),
        new Table({
          width: { size: 100, type: WidthType.PERCENTAGE },
          rows: [
            new TableRow({
              children: [
                createStyledCell('Intake Channel Name', { isHeader: true, widthPercent: 65 }),
                createStyledCell('Petitions Received', { isHeader: true, widthPercent: 35, align: AlignmentType.CENTER })
              ]
            }),
            ...Object.entries(byChannel).map(([channel, count]) => new TableRow({
              children: [
                createStyledCell(channel, { widthPercent: 65 }),
                createStyledCell(String(count), { widthPercent: 35, align: AlignmentType.CENTER, bold: true })
              ]
            }))
          ]
        }),

        // 2. Department Breakdown
        new Paragraph({
          spacing: { before: 200, after: 80 },
          children: [
            createTextRun('2. Distribution by Government Department', { bold: true, size: 22, color: COLOR_NAVY })
          ]
        }),
        new Table({
          width: { size: 100, type: WidthType.PERCENTAGE },
          rows: [
            new TableRow({
              children: [
                createStyledCell('Department Name', { isHeader: true, widthPercent: 65 }),
                createStyledCell('Total Grievances', { isHeader: true, widthPercent: 35, align: AlignmentType.CENTER })
              ]
            }),
            ...Object.entries(byDept).map(([dept, count]) => new TableRow({
              children: [
                createStyledCell(dept, { widthPercent: 65 }),
                createStyledCell(String(count), { widthPercent: 35, align: AlignmentType.CENTER, bold: true })
              ]
            }))
          ]
        }),

        // 3. Taluk Breakdown
        new Paragraph({
          spacing: { before: 200, after: 80 },
          children: [
            createTextRun('3. Geographic Allocation by Taluk', { bold: true, size: 22, color: COLOR_NAVY })
          ]
        }),
        new Table({
          width: { size: 100, type: WidthType.PERCENTAGE },
          rows: [
            new TableRow({
              children: [
                createStyledCell('Taluk Name', { isHeader: true, widthPercent: 65 }),
                createStyledCell('Allocated Petitions', { isHeader: true, widthPercent: 35, align: AlignmentType.CENTER })
              ]
            }),
            ...Object.entries(byTaluk).map(([taluk, count]) => new TableRow({
              children: [
                createStyledCell(taluk, { widthPercent: 65 }),
                createStyledCell(String(count), { widthPercent: 35, align: AlignmentType.CENTER, bold: true })
              ]
            }))
          ]
        })
      ]
    }]
  });

  const filename = `Total_Petitions_Received_Report_${new Date().toISOString().slice(0, 10)}.docx`;
  return await downloadDocxBlob(doc, filename);
}
