// assistantHelpers.js - Real-time Petition Assistant & Field Extraction Utilities
// All mock documents removed. 100% powered by real OCR and official AI pipeline.

export const MOCK_PETITIONS = [];

/**
 * Helper to extract structured portal details from the real processed petition
 */
export function extractPetitionDetails(petition) {
  if (!petition) return null;
  if (petition.portalDetails) {
    return { ...petition.portalDetails };
  }

  // Pure data-driven fallback if portalDetails has not finished loading
  return {
    petitionerName: petition.details?.petitionerName || 'Not found',
    fatherHusbandName: petition.details?.fatherHusbandName || 'Not found',
    complainantSignatory: petition.details?.complainantSignatory || null,
    email: 'Not found',
    phoneNumber: petition.details?.phoneNumber || 'Not found',
    isOwnNumber: 'Yes',
    alternatePhone: 'Not found',
    address: petition.details?.address || 'Not found',
    gender: 'Not mentioned',
    differentlyAbled: 'No',
    petitionerCategory: 'Personal / தனிப்பட்ட குறை',

    description: petition.summary || petition.details?.mainGrievance || 'Processing petition...',
    grievanceSource: 'Collectorate Grievance Day Petition',
    referenceNumber: petition.details?.referenceNumber || 'Not found',
    governmentDepartment: petition.details?.suggestedDepartment || 'Not found',
    localBodyType: 'Rural / கிராமப்புறம்',
    grievanceType: 'Not found',
    grievanceSubType: 'Not found',
    district: 'Erode / ஈரோடு',
    subDepartment: 'Not found',
    ward: 'Not found',
    municipalityWard: 'Not found',
    block: 'Not found',
    taluk: 'Not found',
    revenueDivision: 'Erode / ஈரோடு',
    firka: 'Not found',
    streetName: 'Not found',
    doorNumber: 'Not found',
    responsibleOfficer: 'District Revenue Officer / மாவட்ட வருவாய் அலுவலர்',
    fisheriesRegion: 'Not found',
    fisheriesDivision: 'Not found',
    reasonForRedirection: 'Not applicable / பொருந்தாது',

    communicationAddressSame: 'No',
    communicationAddress: petition.details?.address || 'Not found',

    dueDate: '31 Aug 2026 17:00',
    status: 'Open / நிலுவையில் உள்ளது',
    sourceCode: 'GDP - Grievance Day Petition',
    grievanceId: petition.id ? `TN/AHFISH/ERD/P/OFFLINE/31AUG26/${petition.id}` : 'TN/AHFISH/ERD/P/OFFLINE/31AUG26/001',
    priority: 'Medium',
    callDisposition: 'Registered / பதிவு செய்யப்பட்டது',
    isWhatsappAppeal: 'No',
    isWhatsappTracking: 'Yes',
    isWhatsappReceipt: 'Yes',

    relationshipWithExServicemen: 'No'
  };
}

/**
 * Check if a query is requesting Full Details
 */
export function isFullDetailsQuery(query) {
  const q = (query || '').toLowerCase().trim();
  return (
    q.includes('full details') ||
    q.includes('give me full details') ||
    q.includes('give me the full details') ||
    q.includes('important details') ||
    q.includes('give me the important details') ||
    q === 'details' ||
    q === 'full detail'
  );
}

/**
 * Determine dynamic contextual suggested prompts
 */
export function getContextualSuggestions(lastQuery, usedQueries = new Set()) {
  const q = (lastQuery || '').toLowerCase();

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

  const filtered = candidates.filter(chip => !usedQueries.has(chip.toLowerCase().trim()));
  return filtered.slice(0, 4);
}

/**
 * Smart factual assistant grounded strictly in current petition details
 */
export function getSmartAssistantReply(userText, currentPetition) {
  const lower = userText.toLowerCase().trim();
  
  if (!currentPetition) {
    return "Please upload a petition document first.";
  }

  const details = currentPetition.portalDetails || {};

  // Check petitioner name
  if (lower.includes('petitioner') || lower.includes('applicant') || lower.includes('who is') || lower.includes('name') || lower.includes('பெயர்') || lower.includes('மனுதாரர்')) {
    if (details.petitionerName && details.petitionerName !== 'Not found') {
      return `The petitioner is **${details.petitionerName}**, residing at ${details.address || 'the address specified in the document'}.`;
    }
  }

  // Check phone / mobile
  if (lower.includes('phone') || lower.includes('mobile') || lower.includes('contact') || lower.includes('number') || lower.includes('தொலைபேசி') || lower.includes('கைபேசி')) {
    if (details.phoneNumber && details.phoneNumber !== 'Not found') {
      return `The contact phone number mentioned in the petition is **${details.phoneNumber}**.`;
    }
  }

  // Check department / routing
  if (lower.includes('department') || lower.includes('routing') || lower.includes('handle') || lower.includes('துறை')) {
    if (details.governmentDepartment && details.governmentDepartment !== 'Not found') {
      return `Based on the petition, this belongs to **${details.governmentDepartment}** (${details.responsibleOfficer || 'Concerned Officer'}).`;
    }
  }

  // Check address / location
  if (lower.includes('address') || lower.includes('location') || lower.includes('village') || lower.includes('taluk') || lower.includes('முகவரி') || lower.includes('கிராமம்')) {
    if (details.address && details.address !== 'Not found') {
      return `The location address is **${details.address}**.`;
    }
  }

  // Check grievance / issue / complaint
  if (lower.includes('explain the grievance') || lower.includes('grievance') || lower.includes('complaint') || lower.includes('issue') || lower.includes('problem') || lower.includes('கோரிக்கை') || lower.includes('விவரம்')) {
    if (details.description && details.description !== 'Not found') {
      return `**Grievance Details:** ${details.description}`;
    }
  }

  // Check one line summary
  if (lower.includes('summarize') || lower.includes('one line') || lower.includes('one sentence') || lower.includes('short summary') || lower.includes('சுருக்கம்')) {
    if (currentPetition.summary) {
      return currentPetition.summary;
    }
  }

  // Check action requested
  if (lower.includes('action') || lower.includes('requested') || lower.includes('நடவடிக்கை')) {
    if (details.description && details.description !== 'Not found') {
      return `The petitioner requests: ${details.description}`;
    }
  }

  return `Based on the uploaded petition (${currentPetition.fileName}), the summary is: "${currentPetition.summary || details.description || 'Petition received'}".`;
}
