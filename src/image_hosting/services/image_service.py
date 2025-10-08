"""Image loading business logic: validation, verification, and saving uploaded images."""
import io
import os
import sys
import uuid
from typing import Tuple, List, Dict, Any
from math import ceil

from PIL import Image, UnidentifiedImageError

from src.image_hosting.config import UPLOAD_DIR, MAX_FILE_SIZE, ALLOWED_EXTENSIONS, logger
from src.image_hosting.database import get_connection
from src.image_hosting.utils import infer_ext_from_format

JPEG = 'JPEG'
PNG = 'PNG'
RGB = 'RGB'


class ImageService:
    """
    Provides image handling logic for uploaded files.
    - Performs size and format checks;
    - Verifies and reopens image safely;
    - Saves image with proper parameters;
    - Returns a unique filename and image URL.
    """

    def __init__(self, upload_dir: str = UPLOAD_DIR):
        """Initialize ImageService with the specified upload directory."""
        self.upload_dir = upload_dir

    def validate_bytes(self, file_bytes: bytes, original_filename: str) -> Image.Image:
        """
        Validate uploaded image bytes.
        - Check size limit;
        - Verify image integrity;
        - Reopen image to ensure it's usable;
        - Check allowed image format.
        """
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
        """
        Save the validated image to disk with a unique filename.
        - Applies format-specific saving parameters;
        - Converts image if required (e.g., for JPEG);
        - Logs and returns the new filename and file URL.
        """
        img_format = (image.format or '').upper()
        ext = infer_ext_from_format(img_format)
        unique_name = f"{uuid.uuid4().hex}{ext}"
        target_path = os.path.join(self.upload_dir, unique_name)

        save_kwargs = {}
        if img_format == JPEG:
            if image.mode not in (RGB, 'L'):
                image = image.convert(RGB)
            save_kwargs.update(quality=90, optimize=True, progressive=True)
        elif img_format == PNG:
            save_kwargs.update(optimize=True)

        try:
            image.save(target_path, format=img_format, **save_kwargs)
            try:
                conn = get_connection()
                if conn:
                    cursor = conn.cursor()
                    insert_query = """
                                   INSERT INTO images (filename, original_name, size, file_type)
                                   VALUES (%s, %s, %s, %s) \
                                   """
                    cursor.execute(insert_query,
                                   (unique_name, original_filename, sys.getsizeof(image.tobytes()), img_format))
                    conn.commit()
                    cursor.close()
                    conn.close()
                    logger.info(f"Metadata is successfully saved into database: {unique_name}")
            except Exception as e:
                logger.error(f"Failed to save image: {e}")
        finally:
            try:
                image.close()
            except Exception:
                pass

        file_url = f"/images/{unique_name}"
        logger.info(f"Uploaded '%s' as '%s' (%s). URL: %s", original_filename, unique_name, img_format, file_url)
        return unique_name, file_url

    def handle(self, file_bytes: bytes, original_filename: str) -> Tuple[str, str]:
        """
        Process uploaded file: validate and save.
        Returns a tuple: (unique filename, public file URL).
        """
        image = self.validate_bytes(file_bytes, original_filename)
        return self.save_image(image, original_filename)

    def get_images_list(self) -> List[Dict[str, Any]]:
        """Fetch images from DB and return as list of dicts."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
                       SELECT id, filename, original_name, size, upload_time, file_type
                       FROM images
                       ORDER BY upload_time DESC
                       """)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        items: List[Dict[str, Any]] = []
        for r in rows:
            upload_time = r[4]
            if upload_time is None:
                upload_iso = None
            elif hasattr(upload_time, "isoformat"):
                upload_iso = upload_time.isoformat()
            else:
                upload_iso = str(upload_time)

            items.append({
                "id": r[0],
                "filename": r[1],

                "original_name": r[2],
                "size": r[3],
                "upload_time": upload_iso,
                "file_type": r[5],
                "url": f"/images/{r[1]}",
            })
        return items

    def get_images_page(self, page: int = 1, per_page: int = 10):
        page = max(1, int(page))
        offset = (page - 1) * per_page

        conn = get_connection()
        if not conn:
            return {"images": [], "pagination": {
                "current_page": page, "per_page": per_page,
                "total": 0, "total_pages": 1,
                "has_prev": False, "has_next": False
            }}

        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM images")
        total = cursor.fetchone()[0] or 0

        cursor.execute("""
                       SELECT id, filename, original_name, size, upload_time, file_type
                       FROM images
                       ORDER BY upload_time DESC
                           LIMIT %s
                       OFFSET %s
                       """, (per_page, offset))
        rows = cursor.fetchall()
        cursor.close();
        conn.close()

        items = []
        for r in rows:
            up = r[4]
            upload_iso = up.isoformat() if hasattr(up, "isoformat") else (str(up) if up else None)
            items.append({
                "id": r[0],
                "filename": r[1],
                "original_name": r[2],
                "size": r[3],
                "upload_time": upload_iso,
                "file_type": r[5],
                "url": f"/images/{r[1]}",
            })

        total_pages = max(1, ceil(total / per_page)) if per_page else 1
        return {
            "images": items,
            "pagination": {
                "current_page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": total_pages,
                "has_prev": page > 1,
                "has_next": page < total_pages,
            }
        }

    def handle_delete_image(self, image_id: int) -> bool:
        conn = get_connection()
        if not conn:
            logger.error("DB connection is None in handle_delete_image")
            return False

        try:
            cursor = conn.cursor()
            cursor.execute("SELECT filename FROM images WHERE id = %s", (image_id,))
            result = cursor.fetchone()
            if not result:
                cursor.close()
                conn.close()
                return False
            filename = result[0]
            file_path = os.path.join(self.upload_dir, filename)
            cursor.execute("DELETE FROM images WHERE id = %s", (image_id,))
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as fe:
                logger.error(f"Failed to delete image {filename}: {fe}")

            conn.commit()
            cursor.close()
            conn.close()
            logger.info(f"Deleted image '{filename}'.")
            return True
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass
            raise
