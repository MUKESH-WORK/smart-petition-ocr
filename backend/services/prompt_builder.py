import json
from typing import Dict, Any


class PromptBuilder:
    """
    Cognitive Prompt Engineering Service:
    Constructs strict, schema-adherent system and user prompts for Tamil petition analysis.
    """

    @staticmethod
    def build_analysis_prompt(doc_context: str, verified_entities: Dict[str, Any]) -> str:
        verified_json = json.dumps(verified_entities, ensure_ascii=False)
        return f"""VERIFIED ENTITIES: {verified_json} — do NOT change, reformat, or re-derive any value.
CRITICAL MANDATE: Identifiers (phone, alternate_phone, survey_no, file_number, petition_no, date) MUST come strictly from VERIFIED ENTITIES only. If absent in VERIFIED ENTITIES, output "[தகவல் இல்லை]". NEVER re-extract or fabricate identifiers from OCR text.

Analyze this Tamil government grievance petition and extract all structured details into a JSON object:
{{
  "petitioner_name": "Full name of the petitioner from the sender/applicant section, or null",
  "father_husband_name": "Father or husband name if specified, or null",
  "gender": "Male or Female",
  "phone": "Primary 10-digit mobile number strictly from VERIFIED ENTITIES or '[தகவல் இல்லை]'",
  "alternate_phone": "Secondary phone number strictly from VERIFIED ENTITIES or null",
  "door_no": "Door/House number, or null",
  "street_name": "Street or road name, or null",
  "village": "Village, town, or area, or null",
  "firka": "Firka or post office area, or null",
  "taluk": "Taluk name, or null",
  "district": "District name (if explicitly stated in document, otherwise null)",
  "pincode": "6-digit postal pincode strictly from VERIFIED ENTITIES or null",
  "full_address": "Complete residential address extracted from document, or null",
  "grievance_type": "Specific grievance subject (e.g. ஓய்வூதியம், பட்டா மாறுதல், ஆக்கிரமிப்பு, உதவித்தொகை, குடிநீர், சாலை, மின்சாரம், சான்றிதழ்)",
  "grievance_subtype": "Specific grievance sub-category or request details (e.g. Destitute Widow Pension Scheme (DWPS) / ஆதரவற்ற விதவை உதவித்தொகை)",
  "department": "Government Department responsible for this grievance (e.g. Revenue and Disaster Management (REV), Rural Development and Panchayat Raj Department (RDPR), Municipal Administration and Water Supply (MAWS), Energy Department (ENERGY), Social Welfare and Women Empowerment Department (SWNM))",
  "sub_department": "Sub department or null",
  "survey_no": "Survey number or SF No strictly from VERIFIED ENTITIES or null",
  "priority": "HIGH or MEDIUM or LOW",
  "description_summary_tamil": "Clear, objective administrative summary in Tamil explaining petitioner identity, relation, location, background reason, and exact scheme/action requested",
  "description_summary_english": "Accurate professional 2-3 sentence summary in English"
}}

CRITICAL EXTRACTION GUIDELINES:
1. Petitioner vs Spouse/Father:
   - If sender states 'Name W/o Husband' or 'க/பெ', petitioner_name is Name, father_husband_name is Husband, gender is Female. NEVER combine husband's name into petitioner_name!
   - If sender states 'Name S/o Father' or 'த/பெ', petitioner_name is Name, father_husband_name is Father, gender is Male.
   - If sender states 'Name D/o Father' or 'ம/பெ', petitioner_name is Name, father_husband_name is Father, gender is Female.
2. Official Administrative Summary (description_summary_tamil):
   - Formulate a formal, grammatically sound 2-3 sentence administrative summary in Tamil (DRO பார்வைக்கான மனு சுருக்கம்).
   - Format: 'மனுதாரர் [பெயர்] (தந்தை/கணவர்: [பெயர்]), [பகுதி/கிராமம், வட்டம்/மாவட்டம்] பகுதியில் வசித்து வருகிறார். [மனுவிற்கான பின்னணி சூழல் / காரணம்], [கோரப்படும் அரசு திட்டம் அல்லது நிர்வாக நடவடிக்கை] வழங்கிட / நிறைவேற்றிடக் கோரி மனு அளித்துள்ளார்.'
   - State the factual grievance cause accurately: whether it is social welfare pension, patta transfer, land survey, boundary dispute, encroachment eviction, drinking water, street light, road, ration card, certificate, or civil grievance.
   - NEVER copy broken, ungrammatical, or colloquial handwritten phrasing verbatim (e.g. do not say 'அவருக்கு இறந்துவிட்டார்').
   - PRESERVE all essential grievance keywords and specific scheme names.
   - Do NOT fabricate default district or taluk names if absent from document text.
3. Office Stamp / Docket:
   - If the petition has an official docket stamp with Department (Revenue), Grievance Type (Pension), Subtype (DWP), and Officer (Tahsildar, Kodumudi), utilize these official classifications.
4. Sign-off / Signature at End:
   - Check the end of the petition. If signed 'இப்படிக்கு, (பெயர்)' or 'Signature (பெயர்)', that name is the petitioner's legal name.
5. Grievance Cause vs Reference Annexures:
   - Distinguish the actual grievance prayer from listed annexures. If annexures list past patta or police complaints, check the main prayer to determine grievance_type.
6. Strict Third-Person Summary:
   - Summary MUST strictly use third-person phrasing ('மனுதாரர் [பெயர்]... கோரியுள்ளார்'). NEVER write in first-person ('நான்', 'நாங்கள்', 'உத்தரவிட்டேன்').

Respond ONLY with valid JSON.

Document Text:
{doc_context}
"""


prompt_builder = PromptBuilder()
