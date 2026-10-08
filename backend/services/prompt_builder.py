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
        subject_line: str = "",
        prayer_section: str = "",
    ) -> str:
        # Keep context concise to ensure fast CPU inference
        header_text = (zone_a_header or "").strip()[:400]
        body_text = (zone_b_body or "").strip()[:600]

        # Top 10 Candidates block (formatted for LLM verification)
        if candidates:
            compact_cands = []
            for c in candidates[:10]:
                cid = c.get("taxonomy_id") or c.get("Taxonomy_ID") or c.get("id")
                csub = c.get("grievance_sub_type") or c.get("grievance_subtype") or c.get("Grievance Sub Type") or ""
                ctype = c.get("grievance_type") or c.get("Grievance Type") or ""
                cdept = c.get("department") or c.get("Department") or ""
                coff = c.get("responsible_officer") or c.get("Responsible officer") or ""
                compact_cands.append(f"ID: {cid} | Dept: {cdept} | Type: {ctype} | Subtype: {csub} | Officer: {coff}")
            cands_str = "\n".join(compact_cands)
            tax_block = f"""[TOP 10 TAXONOMY CANDIDATES (FROM AUTHORITATIVE DATABASE)]
{cands_str}"""
            rules_tax = (
                "6. Selected_Taxonomy_ID: Select EXACTLY ONE matching integer ID from TOP 10 TAXONOMY CANDIDATES.\n"
                "   Priority: Subject > Requested Action (Prayer) > Domain Concept > Narrative Body.\n"
                "   CRITICAL RULES:\n"
                "   - If petition is for a pathway/road to a burial ground or crematorium (மயானம் / புதைகுழி / சுடுகாடு பாதை), select 'Pathway To Burial Ground' (Social Justice Department, ID 24), NEVER generic Road (RDPR).\n"
                "   - If petition is for veterinary hospital/animals (கால்நடை மருத்துவமனை), select Animal Husbandry (AHFISH), NEVER Agriculture/Horticulture.\n"
                "   - If petition is for water channel/waterbody encroachment (நீர்வழிப்பாதை ஆக்கிரமிப்பு), select Removal of Encroachments (WRD or REV), NEVER Forest.\n"
                "   - DO NOT classify by isolated incidental keywords.\n"
                "   - DO NOT invent any ID outside this list.\n"
                "7. Scope: 'PUBLIC' (community / infrastructure / pathway / village road / civic amenities) or "
                "'INDIVIDUAL' (personal welfare / pension / scholarship / patta) or 'MIXED' or 'UNKNOWN'."
            )
            json_tax_fields = (
                '\n  "Selected_Taxonomy_ID": 123,'
                '\n  "Scope": "PUBLIC | INDIVIDUAL | MIXED | UNKNOWN",'
            )
        elif authoritative_taxonomy:
            tax_id = authoritative_taxonomy.get("id") or authoritative_taxonomy.get("taxonomy_id")
            tax_sub = authoritative_taxonomy.get("grievance_sub_type") or authoritative_taxonomy.get("grievance_subtype", "")
            tax_dept = authoritative_taxonomy.get("department", "")
            tax_block = f"""[AUTHORITATIVE TAXONOMY (Pre-Resolved from Master DB)]
ID: {tax_id} | {tax_sub} | {tax_dept}"""
            rules_tax = "6. Selected_Taxonomy_ID: Use the pre-resolved ID integer above."
            json_tax_fields = f'\n  "Selected_Taxonomy_ID": {tax_id},\n  "Scope": "PUBLIC | INDIVIDUAL | MIXED | UNKNOWN",'
        elif candidates_json:
            tax_block = f"""[TAXONOMY CANDIDATES]
{candidates_json[:500]}"""
            rules_tax = "6. Selected_Taxonomy_ID: Select the matching candidate ID integer from TAXONOMY CANDIDATES, or null."
            json_tax_fields = '\n  "Selected_Taxonomy_ID": null,\n  "Scope": "PUBLIC | INDIVIDUAL | MIXED | UNKNOWN",'
        else:
            tax_block = ""
            rules_tax = ""
            json_tax_fields = ""

        # Section for extracted Subject & Prayer
        extracted_sections = []
        if subject_line:
            extracted_sections.append(f"[NORMALIZED SUBJECT LINE]\n{subject_line}")
        if prayer_section:
            extracted_sections.append(f"[REQUESTED ACTION / PRAYER]\n{prayer_section}")
        extracted_block = ("\n\n" + "\n\n".join(extracted_sections)) if extracted_sections else ""
        tax_section = f"\n\n{tax_block}" if tax_block else ""

        return f"""Extract Tamil administrative petition fields into strict JSON:

[ZONE A: SENDER HEADER]
{header_text}

[ZONE B: NARRATIVE]
{body_text}{extracted_block}{tax_section}

RULES:
1. Petitioner_Name: Exact name from sender block (அனுப்புநர்) or signature (இப்படிக்கு).
2. Father_Husband_Name: Name following த/பெ or க/பெ, or null if absent.
3. Gender: "Male" or "Female" or null based on name/relationship.
4. Phone_Number: 10-digit mobile number from sender or null.
5. Address, Taluk, Village, District: Extract full address, taluk, village/town, district.
{rules_tax}
8. Summary_Tamil: Concise 1-2 sentence formal administrative summary (அலுவலக நடை) matching the selected taxonomy:
   "மனுதாரர் [பெயர்], [பகுதி] [கோரிக்கை விவரம்] உரிய நடவடிக்கை எடுக்குமாறு கோரிக்கை விடுத்துள்ளார்."
9. Grievance_Subject: Short request subject line (e.g. from பொருள்).
10. Decision_Rationale: Very short 1-sentence reason for selected taxonomy.

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
  "District": "District name",{json_tax_fields}
  "Summary_Tamil": "மனுதாரர் [பெயர்], [பகுதி] [கோரிக்கை] உரிய நடவடிக்கை எடுக்குமாறு கோரிக்கை விடுத்துள்ளார்.",
  "Grievance_Subject": "Request subject from petition",
  "Decision_Rationale": "Short 1-sentence reason"
}}"""

    @staticmethod
    def build_taxonomy_verification_prompt(
        subject_line: str,
        prayer_section: str,
        body_context: str,
        candidates: List[Dict[str, Any]]
    ) -> str:
        """
        Dedicated Taxonomy Verification Prompt:
        Compares normalized subject, prayer, and context against Top 10 DB candidates.
        """
        compact_cands = []
        valid_ids = []
        for c in candidates[:10]:
            cid = c.get("taxonomy_id") or c.get("Taxonomy_ID") or c.get("id")
            csub = c.get("grievance_sub_type") or c.get("grievance_subtype") or ""
            ctype = c.get("grievance_type") or ""
            cdept = c.get("department") or ""
            coff = c.get("responsible_officer") or ""
            compact_cands.append(f"ID: {cid} | Dept: {cdept} | Type: {ctype} | Subtype: {csub} | Officer: {coff}")
            if cid is not None:
                valid_ids.append(cid)

        cands_str = "\n".join(compact_cands)
        ids_str = ", ".join(str(i) for i in valid_ids)

        return f"""Verify Tamil grievance petition taxonomy against the Top 10 database candidates.

[EXTRACTED SUBJECT]
{subject_line or "Not available"}

[REQUESTED ACTION / PRAYER]
{prayer_section or "Not available"}

[NARRATIVE CONTEXT]
{(body_context or "")[:500]}

[TOP 10 TAXONOMY CANDIDATES (FROM DATABASE)]
{cands_str}

RULES:
1. Select EXACTLY ONE integer ID from [{ids_str}]. You MUST NOT invent any other ID.
2. Classification priority:
   Subject line > Requested Action (Prayer) > Domain concepts > Relevant body context > Taxonomy meaning > Incidental terms.
3. DO NOT classify by incidental body keywords (e.g., 'விவசாயிகள்' or 'முதியவர்கள்' in body alone).
4. Determine Scope: 'PUBLIC' (civic infrastructure, road, burial ground, water channel) or 'INDIVIDUAL' (personal pension, personal scholarship, personal patta) or 'MIXED' or 'UNKNOWN'.
5. Draft formal concise Tamil description grounded strictly in petition facts.

RETURN STRICT JSON ONLY:
{{
  "selected_taxonomy_id": {valid_ids[0] if valid_ids else 1},
  "taxonomy_confidence": 0.95,
  "scope": "PUBLIC",
  "scope_confidence": 0.95,
  "summary_tamil": "மனுதாரர்...",
  "validation": "supported",
  "decision_rationale": "Short factual explanation"
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

