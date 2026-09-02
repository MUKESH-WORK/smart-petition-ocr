// Realistic Mock Datasets for Tamil Nadu Government Petition AI Assistant

export const MOCK_PETITIONS = [
  {
    id: 'TEMP-001',
    fileName: 'petition_001.pdf',
    fileSize: '1.8 MB',
    fileType: 'PDF Document (Scanned)',
    uploadedAt: 'Today at 10:14 AM',
    totalPages: 1,
    language: 'Tamil',
    confidenceScore: 96,
    status: 'Analysis Complete',
    
    // AI Summary
    summary: 'The petitioner requests repair of a damaged road in ABC Village, Erode District. The petition states that the road has remained damaged for several months and causes transportation difficulties during rainfall.',
    
    // Raw OCR Extracted Text (Full transcript for verification)
    rawOcrText: `================================================================================
ஈரோடு மாவட்ட ஆட்சியர் அலுவலகம் - மக்கள் குறைதீர்க்கும் நாள் மனு
OFFICE OF THE DISTRICT COLLECTOR, ERODE — GRIEVANCE DAY PETITION
மனு எண் / Ref No: PET-2026-ERD-08492        நாள் / Date: 16-02-2026
முத்திரை: RECEIVED • COLLECTORATE ERODE
================================================================================

அனுப்புநர் (From):
  ஆர். குமார் (வயது 44), த/பெ. ராமசாமி,
  கதவு எண் 14/2, மாரியம்மன் கோவில் தெரு,
  ABC கிராமம், திங்களூர் பிர்கா,
  பெருந்துறை வட்டம், ஈரோடு மாவட்டம் - 638052.
  கைபேசி (Mobile): 9876543210

பெறுநர் (To):
  உயர்திரு மாவட்ட ஆட்சித்தலைவர் அவர்கள்,
  மாவட்ட ஆட்சியர் பெருந்திட்ட வளாகம்,
  ஈரோடு மாவட்டம்.

பொருள் (Subject):
  பெருந்துறை வட்டம், ABC கிராமத்தில் மாரியம்மன் கோவில் தெருவில் பழுதடைந்துள்ள 
  தார் சாலையை சீரமைத்து தரக்கோருதல் - சார்பாக.

மனுவின் விவரம் (Grievance Text):
  வணக்கம். நாங்கள் ஈரோடு மாவட்டம் பெருந்துறை வட்டம் ABC கிராமத்தில் வசித்து வருகிறோம். 
  எங்கள் பகுதியில் உள்ள மாரியம்மன் கோவில் தெரு பிரதான இணைப்புச் சாலை கடந்த ஆறு 
  மாதங்களுக்கு மேலாக ஆங்காங்கே பெரிய பள்ளங்கள் ஏற்பட்டு மிகவும் மோசமான நிலையில் உள்ளது.
  
  மழைக்காலங்களில் இந்த பள்ளங்களில் மழைநீர் தேங்கி நிற்பதால் பள்ளி செல்லும் மாணவ, 
  மாணவியர் மற்றும் பால் வண்டிகள், இருசக்கர வாகனங்கள் விபத்துக்குள்ளாகும் நிலை உள்ளது. 
  இதுகுறித்து ஊராட்சி நிர்வாகத்திடம் முறையிட்டும் இதுவரை எவ்வித நடவடிக்கையும் 
  எடுக்கப்படவில்லை.

  எனவே, பொதுமக்கள் மற்றும் பள்ளி மாணவர்களின் நலனைக் கருத்தில் கொண்டு, 
  பழுதடைந்த இந்த தார் சாலையை உடனடியாக சீரமைத்து புதிய சாலை அமைத்துத் 
  தருமாறு பணிவுடன் கேட்டுக்கொள்கிறேன்.

இவண் (Yours faithfully),
  [ஒப்பம்: ஆர். குமார்]
  (R. KUMAR)

இணைப்புகள் (Enclosures):
  1. பழுதடைந்த சாலையின் புகைப்படங்கள் (2 நகல்கள்)
  2. ஆதார் அடையாள அட்டை நகல்
================================================================================`,

    // Mock Chat Knowledge Base & Fact Verification
    qaDatabase: [
      {
        questionMatches: ['full details', 'give me full details', 'give me the full details', 'important details', 'give me the important details', 'details'],
        answer: `**FULL PETITION DETAILS**

**Petitioner:**
R. Kumar (Age 44, S/o Ramasamy)

**Phone:**
9876543210

**Address:**
14/2, Mariamman Kovil Street,
ABC Village, Thingalur Firka,
Perundurai Taluk, Erode - 638052

**Main Grievance:**
Request for repair of damaged village link road with severe potholes for over 6 months.

**Location:**
ABC Village, Perundurai Taluk, Erode District

**Reference Number:**
PET-2026-ERD-08492 (Collectorate Grievance Day)

**Suggested Department:**
Rural Development / Road Maintenance (Village Panchayat Wing)

**Requested Action:**
Repair and resurface the damaged road.`
      },
      {
        questionMatches: ['summarize in one line', 'one line', 'one sentence', 'short summary'],
        answer: 'Citizen R. Kumar requests urgent repair of a pothole-ridden village road in ABC Village, Perundurai Taluk that causes transit hazards during rainfall.'
      },
      {
        questionMatches: ['explain the grievance', 'grievance', 'complaint', 'main complaint', 'issue', 'problem'],
        answer: 'The grievance states that the main link road in **Mariamman Kovil Street, ABC Village** has had deep potholes for over 6 months. During rains, stagnant water creates severe hazards for school children, two-wheelers, and milk delivery vans, with no action taken after initial local complaints.'
      },
      {
        questionMatches: ['which department', 'department', 'handle this', 'routing', 'responsible'],
        answer: 'Based on the petition, this appears related to **Rural Development & Panchayat Raj** (Block Development Officer / Village Panchayat road wing). Please verify before entering it into the official grievance portal.'
      },
      {
        questionMatches: ['why this department', 'why department', 'reason for department'],
        answer: 'This department is suggested because village link roads within rural panchayat limits (ABC Village, Perundurai) fall under the maintenance purview of the Block Development Office (BDO - Village Panchayats).'
      },
      {
        questionMatches: ['what action is requested', 'action requested', 'requested action', 'what is requested'],
        answer: 'The petitioner requests an official site inspection, prompt repair of potholes, and laying of a new tar road surface on Mariamman Kovil Street.'
      },
      {
        questionMatches: ['who is the petitioner', 'petitioner', 'applicant', 'name'],
        answer: 'The petitioner is **R. Kumar** (Age 44), S/o Ramasamy, residing at 14/2, Mariamman Kovil Street, ABC Village, Perundurai Taluk, Erode.'
      },
      {
        questionMatches: ['phone', 'mobile', 'contact', 'number'],
        answer: 'The contact phone number mentioned in the document is **9876543210**.'
      },
      {
        questionMatches: ['address', 'location', 'village', 'where'],
        answer: 'The address is **14/2, Mariamman Kovil Street, ABC Village, Thingalur Firka, Perundurai Taluk, Erode District - 638052**.'
      },
      {
        questionMatches: ['reference', 'ref number', 'id'],
        answer: 'The document includes official endorsement reference number: **PET-2026-ERD-08492** (Stamped 16-02-2026 at Erode Collectorate).'
      }
    ]
  },

  // Sample Petition 2: Salem Water Supply
  {
    id: 'TEMP-002',
    fileName: 'salem_water_petition_042.pdf',
    fileSize: '2.4 MB',
    fileType: 'PDF Document (Scanned)',
    uploadedAt: 'Today at 09:30 AM',
    totalPages: 1,
    language: 'Tamil & English',
    confidenceScore: 94,
    status: 'Analysis Complete',
    
    summary: 'The petitioner submits a grievance regarding irregular drinking water supply in Ward 12, Attur Municipality, Salem District. Public taps have been dry for the past 12 days due to pipeline leakage near Railway Gate.',
    
    rawOcrText: `================================================================================
சேலம் மாவட்ட ஆட்சியர் குறைதீர்க்கும் நாள் மனு
DISTRICT COLLECTORATE, SALEM — GRIEVANCE PETITION
Ref: PET-2026-SLM-04192        Date: 10-02-2026
Seal: COLLECTORATE SALEM • TAPAL RECEIVED
================================================================================

அனுப்புநர் (From):
  எஸ். மீனாட்சி அம்மாள் (S. Meenakshi Ammal),
  28, காந்தி ரோடு, வார்டு 12,
  ஆத்தூர், சேலம் மாவட்டம் - 636102.
  கைபேசி: 9443218765

பெறுநர் (To):
  உயர்திரு மாவட்ட ஆட்சியர் அவர்கள்,
  சேலம் மாவட்டம்.

பொருள் (Subject):
  ஆத்தூர் நகராட்சி வார்டு 12ல் கடந்த 12 நாட்களாக குடிநீர் விநியோகம் 
  தடைபட்டுள்ளதை சீரமைக்க கோருதல்.

விவரம் (Body):
  மதிப்பிற்குரிய ஐயா,
  ஆத்தூர் நகராட்சிக்குட்பட்ட காந்தி ரோடு பகுதியில் ரயில்வே கேட் அருகில் 
  பிரதான குடிநீர் குழாயில் ஏற்பட்ட உடைப்பு காரணமாக கடந்த 12 நாட்களாக 
  குடிநீர் வரவில்லை. பொதுமக்கள் மிகவும் சிரமப்படுகின்றனர். உடனடியாக 
  குழாயை சரிசெய்து தண்ணீர் விநியோகம் செய்ய உத்தரவிடுமாறு கேட்டுக்கொள்கிறேன்.

இவண்,
  [ஒப்பம்: எஸ். மீனாட்சி அம்மாள்]
================================================================================`,

    qaDatabase: [
      {
        questionMatches: ['full details', 'give me full details', 'give me the full details', 'important details', 'details'],
        answer: `**FULL PETITION DETAILS**

**Petitioner:**
S. Meenakshi Ammal

**Phone:**
9443218765

**Address:**
28, Gandhi Road, Ward 12,
Attur, Salem - 636102

**Main Grievance:**
Drinking water supply disruption for 12 days due to burst pipeline near Railway Gate.

**Location:**
Ward 12, Attur Municipality, Salem District

**Reference Number:**
PET-2026-SLM-04192 (Dated 10-02-2026)

**Suggested Department:**
Municipal Administration & Water Supply (Attur Municipality / TWAD)

**Requested Action:**
Immediate pipeline repair and restoration of public drinking water supply.`
      },
      {
        questionMatches: ['summarize in one line', 'one line', 'one sentence'],
        answer: 'Petitioner S. Meenakshi Ammal requests urgent repair of a burst drinking water pipeline near Railway Gate in Ward 12, Attur Municipality.'
      },
      {
        questionMatches: ['explain the grievance', 'grievance', 'issue', 'complaint'],
        answer: 'Drinking water supply in Ward 12 has been completely disrupted for the past 12 days due to a major underground pipeline burst near the Railway Gate.'
      },
      {
        questionMatches: ['which department', 'department', 'handle'],
        answer: 'Based on the petition, this appears related to **Municipal Administration & Water Supply** (Attur Municipality Water Supply Wing). Please verify before portal entry.'
      },
      {
        questionMatches: ['what action is requested', 'action requested', 'action'],
        answer: 'The petitioner requests emergency pipe replacement and resumption of the scheduled drinking water supply to Ward 12.'
      },
      {
        questionMatches: ['petitioner', 'who is', 'name'],
        answer: 'The applicant is **S. Meenakshi Ammal**, residing at 28, Gandhi Road, Ward 12, Attur, Salem.'
      },
      {
        questionMatches: ['phone', 'mobile', 'contact'],
        answer: 'The petitioner\'s contact number is **9443218765**.'
      }
    ]
  },

  // Sample Petition 3: Patta Sub-Division
  {
    id: 'TEMP-003',
    fileName: 'patta_transfer_cb09.pdf',
    fileSize: '3.1 MB',
    fileType: 'PDF Document (Scanned)',
    uploadedAt: 'Yesterday at 04:15 PM',
    totalPages: 3,
    language: 'Tamil & English',
    confidenceScore: 92,
    status: 'Analysis Complete',
    
    summary: 'The petitioner requests sub-division and issuance of a separate Patta for agricultural Survey No. 142/3B measuring 1.45 Acres in Pollachi Taluk, Coimbatore District following registered partition deed.',
    
    rawOcrText: `================================================================================
கோயம்புத்தூர் மாவட்ட வருவாய்த்துறை மனு
DISTRICT REVENUE CELL, COIMBATORE — PATTA SUB-DIVISION PETITION
Ref: PET-2026-CBE-09142        Date: 18-02-2026
Seal: POLLACHI TALUK OFFICE • REVENUE STAMP
================================================================================

அனுப்புநர் (From):
  கே. வேலுசாமி (K. Velusamy),
  5/82, ஆனைமலை ரோடு,
  பொள்ளாச்சி வட்டம், கோயம்புத்தூர் - 642001.
  கைபேசி: 9842267812

பெறுநர் (To):
  வட்டாட்சியர் அவர்கள் (The Tahsildar),
  வட்டாட்சியர் அலுவலகம், பொள்ளாச்சி வட்டம்.

பொருள் (Subject):
  பொள்ளாச்சி வட்டம் புல எண் 142/3B விஸ்தீரணம் 1.45 ஏக்கர் நிலத்திற்கு 
  பாகப்பிரிவினை அடிப்படையில் உட்பிரிவு செய்து தனி பட்டா வழங்கக் கோருதல்.

விவரம் (Body):
  ஐயா, பொள்ளாச்சி வட்டம் புல எண் 142/3Bல் உள்ள 1.45 ஏக்கர் பூர்வீக நிலம் 
  குடும்ப பாகப்பிரிவினை ஆவணம் எண் 1104/2025ன் படி எனது பங்கிற்கு வந்துள்ளது. 
  மேற்படி நிலத்தை நில அளவர் மூலம் அளவீடு செய்து உட்பிரிவு செய்து 
  பட்டா வழங்கிட வேண்டுகிறேன்.

இவண்,
  [ஒப்பம்: கே. வேலுசாமி]
================================================================================`,

    qaDatabase: [
      {
        questionMatches: ['full details', 'give me full details', 'give me the full details', 'important details', 'details'],
        answer: `**FULL PETITION DETAILS**

**Petitioner:**
K. Velusamy

**Phone:**
9842267812

**Address:**
5/82, Anaimalai Road,
Pollachi Taluk, Coimbatore - 642001

**Survey Number:**
Survey No. 142/3B (Extent: 1.45 Acres)

**Main Grievance:**
Partition deed settlement — request for field survey, sub-division and issuance of individual Patta.

**Location:**
Pollachi Taluk, Coimbatore District

**Reference Number:**
PET-2026-CBE-09142 (Dated 18-02-2026)

**Suggested Department:**
Revenue and Disaster Management (Tahsildar / Taluk Surveyor, Pollachi)

**Requested Action:**
Inspect land, sub-divide survey boundaries, and issue separate Patta record.`
      },
      {
        questionMatches: ['summarize in one line', 'one line'],
        answer: 'Petitioner K. Velusamy requests land survey, sub-division, and separate Patta for 1.45 Acres in S.No 142/3B, Pollachi based on partition deed.'
      },
      {
        questionMatches: ['explain the grievance', 'grievance', 'issue'],
        answer: 'The grievance is a request to demarcate boundaries and issue an independent Patta for ancestral land divided under Deed No. 1104/2025.'
      },
      {
        questionMatches: ['which department', 'department', 'handle'],
        answer: 'This falls under the **Revenue and Disaster Management Department** (Tahsildar / Taluk Surveyor / VAO Pollachi).'
      },
      {
        questionMatches: ['what action is requested', 'action requested', 'action'],
        answer: "Field survey by Taluk surveyor, sub-division entry in village 'A' Register, and issuance of Patta passbook."
      },
      {
        questionMatches: ['petitioner', 'who is', 'name'],
        answer: 'The applicant is **K. Velusamy**, residing at 5/82, Anaimalai Road, Pollachi Taluk, Coimbatore.'
      },
      {
        questionMatches: ['phone', 'mobile', 'contact'],
        answer: 'The petitioner\'s phone number is **9842267812**.'
      }
    ]
  }
];

