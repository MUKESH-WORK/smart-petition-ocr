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
        # Keep context concise to ensure fast CPU inference
        header_text = (zone_a_header or "").strip()[:600]
        body_text = (zone_b_body or "").strip()[:800]
        return f"""Extract Tamil administrative petition fields into strict JSON:

[ZONE A: SENDER HEADER]
{header_text}

[ZONE B: NARRATIVE]
{body_text}

[TAXONOMY CANDIDATES]
{candidates_json}

RULES:
1. Petitioner_Name: Exact name from sender block (அனுப்புநர்) or signature (இப்படிக்கு).
2. Father_Husband_Name: Name following த/பெ or க/பெ, or null if absent.
3. Gender: "Male" or "Female" or null based on name/relationship.
4. Phone_Number: 10-digit mobile number from sender or null.
5. Address, Taluk, Village, District: Extract full address, taluk, village/town, district (e.g. ஈரோடு).
6. Selected_Taxonomy: Select the best matching entry from TAXONOMY CANDIDATES.
7. Description: 2-sentence formal administrative Tamil summary starting with "மனுதாரர் [பெயர்], ...". Do not copy raw text.

JSON FORMAT:
{{
  "Petitioner_Name": "Petitioner name from sender or signature",
  "Father_Husband_Name": "Father or husband name or null",
  "Gender": "Male | Female | null",
  "Complainant_Signatory": "Signatory if signing on behalf or null",
  "Phone_Number": "10-digit mobile or null",
  "Address": "Full sender address",
  "Taluk": "Taluk name",
  "Village": "Village or town name",
  "District": "District name",
  "Selected_Taxonomy": {{
    "Department": "Exact Department from candidates",
    "Grievance_Type": "Exact Grievance Type from candidates",
    "Grievance_Sub_Type": "Exact Grievance Sub Type from candidates",
    "Sub_Department": "Exact Sub Department from candidates",
    "Responsible_officer": "Exact Responsible officer from candidates"
  }},
  "Description": "2-sentence formal administrative Tamil summary starting with 'மனுதாரர்...'"
}}"""


prompt_builder = PromptBuilder()
