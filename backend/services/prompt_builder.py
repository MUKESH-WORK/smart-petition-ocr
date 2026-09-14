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
   - Extract the real petitioner name strictly from valid Tamil words that appear in the sender block (அனுப்புநர்) or closing signature block. NEVER invent names or output examples.

2. FATHER / HUSBAND NAME:
   - Read the line starting with "த/பெ." or "க/பெ." or parent name following the petitioner (e.g., "த/பெ. [பெயர்]").
   - If not mentioned in the petition, set to null. DO NOT confuse with occupation or narrative text.

3. PETITIONER IDENTIFICATION & DUAL-APPLICANT CONTEXT:
   - "Petitioner_Name": Extract the exact petitioner name from the sender block under 'அனுப்புநர்' or closing signature 'இப்படிக்கு, (பெயர்)'.
   - "Complainant_Signatory": If a parent/guardian signs on behalf of a beneficiary, extract their name, otherwise null.
   - "Phone_Number": Extract the 10-digit mobile number from sender or signature block (e.g., starting with 6, 7, 8, or 9), including split/multiline numbers.

4. VILLAGE & ADDRESS RESOLUTION:
   - Keep the full address preserving house numbers, landmark streets, and villages.
   - "Village": Extract the Revenue Village / Post (e.g. text before (Po) / அஞ்சல் or suffixes like பாளையம்/தொழுவு/பட்டி).
   - "Taluk": Set the correct administrative Taluk (e.g., text before (TK) / வட்டம்). NEVER set Taluk equal to the Revenue Village.
   - "District": Set the District name (e.g., ஈரோடு).

5. METADATA PRIORITY ROUTING & TAXONOMY MATCHING:
   - You MUST select one exact option from the provided "TAXONOMY CANDIDATES" array that matches the petition core grievance.
   - If the petition is regarding drinking water (குடிநீர்), select the matching Drinking Water entry.
   - If the petition is regarding Free HSD / Patta (வீட்டு மனைப் பட்டா), select the matching Patta entry.
   - If the petition is regarding Aadhaar / e-Sevai, select the matching IT / Aadhaar entry.

6. NARRATIVE EXTRACTION & SUMMARY COMPLETENESS:
   - SUMMARY COMPLETENESS: Output a complete, coherent 2-sentence summary in formal administrative Tamil starting with "மனுதாரர் [பெயர்], ...".
   - Ground the summary strictly on the actual grievance described in the text (e.g. குடிநீர் விநியோகம், பட்டா, கல்வி, சாலை).
   - NEVER output raw OCR noise or unrelated schemes.

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
  "Petitioner_Name": "Exact petitioner name strictly from sender block or signature, NEVER an example name",
  "Complainant_Signatory": "Complainant if submitting on behalf, or null",
  "Father_Husband_Name": "Father or Husband Name if present, or null",
  "Phone_Number": "10-Digit Mobile from sender block, or null",
  "Address": "Full Address from sender block",
  "Taluk": "Taluk Name from sender block or petition",
  "Village": "Village Name from sender block or petition",
  "District": "District Name",
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
