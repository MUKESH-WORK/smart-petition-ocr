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
        self._path_cache = {}
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
        self._path_cache[str(source_id)] = saved_path

        return saved_path, file_hash, len(content)

    def get_file_path(self, source_id: str, ext: Optional[str] = None, file_hash: Optional[str] = None) -> Optional[str]:
        """Returns the absolute file path for a given source_id using O(1) cache/targeted lookup."""
        sid = str(source_id)
        if sid in self._path_cache:
            p = self._path_cache[sid]
            if os.path.exists(p):
                return p

        if not os.path.exists(self.upload_dir):
            return None

        if file_hash and ext:
            direct = os.path.join(self.upload_dir, f"{sid}_{file_hash[:8]}{ext}")
            if os.path.exists(direct):
                self._path_cache[sid] = direct
                return direct

        import glob
        matches = glob.glob(os.path.join(self.upload_dir, f"{sid}*"))
        if matches:
            self._path_cache[sid] = matches[0]
            return matches[0]
        return None

    def get_page_image_path(self, source_id: str, page_number: int) -> str:
        return os.path.join(self.static_media_dir, f"{source_id}_p{page_number}.png")

    async def convert_document_to_images(self, source_id: str, file_path: str, file_type: str) -> List[str]:
        """
        Converts PDF or image input into a list of 200 DPI normalized PNG images in static/media/.
        Offloads synchronous CPU-bound rasterization to a worker thread to keep the async event loop responsive.
        """
        def _sync_convert() -> List[str]:
            image_paths = []
            f_type = file_type.lower().replace(".", "")
            target_dpi = getattr(settings, "OCR_DPI", 200)

            if f_type == "pdf":
                try:
                    import fitz
                    with fitz.open(file_path) as doc:
                        for idx, page in enumerate(doc, 1):
                            pix = page.get_pixmap(dpi=target_dpi)
                            out_path = self.get_page_image_path(source_id, idx)
                            pix.save(out_path)
                            image_paths.append(out_path)
                except Exception as e:
                    try:
                        from pdf2image import convert_from_path
                        images = convert_from_path(file_path, dpi=target_dpi)
                        for idx, img in enumerate(images, 1):
                            out_path = self.get_page_image_path(source_id, idx)
                            img.save(out_path, "PNG")
                            image_paths.append(out_path)
                    except Exception as e2:
                        raise RuntimeError(f"Error converting PDF to images: {e} | {e2}")
            elif f_type in ["png", "jpg", "jpeg", "tiff", "tif", "webp", "bmp"]:
                try:
                    with Image.open(file_path) as img:
                        # Validation: check image dimensions
                        if img.width < 50 or img.height < 50:
                            raise ValueError(f"Image too small ({img.width}x{img.height}) for OCR processing")
                        if img.mode != "RGB":
                            img_rgb = img.convert("RGB")
                        else:
                            img_rgb = img
                        out_path = self.get_page_image_path(source_id, 1)
                        img_rgb.save(out_path, "PNG")
                        image_paths.append(out_path)
                except Exception as e:
                    raise ValueError(f"Invalid or corrupted image file: {e}")
            else:
                raise ValueError(f"Unsupported file type for OCR: {f_type}")

            return image_paths

        return await asyncio.to_thread(_sync_convert)


file_store = FileStore()
