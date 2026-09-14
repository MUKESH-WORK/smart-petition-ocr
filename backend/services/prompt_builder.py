import json
from typing import Dict, Any, Optional

SYSTEM_PROMPT_COGNITIVE = (
    "You are an expert Tamil Nadu administrative petition extraction AI. "
    "Your task is to extract administrative entities and map the petition to the CM Helpline Master Taxonomy."
)


class PromptBuilder:
    """
    Cognitive Prompt Engineering Service:
    Constructs strict, schema-adherent system and user prompts for Tamil petition analysis.
    """

    @staticmethod
    def build_analysis_prompt(
        zone_a_header: str,
        zone_b_body: str,
        candidates_json: str
    ) -> str:
        return f"""### STRICT EXTRACTION & SUMMARY RULES:

1. NOISE PRE-FILTERING:
   - Discard all OCR watermark/scanner noise strings (e.g., "பிளூப்ரீவ்", "ப்ளூப்ரிண்ட்", "வட்டாராசிரியர்", "ராஷ்ட்ர கலா", "தோட்டாரன்", "டி. சி. பட்டணம்", "அடிசூ", "DocScanner", "CamScanner").
   - Extract the real petitioner name from valid Tamil words that appear in the sender block and signature (e.g., "சந்திரசேகர்").

2. FATHER / HUSBAND NAME:
   - Read the line starting with "த/பெ." or "க/பெ." or the parent name following the petitioner (e.g., "துரைராஜ்" / "த/பெ. துரைராஜ்", "சாமிநாதன்").
   - DO NOT confuse with occupation or narrative text.

3. PETITIONER IDENTIFICATION & DUAL-APPLICANT CONTEXT:
   - "Petitioner_Name": Extract the petitioner/beneficiary name (e.g., "சந்திரசேகர்", "S. செல்வி / S. தர்ஷிதன்").
   - "Complainant_Signatory": If a parent/guardian signs on behalf (e.g. "S. செல்வி"), extract their name, otherwise null.
   - "Phone_Number": Extract the 10-digit mobile number from sender or signature block, including multiline/split numbers (e.g. "78679 30184" or "78679\n30184" ➔ "7867930184", "9524385856").

4. VILLAGE & ADDRESS RESOLUTION:
   - Keep the full address preserving house numbers, landmark streets, and villages (e.g. "336-8, பனைப்பாளையம், கூரப்பாளையம், ஈரோடு", "3, சம்பாமேடு, ஊத்துக்குளிரோடு, புஞ்சைபாலத் தொழுவு, ஈரோடு - 638751").
   - "Village": Extract the Revenue Village ending with known suffixes like பாளையம்/பளையம்/தொழுவு/பட்டி (e.g., "கூரப்பாளையம்", "புஞ்சைபாலத் தொழுவு").
   - "Taluk": Set the correct administrative Taluk (e.g., "ஈரோடு"). NEVER set Taluk equal to the Revenue Village.
   - "District": Set the District name (e.g., "ஈரோடு").

5. METADATA PRIORITY ROUTING & TAXONOMY MATCHING:
   - Check the form metadata table/footer:
     * When Form Footer states "Revenue Dept" and "Free HSD" (or Free House Site / Natham Patta):
       - Department: Revenue and Disaster Management (REV)
       - Grievance Type: Natham Patta /Free House Site Patta
       - Grievance Sub Type: Natham Patta /Free House Site Patta
       - Responsible Officer: Tahsildar, Erode
     * When Header/Department is "Information Technology" and issue involves "Aadhar":
       - Department: Information Technology Department (IT)
       - Grievance Type: Application Related Complaints - CeG
       - Grievance Sub Type: eSevai - Complaint related to Aadhaar Enrolment
       - Responsible Officer: Special Tahsildar TACTV / e-sevai helpdesk
   - You MUST select one exact option from the provided "TAXONOMY CANDIDATES" array.

6. NARRATIVE EXTRACTION & SUMMARY COMPLETENESS:
   - SUMMARY COMPLETENESS: Output a complete, coherent 2-sentence summary in formal administrative Tamil.
   - NEVER output raw OCR noise or broken garbage text.
   - For Free House Site Patta (Free HSD):
     "மனுதாரர் சந்திரசேகர், ஈரோடு மாவட்டம் கூரப்பாளையம் பகுதியில் இலவச வீட்டு மனைப் பட்டா (Free House Site Patta) வழங்கிடக் கோரி ஈரோடு வட்டார வருவாய் வட்டாட்சியருக்கு மனு அளித்துள்ளார்."
   - For Aadhaar name correction:
     "மனுதாரர் S. செல்வி தனது மகன் S. தர்ஷிதன் என்பவரின் பெயரை தமிழ்நாடு அரசு கெசட் மற்றும் பள்ளி மாற்றுச் சான்றிதழில் (TC) பெயர் மாற்றம் செய்து, அதன் மூலமாக இ-சேவை மையத்தில் விண்ணப்பித்தும் ஆதார் அட்டை பெயர் மாற்றம் நிராகரிக்கப்பட்டதால், உரிய பெயர் மாற்றம் செய்து தர நடவடிக்கை கோரியுள்ளார்."

---

### INPUT PETITION TEXT:
[ZONE A: SENDER HEADER]
{zone_a_header}

[ZONE B: PETITION NARRATIVE]
{zone_b_body}

---

### TAXONOMY CANDIDATES (From CM Helpline Master Sheet):
{candidates_json}

---

### REQUIRED JSON OUTPUT:
{{
  "Petitioner_Name": "Extracted Petitioner Name (e.g. சந்திரசேகர்)",
  "Complainant_Signatory": "Complainant if submitting on behalf, or null",
  "Father_Husband_Name": "Father or Husband Name (e.g. துரைராஜ்)",
  "Phone_Number": "10-Digit Mobile (e.g. 7867930184)",
  "Address": "Full Address (e.g. 336-8, பனைப்பாளையம், கூரப்பாளையம், ஈரோடு)",
  "Taluk": "Taluk Name (e.g. ஈரோடு)",
  "Village": "Village Name (e.g. கூரப்பாளையம்)",
  "District": "District Name (e.g. ஈரோடு)",
  "Selected_Taxonomy": {{
    "Department": "Exact Department string from candidates",
    "Grievance_Type": "Exact Grievance Type string from candidates",
    "Grievance_Sub_Type": "Exact Grievance Sub Type string from candidates",
    "Sub_Department": "Exact Sub Department from candidates",
    "Responsible_officer": "Exact Responsible officer from candidates"
  }},
  "Description": "Complete 2-sentence Tamil executive summary starting with 'மனுதாரர்...'"
}}
"""


prompt_builder = PromptBuilder()
