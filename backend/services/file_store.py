import os
import hashlib
import asyncio
from typing import Tuple, List, Optional
from PIL import Image
from app.config import settings


class FileStore:
    def __init__(self, upload_dir: str = settings.UPLOAD_DIR, static_media_dir: str = settings.STATIC_MEDIA_DIR):
        self.upload_dir = upload_dir
        self.static_media_dir = static_media_dir
        os.makedirs(self.upload_dir, exist_ok=True)
        os.makedirs(self.static_media_dir, exist_ok=True)

    @staticmethod
    def compute_sha256(content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    async def save_uploaded_file(self, source_id: str, filename: str, content: bytes) -> Tuple[str, str, int]:
        """
        Saves file to filesystem uploads directory and computes SHA256.
        Returns (saved_path, sha256_hash, size_bytes).
        """
        ext = os.path.splitext(filename)[1].lower()
        file_hash = self.compute_sha256(content)
        saved_filename = f"{source_id}_{file_hash[:8]}{ext}"
        saved_path = os.path.join(self.upload_dir, saved_filename)

        def _sync_write():
            with open(saved_path, "wb") as f:
                f.write(content)

        await asyncio.to_thread(_sync_write)

        return saved_path, file_hash, len(content)

    def get_file_path(self, source_id: str) -> Optional[str]:
        """Returns the absolute file path for a given source_id if it exists in uploads."""
        if not os.path.exists(self.upload_dir):
            return None
        for fname in os.listdir(self.upload_dir):
            if fname.startswith(str(source_id)):
                return os.path.join(self.upload_dir, fname)
        return None

    def get_page_image_path(self, source_id: str, page_number: int) -> str:
        return os.path.join(self.static_media_dir, f"{source_id}_p{page_number}.png")

    async def convert_document_to_images(self, source_id: str, file_path: str, file_type: str) -> List[str]:
        """
        Converts PDF or image input into a list of 300 DPI normalized PNG images in static/media/.
        """
        image_paths = []
        file_type = file_type.lower().replace(".", "")

        if file_type == "pdf":
            try:
                import fitz
                doc = fitz.open(file_path)
                for idx, page in enumerate(doc, 1):
                    pix = page.get_pixmap(dpi=150)
                    out_path = self.get_page_image_path(source_id, idx)
                    pix.save(out_path)
                    image_paths.append(out_path)
            except Exception as e:
                try:
                    from pdf2image import convert_from_path
                    images = convert_from_path(file_path, dpi=150)
                    for idx, img in enumerate(images, 1):
                        out_path = self.get_page_image_path(source_id, idx)
                        img.save(out_path, "PNG")
                        image_paths.append(out_path)
                except Exception as e2:
                    raise RuntimeError(f"Error converting PDF to images: {e} | {e2}")
        elif file_type in ["png", "jpg", "jpeg", "tiff", "webp"]:
            img = Image.open(file_path)
            if img.mode != "RGB":
                img = img.convert("RGB")
            out_path = self.get_page_image_path(source_id, 1)
            img.save(out_path, "PNG")
            image_paths.append(out_path)
        else:
            raise ValueError(f"Unsupported file type for OCR: {file_type}")

        return image_paths


file_store = FileStore()
