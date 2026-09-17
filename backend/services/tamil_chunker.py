import re
from typing import List, Dict, Any, Optional


class TamilSemanticChunker:
    """
    Split on Tamil sentence boundaries.
    Preserve tables as atomic units.
    Max 1500 chars, overlap 200 chars.
    """

    SENTENCE_ENDERS = r'[।.?\n]+'
    TABLE_PATTERNS = [
        r'வ\.எண்\s*\|',
        r'துறை\s*\|',
        r'தொகை\s*\|',
        r'ஒதுக்கீடு\s*\|',
        r'புல\s*எண்\s*\|',
        r'விவரம்\s*\|'
    ]

    def _is_table(self, text: str) -> bool:
        for pattern in self.TABLE_PATTERNS:
            if re.search(pattern, text):
                return True
        # Check if contains multiple pipe delimiters
        if text.count("|") >= 4 and "\n" in text:
            return True
        return False

    def _get_overlap(self, sentences: List[str], overlap_chars: int = 200) -> str:
        accumulated = []
        char_count = 0
        for sent in reversed(sentences):
            if char_count + len(sent) <= overlap_chars:
                accumulated.insert(0, sent)
                char_count += len(sent)
            else:
                break
        return " ".join(accumulated) + " " if accumulated else ""

    def _make_chunk(self, text: str, page_number: int, index: int, sentences: List[str], metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {
            "text": text.strip(),
            "page_number": page_number,
            "index": index,
            "char_count": len(text.strip()),
            "sentence_count": len(sentences),
            "is_table": False,
            "metadata": metadata or {}
        }

    def split(self, text: str, page_number: int, metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        if not text or not text.strip():
            return []

        if self._is_table(text):
            return [{
                "text": text.strip(),
                "page_number": page_number,
                "index": 0,
                "char_count": len(text.strip()),
                "sentence_count": 1,
                "is_table": True,
                "metadata": metadata or {}
            }]

        sentences = [s.strip() for s in re.split(self.SENTENCE_ENDERS, text) if s.strip()]
        if not sentences:
            return []

        chunks = []
        current = ""
        current_sents = []
        chunk_idx = 0

        for sent in sentences:
            if len(current) + len(sent) + 1 <= 1500:
                current += sent + " "
                current_sents.append(sent)
            else:
                if current.strip():
                    chunks.append(self._make_chunk(current, page_number, chunk_idx, current_sents, metadata))
                    chunk_idx += 1
                overlap = self._get_overlap(current_sents, 200)
                current = overlap + sent + " "
                current_sents = [sent]

        if current.strip():
            chunks.append(self._make_chunk(current, page_number, chunk_idx, current_sents, metadata))

        return chunks


tamil_chunker = TamilSemanticChunker()
