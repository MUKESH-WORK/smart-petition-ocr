import logging
import cv2
import numpy as np
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)


class RegionAnalyzer:
    """
    Production-grade Stage 1 Region Analyzer:
    - Stamp box detection (GDP intake stamp: மக்கள் குறை தீர்க்கும் நாள் மனு)
    - Stamp cell parsing & masking from body text
    - Photo and thumbprint rejection
    - Strikethrough detection on line crops (horizontal line profile heuristic)
    """

    STAMP_KEYWORDS = [
        "மக்கள் குறை", "தீர்க்கும் நாள்", "மனு நாள்", "நாள்:", "நாள் :",
        "தொடர்புடைய", "அரசுத்துறை", "துறை", "வகை", "குறை", "Home Prohib",
        "Land Grabbing", "கோரிக்கை"
    ]

    def detect_stamp_box(self, image: np.ndarray, is_first_page: bool = True) -> Optional[Tuple[int, int, int, int]]:
        """
        Detects rectangular GDP intake stamp box on upper 45% of Page 1.
        Returns (x, y, w, h) bounding box or None if not found.
        """
        if not is_first_page or image is None:
            return None

        try:
            h, w = image.shape[:2]
            upper_region_limit = int(h * 0.48)
            upper_crop = image[:upper_region_limit, :]

            gray = cv2.cvtColor(upper_crop, cv2.COLOR_BGR2GRAY) if len(upper_crop.shape) == 3 else upper_crop.copy()
            binary = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY_INV, 15, 8
            )

            # Detect horizontal and vertical lines to find table / stamp box
            scale = 20
            horizontal_size = max(1, w // scale)
            horizontal_structure = cv2.getStructuringElement(cv2.MORPH_RECT, (horizontal_size, 1))
            horizontal = cv2.erode(binary, horizontal_structure)
            horizontal = cv2.dilate(horizontal, horizontal_structure)

            vertical_size = max(1, h // scale)
            vertical_structure = cv2.getStructuringElement(cv2.MORPH_RECT, (1, vertical_size))
            vertical = cv2.erode(binary, vertical_structure)
            vertical = cv2.dilate(vertical, vertical_structure)

            table_mask = cv2.add(horizontal, vertical)
            contours, _ = cv2.findContours(table_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            candidates = []
            for c in contours:
                x, y, bw, bh = cv2.boundingRect(c)
                # Stamp box should be reasonably sized (width > 25% of page, height > 80px)
                if (bw > w * 0.22) and (bh > 70) and (bw * bh < (w * h * 0.35)):
                    candidates.append((x, y, bw, bh))

            if candidates:
                # Pick the largest candidate in upper region
                candidates.sort(key=lambda b: b[2] * b[3], reverse=True)
                return candidates[0]

            return None
        except Exception as e:
            logger.debug(f"Stamp detection fallback: {e}")
            return None

    def mask_stamp_region(self, image: np.ndarray, stamp_box: Optional[Tuple[int, int, int, int]]) -> np.ndarray:
        """Fills stamp region with white pixels to prevent duplicate body OCR."""
        if stamp_box is None:
            return image
        x, y, w, h = stamp_box
        masked = image.copy()
        # Leave a clean white rectangle for body OCR pass
        cv2.rectangle(masked, (x, y), (x + w, y + h), (255, 255, 255), -1)
        return masked

    def detect_non_text_regions(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Detects citizen photo or ink thumbprint regions to reject them from text OCR.
        Identifies high-density square/oval dark blobs.
        """
        regions = []
        try:
            h, w = image.shape[:2]
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image.copy()
            _, thresh = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY_INV)

            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for c in contours:
                x, y, bw, bh = cv2.boundingRect(c)
                aspect = float(bw) / float(bh) if bh > 0 else 0
                area = bw * bh
                # Passport photo: ~1:1 to 4:5 aspect, size between 120x120 and 450x450
                if 0.7 <= aspect <= 1.4 and (10000 < area < (w * h * 0.08)):
                    # Check ink density
                    roi = thresh[y:y+bh, x:x+bw]
                    density = np.count_nonzero(roi) / float(area)
                    if density > 0.45:
                        regions.append((x, y, bw, bh))
        except Exception as e:
            logger.debug(f"Non-text region detection: {e}")
        return regions

    def is_strikethrough(self, line_crop: np.ndarray) -> bool:
        """
        Strikethrough detection pass on line crops (fixes D7).
        Analyzes the horizontal line profile across the middle horizontal slice (30%-70% height).
        If a continuous or near-continuous horizontal dark line runs through the characters, flags True.
        """
        if line_crop is None or line_crop.size == 0:
            return False

        try:
            ch, cw = line_crop.shape[:2]
            if ch < 12 or cw < 30:
                return False

            gray = cv2.cvtColor(line_crop, cv2.COLOR_BGR2GRAY) if len(line_crop.shape) == 3 else line_crop.copy()
            binary = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY_INV, 15, 8
            )

            # Analyze middle horizontal slice (30% to 70% of line height)
            mid_start = int(ch * 0.30)
            mid_end = int(ch * 0.70)
            mid_slice = binary[mid_start:mid_end, :]

            # Horizontal projection profile
            horizontal_proj = np.sum(mid_slice == 255, axis=1)
            max_line_pixels = np.max(horizontal_proj) if len(horizontal_proj) > 0 else 0

            # If a single row in the middle has high continuous pixel count across width (>50% of width)
            if max_line_pixels > (cw * 0.52):
                # Verify stroke continuity across the horizontal row
                peak_row_idx = np.argmax(horizontal_proj)
                row_pixels = mid_slice[peak_row_idx, :]
                consecutive_segments = 0
                curr = 0
                max_consec = 0
                for px in row_pixels:
                    if px == 255:
                        curr += 1
                        if curr > max_consec:
                            max_consec = curr
                    else:
                        curr = 0
                # If a connected stroke spans at least 30% of the line width continuously
                if max_consec > (cw * 0.28):
                    return True

            return False
        except Exception as e:
            logger.debug(f"Strikethrough analysis fallback: {e}")
            return False


region_analyzer = RegionAnalyzer()


def detect_stamp_box(image: np.ndarray, is_first_page: bool = True) -> Optional[Tuple[int, int, int, int]]:
    return region_analyzer.detect_stamp_box(image, is_first_page=is_first_page)


def mask_stamp_region(image: np.ndarray, stamp_box: Optional[Tuple[int, int, int, int]]) -> np.ndarray:
    return region_analyzer.mask_stamp_region(image, stamp_box)


def detect_non_text_regions(image: np.ndarray) -> List[Tuple[int, int, int, int]]:
    return region_analyzer.detect_non_text_regions(image)


def is_strikethrough(line_crop: np.ndarray) -> bool:
    return region_analyzer.is_strikethrough(line_crop)


def reject_non_text_elements(elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filters out non-text elements (photos, thumbprints) from a candidate element list."""
    filtered = []
    for el in elements:
        if el.get("type") == "photo":
            continue
        crop = el.get("crop")
        if crop is not None and crop.size > 0:
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if len(crop.shape) == 3 else crop.copy()
            _, thresh = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY_INV)
            density = np.count_nonzero(thresh) / float(crop.shape[0] * crop.shape[1])
            # Reject massive solid dark blobs
            if density > 0.85:
                continue
        filtered.append(el)
    return filtered
