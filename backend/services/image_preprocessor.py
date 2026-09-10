import os
import logging
import cv2
import numpy as np
from typing import Tuple, Optional
from PIL import Image

logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """
    Production-grade Stage 0 Document Preprocessing Pipeline:
    - Grayscale conversion
    - Deskew via minAreaRect on binary text mask
    - Perspective correction (4-point transform)
    - Adaptive Contrast Enhancement (CLAHE)
    - 300 DPI target normalization
    """

    def __init__(self, target_dpi: int = 300):
        self.target_dpi = target_dpi

    @staticmethod
    def _order_points(pts: np.ndarray) -> np.ndarray:
        """Orders coordinates: top-left, top-right, bottom-right, bottom-left"""
        rect = np.zeros((4, 2), dtype="float32")
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]
        return rect

    def correct_perspective(self, image: np.ndarray) -> np.ndarray:
        """Applies 4-point perspective warp if a distinct document contour is found."""
        try:
            h, w = image.shape[:2]
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image.copy()
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            edged = cv2.Canny(blurred, 50, 200)

            contours, _ = cv2.findContours(edged, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
            contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]

            doc_contour = None
            for c in contours:
                peri = cv2.arcLength(c, True)
                approx = cv2.approxPolyDP(c, 0.02 * peri, True)
                if len(approx) == 4 and cv2.contourArea(approx) > (w * h * 0.45):
                    doc_contour = approx.reshape(4, 2)
                    break

            if doc_contour is None:
                return image

            rect = self._order_points(doc_contour)
            (tl, tr, br, bl) = rect

            width_a = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
            width_b = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
            max_width = max(int(width_a), int(width_b))

            height_a = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
            height_b = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
            max_height = max(int(height_a), int(height_b))

            if max_width < 100 or max_height < 100:
                return image

            dst = np.array([
                [0, 0],
                [max_width - 1, 0],
                [max_width - 1, max_height - 1],
                [0, max_height - 1]
            ], dtype="float32")

            matrix = cv2.getPerspectiveTransform(rect, dst)
            warped = cv2.warpPerspective(image, matrix, (max_width, max_height))
            return warped
        except Exception as e:
            logger.debug(f"Perspective correction bypassed: {e}")
            return image

    def deskew(self, image: np.ndarray) -> np.ndarray:
        """Detects text orientation tilt and straightens document between 1.5° and 45°."""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image.copy()
            # Invert & threshold
            binary = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY_INV, 15, 8
            )

            coords = np.column_stack(np.where(binary > 0))
            if len(coords) < 150:
                return image

            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45.0:
                angle = -(90.0 + angle)
            elif angle > 45.0:
                angle = 90.0 - angle
            else:
                angle = -angle

            if 1.5 < abs(angle) < 45.0:
                h, w = image.shape[:2]
                center = (w // 2, h // 2)
                m = cv2.getRotationMatrix2D(center, angle, 1.0)
                deskewed = cv2.warpAffine(
                    image, m, (w, h),
                    flags=cv2.INTER_LINEAR,
                    borderMode=cv2.BORDER_REPLICATE
                )
                return deskewed
            return image
        except Exception as e:
            logger.debug(f"Deskew skipped: {e}")
            return image

    def apply_clahe(self, image: np.ndarray) -> np.ndarray:
        """Enhances contrast across uneven lighting and scanner shadows."""
        try:
            if len(image.shape) == 3:
                lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
                l, a, b = cv2.split(lab)
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                cl = clahe.apply(l)
                enhanced_lab = cv2.merge((cl, a, b))
                return cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
            else:
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                return clahe.apply(image)
        except Exception as e:
            logger.debug(f"CLAHE contrast enhancement bypassed: {e}")
            return image

    def normalize_dpi(self, image: np.ndarray, target_height: int = 2400) -> np.ndarray:
        """Scales image to ~300 DPI equivalent for optimal Indic character recognition."""
        try:
            h, w = image.shape[:2]
            if h < 1200:
                scale = target_height / float(h)
                new_w = int(w * scale)
                return cv2.resize(image, (new_w, target_height), interpolation=cv2.INTER_CUBIC)
            elif h > 3500:
                scale = target_height / float(h)
                new_w = int(w * scale)
                return cv2.resize(image, (new_w, target_height), interpolation=cv2.INTER_AREA)
            return image
        except Exception:
            return image

    def process_image(self, input_path: str, output_path: Optional[str] = None) -> str:
        """
        Executes full preprocessing pipeline:
        1. Read image
        2. Perspective correction
        3. Deskew
        4. CLAHE contrast enhancement
        5. 300 DPI scaling
        6. Save processed image
        """
        img = cv2.imread(input_path)
        if img is None:
            raise FileNotFoundError(f"Image not found at {input_path}")

        # Pipeline stages
        img = self.correct_perspective(img)
        img = self.deskew(img)
        img = self.apply_clahe(img)
        img = self.normalize_dpi(img)

        out_path = output_path or input_path
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        cv2.imwrite(out_path, img)
        return out_path


image_preprocessor = ImagePreprocessor()


def deskew_image(image: np.ndarray) -> Tuple[np.ndarray, float]:
    """Helper function to deskew an in-memory image array and return (image, angle)."""
    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image.copy()
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 15, 8
        )
        coords = np.column_stack(np.where(binary > 0))
        if len(coords) < 150:
            return image, 0.0

        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45.0:
            angle = -(90.0 + angle)
        elif angle > 45.0:
            angle = 90.0 - angle
        else:
            angle = -angle

        if 1.5 < abs(angle) < 45.0:
            h, w = image.shape[:2]
            center = (w // 2, h // 2)
            m = cv2.getRotationMatrix2D(center, angle, 1.0)
            deskewed = cv2.warpAffine(
                image, m, (w, h),
                flags=cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_REPLICATE
            )
            return deskewed, float(angle)
        return image, float(angle)
    except Exception as e:
        logger.debug(f"deskew_image error: {e}")
        return image, 0.0


def apply_clahe(image: np.ndarray) -> np.ndarray:
    """Helper function to apply CLAHE to an image array."""
    return image_preprocessor.apply_clahe(image)


def normalize_dpi(image: np.ndarray, target_height: int = 2400) -> np.ndarray:
    """Helper function to normalize DPI of an image array."""
    return image_preprocessor.normalize_dpi(image, target_height)


def preprocess_document_image(image: np.ndarray, target_dpi: int = 300) -> np.ndarray:
    """Helper function to run in-memory Stage 0 preprocessing pipeline."""
    img = image_preprocessor.correct_perspective(image)
    img, _ = deskew_image(img)
    img = image_preprocessor.apply_clahe(img)
    img = image_preprocessor.normalize_dpi(img)
    return img
