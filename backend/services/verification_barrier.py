import re
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

STOPWORDS_TAMIL = {
    "மற்றும்", "ஆகிய", "என்ற", "சார்ந்த", "கொண்டு", "மூலம்", "உள்ள", "குறித்து", "செய்து",
    "உள்ளது", "வசித்து", "வருகிறார்", "கோரி", "மனு", "அளித்துள்ளார்", "நடவடிக்கை",
    "the", "and", "for", "with", "from", "that", "this", "have", "has", "was", "are", "been"
}


class VerificationBarrier:
    """
    Anti-Hallucination & Grounding Verification Barrier (Google-grade Domain Service):
    Enforces strict grounding validation against source OCR document text:
    1. Content Word Grounding: >= 60% of content words in a claim must appear in the SAME source chunk.
    2. Digit Sequence Grounding: Every sequence of digits must exist in the source document.
    3. Blocks fabricated numbers and ungrounded claims.
    """

    def __init__(self, stopwords=STOPWORDS_TAMIL, min_chunk_ratio: float = 0.60):
        self.stopwords = stopwords
        self.min_chunk_ratio = min_chunk_ratio

    def verify_claims(self, analysis: Dict[str, Any], doc_text: Any) -> Dict[str, Any]:
        """
        Validates generated AI claims against source text chunks.
        Computes grounding_score (0.0 to 1.0) and hallucination_score (0.0 to 1.0).
        """
        claims = analysis.get("claims", [])
        if not claims:
            summary = analysis.get("description_summary_tamil", "")
            if summary:
                claims = [{"text": summary[:140], "source_page": 1, "confidence": 0.90}]
            else:
                claims = []

        # Prepare chunk strings
        chunks: List[str] = []
        if isinstance(doc_text, list):
            for c in doc_text:
                t = c.get("chunk_text", "") if isinstance(c, dict) else str(c)
                if t:
                    chunks.append(t)
        else:
            raw_s = str(doc_text or "")
            split_chunks = [p.strip() for p in raw_s.split("--- பக்கம் ") if p.strip()]
            chunks = split_chunks if split_chunks else [raw_s]

        full_doc_str = " ".join(chunks)
        doc_lower = full_doc_str.lower()
        verified_count = 0

        for claim in claims:
            claim_text = str(claim.get("text", "")).strip()
            if not claim_text:
                claim["verified"] = False
                claim["confidence"] = 0.0
                continue

            # 1. Strict Digit Sequence Check
            claim_digits = re.findall(r'\d+', claim_text)
            digits_ok = all(d in full_doc_str for d in claim_digits)
            if not digits_ok:
                claim["verified"] = False
                claim["confidence"] = 0.0
                continue

            # 2. Content Word Grounding Check (>= 60% in the SAME source chunk)
            words = [w for w in re.findall(r'[\w\u0B80-\u0BFF]+', claim_text.lower()) if len(w) > 3 and w not in self.stopwords]
            if not words:
                is_sub = claim_text.lower() in doc_lower
                claim["verified"] = is_sub
                claim["confidence"] = 1.0 if is_sub else 0.0
                if is_sub:
                    verified_count += 1
                continue

            max_chunk_ratio = 0.0
            for ch in chunks:
                ch_lower = ch.lower()
                matched_in_chunk = sum(1 for w in words if w in ch_lower)
                ratio = matched_in_chunk / len(words)
                if ratio > max_chunk_ratio:
                    max_chunk_ratio = ratio

            if max_chunk_ratio >= self.min_chunk_ratio:
                claim["verified"] = True
                claim["confidence"] = round(max_chunk_ratio, 2)
                verified_count += 1
            else:
                claim["verified"] = False
                claim["confidence"] = 0.0

        # Post-check: regex-scan entire AI summary for ungrounded digit sequences
        summary_all = f"{analysis.get('description_summary_tamil', '')} {analysis.get('description_summary_english', '')}"
        summary_digits = re.findall(r'\d+', summary_all)
        unverified_digits = [d for d in summary_digits if d not in full_doc_str]
        if unverified_digits:
            analysis["flagged_unverified_digits"] = unverified_digits
            logger.warning(f"Anti-hallucination barrier flagged unverified digits in summary: {unverified_digits}")

        total = len(claims) if claims else 1
        hallucination_score = round((total - verified_count) / total, 2)
        if unverified_digits:
            hallucination_score = min(1.0, round(hallucination_score + 0.25, 2))

        analysis["claims"] = claims
        analysis["hallucination_score"] = max(0.0, min(1.0, hallucination_score))
        analysis["grounding_score"] = round(1.0 - analysis["hallucination_score"], 2)
        return analysis


verification_barrier = VerificationBarrier()