// Helper to determine dynamic contextual suggested prompts
export function getContextualSuggestions(lastQuery, usedQueries = new Set()) {
  const q = (lastQuery || '').toLowerCase();

  // If no queries yet, initial state is Full Details
  if (!lastQuery) {
    return ['Full Details'];
  }

  let candidates = [];

  if (q.includes('full details') || q.includes('details')) {
    candidates = [
      'Summarize in one line',
      'Explain the grievance',
      'Which department should handle this?',
      'What action is requested?'
    ];
  } else if (q.includes('department') || q.includes('routing')) {
    candidates = [
      'Why this department?',
      'What is the grievance type?',
      'What location is involved?',
      'What action is requested?'
    ];
  } else if (q.includes('petitioner') || q.includes('who is') || q.includes('name')) {
    candidates = [
      'What is the phone number?',
      'What address is mentioned?',
      'Is a reference number available?',
      'Which department should handle this?'
    ];
  } else if (q.includes('summarize') || q.includes('one line')) {
    candidates = [
      'Explain the grievance',
      'Which department should handle this?',
      'What action is requested?',
      'What is the phone number?'
    ];
  } else if (q.includes('grievance') || q.includes('issue') || q.includes('complaint')) {
    candidates = [
      'What action is requested?',
      'Which department should handle this?',
      'What location is mentioned?',
      'Summarize in one line'
    ];
  } else {
    candidates = [
      'Summarize in one line',
      'Which department should handle this?',
      'What action is requested?',
      'What address is mentioned?'
    ];
  }

  // Filter out any prompts that have already been used in this conversation
  const filtered = candidates.filter(chip => !usedQueries.has(chip.toLowerCase().trim()));
  
  // Return top 3-4 suggestions
  return filtered.slice(0, 4);
}

