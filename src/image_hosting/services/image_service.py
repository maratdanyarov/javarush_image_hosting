import io
import os
import uuid
from typing import Tuple

from PIL import Image, UnidentifiedImageError

from src.image_hosting.config import UPLOAD_DIR, MAX_FILE_SIZE, ALLOWED_EXTENSIONS, logger
from src.image_hosting.utils import infer_ext_from_format

class ImageService:
    """
    Image loading business logic:
    - basic size/format checks;
    - verification (verify()) and reopening;
    - safe save with parameters for JPEG/PNG;
    Returns unique_name and file_url.
    """
    def __init__(self, upload_dir: str = UPLOAD_DIR):
        self.upload_dir = upload_dir

    def validate_bytes(self, file_bytes: bytes, original_filename: str) -> Image.Image:
        if len(file_bytes) > MAX_FILE_SIZE:
            raise ValueError(f"File exceeds maximum file size: {MAX_FILE_SIZE} bytes.")

        # Check file integrity
        try:
            with Image.open(io.BytesIO(file_bytes)) as probe:
                probe.verify()
        except UnidentifiedImageError:
            raise ValueError("Invalid image file.")
        except Exception:
            raise ValueError("Invalid or corrupted image file.")

        # Reopen file after verification
        try:
            image = Image.open(io.BytesIO(file_bytes))
        except Exception:
            raise ValueError("Failed to reopen image.")

        img_format = (image.format or '').upper()
        if img_format not in ALLOWED_EXTENSIONS:
            raise ValueError(f"Image format {img_format} is not supported.")

        return image

    def save_image(self, image: Image.Image, original_filename: str) -> Tuple[str, str]:
        img_format = (image.format or '').upper()
        ext = infer_ext_from_format(img_format)
        unique_name = f"{uuid.uuid4().hex}{ext}"
        target_path = os.path.join(self.upload_dir, unique_name)

        save_kwargs = {}
        if img_format == 'JPEG':
            if image.mode not in ('RGB', 'L'):
                image = image.convert('RGB')
            save_kwargs.update(quality=90, optimize=True, progressive=True)
        elif img_format == 'PNG':
            save_kwargs.update(optimize=True)

        try:
            image.save(target_path, format=img_format, **save_kwargs)
        finally:
            try:
                image.close()
            except Exception:
                pass

        file_url = f"/images/{unique_name}"
        logger.info(f"Uploaded '%s' as '%s' (%s). URL: %s", original_filename, unique_name, img_format, file_url)
        return unique_name, file_url

    def handle(self, file_bytes: bytes, original_filename: str) -> Tuple[str, str]:
        image = self.validate_bytes(file_bytes, original_filename)
        return self.save_image(image, original_filename)
