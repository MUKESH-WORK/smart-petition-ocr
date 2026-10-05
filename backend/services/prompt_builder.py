import json
from typing import Dict, Any, Optional, List

SYSTEM_PROMPT_COGNITIVE = (
    "You are an expert Tamil Nadu administrative petition extraction AI. "
    "Extract required administrative entities into strict JSON format only. Do not invent facts."
)


class PromptBuilder:
    """
    Cognitive Prompt Engineering Service:
    Constructs strict, schema-adherent system and user prompts for Tamil petition analysis.
    Optimized for fast inference and deterministic field grounding.
    """

    @staticmethod
    def build_analysis_prompt(
        zone_a_header: str,
        zone_b_body: str,
        candidates_json: str = "",
        authoritative_taxonomy: Optional[Dict[str, Any]] = None,
        candidates: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        # Keep context concise to ensure fast CPU inference
        header_text = (zone_a_header or "").strip()[:400]
        body_text = (zone_b_body or "").strip()[:500]

        # Case 1: Confident DB Taxonomy already pre-resolved from Master DB
        if authoritative_taxonomy:
            tax_id = authoritative_taxonomy.get("id") or authoritative_taxonomy.get("taxonomy_id")
            tax_sub = authoritative_taxonomy.get("grievance_sub_type") or authoritative_taxonomy.get("grievance_subtype", "")
            tax_dept = authoritative_taxonomy.get("department", "")
            tax_block = f"""[AUTHORITATIVE TAXONOMY (Pre-Resolved from Master DB)]
ID: {tax_id} | {tax_sub} | {tax_dept}"""
            rules_tax = "6. Taxonomy: Pre-resolved as authoritative above. Do not modify."
            json_tax_field = ""

        # Case 2: Ambiguous candidates provided (top-5 compact lines)
        elif candidates:
            compact_cands = []
            for c in candidates[:5]:
                cid = c.get("taxonomy_id") or c.get("Taxonomy_ID") or c.get("id")
                csub = c.get("grievance_sub_type") or c.get("Grievance Sub Type") or ""
                cdept = c.get("department") or c.get("Department") or ""
                compact_cands.append(f"ID: {cid} | {csub} | {cdept}")
            cands_str = "\n".join(compact_cands)
            tax_block = f"""[TAXONOMY CANDIDATES]
{cands_str}"""
            rules_tax = "6. Selected_Taxonomy_ID: Select the single matching candidate ID integer from TAXONOMY CANDIDATES, or null if none."
            json_tax_field = '\n  "Selected_Taxonomy_ID": null,'

        # Case 3: Legacy string fallback
        elif candidates_json:
            tax_block = f"""[TAXONOMY CANDIDATES]
{candidates_json[:500]}"""
            rules_tax = "6. Selected_Taxonomy_ID: Select the matching candidate ID integer from TAXONOMY CANDIDATES, or null."
            json_tax_field = '\n  "Selected_Taxonomy_ID": null,'
        else:
            tax_block = ""
            rules_tax = ""
            json_tax_field = ""

        tax_section = f"\n{tax_block}\n" if tax_block else ""

        return f"""Extract Tamil administrative petition fields into strict JSON:

[ZONE A: SENDER HEADER]
{header_text}

[ZONE B: NARRATIVE]
{body_text}{tax_section}
RULES:
1. Petitioner_Name: Exact name from sender block (அனுப்புநர்) or signature (இப்படிக்கு).
2. Father_Husband_Name: Name following த/பெ or க/பெ, or null if absent.
3. Gender: "Male" or "Female" or null based on name/relationship.
4. Phone_Number: 10-digit mobile number from sender or null.
5. Address, Taluk, Village, District: Extract full address, taluk, village/town, district.
{rules_tax}
7. Grievance_Subject: Short request subject line (e.g. from பொருள்).

JSON FORMAT:
{{
  "Petitioner_Name": "Petitioner name from sender or signature",
  "Father_Husband_Name": null,
  "Gender": "Male | Female | null",
  "Complainant_Signatory": null,
  "Phone_Number": "10-digit mobile or null",
  "Address": "Full sender address",
  "Taluk": "Taluk name",
  "Village": "Village or town name",
  "District": "District name",{json_tax_field}
  "Grievance_Subject": "Request subject from petition"
}}"""

    @staticmethod
    def build_administrative_description_prompt(facts: Dict[str, Any], doc_context: str = "") -> str:
        """Constructs a targeted prompt to draft the official Tamil description from verified facts."""
        facts_summary = (
            f"Petitioner: {facts.get('petitioner_name')}\n"
            f"District: {facts.get('district')}\n"
            f"Taluk: {facts.get('taluk')}\n"
            f"Village: {facts.get('village')}\n"
            f"Street: {facts.get('street_name')}\n"
            f"Department: {facts.get('department')}\n"
            f"Grievance Type: {facts.get('grievance_type')}\n"
            f"Grievance Subtype: {facts.get('grievance_subtype')}\n"
            f"Requested Action / Subject: {facts.get('requested_action') or facts.get('grievance_subject')}\n"
        )
        return f"""Based ONLY on the verified facts below, draft a concise 1-2 sentence official Tamil grievance description (அலுவலக நடை).

[VERIFIED STRUCTURED FACTS]
{facts_summary}

[CONTEXT SNIPPET]
{(doc_context or "")[:400]}

INSTRUCTIONS:
1. Write in formal Tamil administrative format (அலுவலக நடை):
   "மனுதாரர் [பெயர்], [பகுதி விவரம்] [மனுதாரரின் உண்மையான கோரிக்கை] உரிய நடவடிக்கை எடுக்குமாறு கோரிக்கை விடுத்துள்ளார்."
2. Ground strictly in the verified facts. Do not invent any new details, names, or locations.
3. Prohibited conversational phrasing: DO NOT use "கூறியவர்", "தெரிவித்தவர்", "செய்து கூறியவர்", "செய்ததாக கூறியவர்", "ஏற்படுத்துவதாக கூறியவர்".
4. Return ONLY a JSON object: {{"description_summary_tamil": "..."}}
"""


prompt_builder = PromptBuilder()