// Helper to find matching answer for chat query with strict document grounding
export function getSmartAssistantReply(userText, currentPetition) {
  const lower = userText.toLowerCase().trim();
  
  if (!currentPetition) {
    return "Please upload a petition document first.";
  }

  // Check specific matches in the petition database
  for (const item of currentPetition.qaDatabase) {
    for (const match of item.questionMatches) {
      if (lower.includes(match)) {
        return item.answer;
      }
    }
  }

  // Common queries: Date / Time
  if (lower.includes('date') || lower.includes('when') || lower.includes('submitted')) {
    return `The petition has a receipt stamp date of **16-02-2026** at the District Collectorate Grievance Day Cell.`;
  }

  // Common queries: Urgency / Priority
  if (lower.includes('urgent') || lower.includes('priority')) {
    return `Based on the grievance (road blockage and rainfall transit hazard), this issue carries **Medium / High Civic Priority**. Please verify urgency guidelines before filing in the official portal.`;
  }

  // Common queries: Enclosures / Attachments
  if (lower.includes('attachment') || lower.includes('enclosure') || lower.includes('documents attached')) {
    return `The document mentions the following enclosures: **1. Photographs of damaged road (2 copies)**, **2. Copy of Aadhaar Card**.`;
  }

  // Fallback factual response
  return `Based on the uploaded petition (${currentPetition.fileName}), the summary is: "${currentPetition.summary}". You can ask specific questions about the petitioner, location, department, or requested action.`;
}
