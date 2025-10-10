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
    Service that encapsulates image validation, transformation and persistence.
    """

    def __init__(self, upload_dir: str = UPLOAD_DIR):
        self.upload_dir = upload_dir

    def validate_bytes(self, file_bytes: bytes, original_filename: str) -> Image.Image:
        """
        Validate raw uploaded bytes and return a reopened PIL Image.
        Steps:
            - Check upper size limit.
            - Verify basic image integrity with PIL.verify().
            - Reopen image for actual use.
            - Ensure format is allowed.
        Args:
            file_bytes: Raw uploaded bytes.
            original_filename: Original filename for logging context.
        Returns:
            A reopened PIL Image object ready for saving.
        Raises:
            ValueError: If the file is too large, invalid, or unsupported.
        """
        logger.debug(f"Validating image bytes: name={original_filename}")
        if len(file_bytes) > MAX_FILE_SIZE:
            logger.warning(f"Validation failed: file exceeds limit ({len(file_bytes)} > {MAX_FILE_SIZE}) for {original_filename}")
            raise ValueError(f"File exceeds maximum file size: {MAX_FILE_SIZE} bytes.")

        try:
            with Image.open(io.BytesIO(file_bytes)) as probe:
                probe.verify()
        except UnidentifiedImageError as uie:
            logger.error(f"Validation failed: unidentified image for {original_filename}: {uie}")
            raise ValueError("Invalid image file.")
        except Exception as e:
            logger.warning(f"Validation failed: corrupted image data for {original_filename}: {e}")
            raise ValueError("Invalid or corrupted image file.")

        try:
            image = Image.open(io.BytesIO(file_bytes))
        except Exception as e:
            logger.error(f"Validation failed: unable to reopen image for {original_filename}: {e}")
            raise ValueError("Failed to reopen image.")

        img_format = (image.format or '').upper()
        if img_format not in ALLOWED_EXTENSIONS:
            logger.warning(f"Validation failed: unsupported format {img_format} for {original_filename}")
            raise ValueError(f"Image format {img_format} is not supported.")

        return image

    def save_image(self, image: Image.Image, original_filename: str) -> Tuple[str, str]:
        """
        Persist a validated PIL Image to disk and record metadata.
        Applies format-specific parameters, converts to RGB for JPEG if required,
        and writes a DB record with essential metadata.
        Args:
            image: A previously validated PIL Image.
            original_filename: Client-provided original name for logging/DB.
        Returns:
            (unique_name, public_url) for the saved image.
        """
        img_format = (image.format or '').upper()
        ext = infer_ext_from_format(img_format)
        unique_name = f"{uuid.uuid4().hex}{ext}"
        target_path = os.path.join(self.upload_dir, unique_name)

        logger.debug(f"Preparing to save image: original={original_filename} "
                     f"as={unique_name} format={img_format} path={target_path}")


        save_kwargs: Dict[str, Any] = {}
        if img_format == JPEG:
            if image.mode not in (RGB, 'L'):
                logger.debug(f"Converting image mode {image.mode} -> {RGB} for JPEG")
                image = image.convert(RGB)
            save_kwargs.update(quality=90, optimize=True, progressive=True)
        elif img_format == PNG:
            save_kwargs.update(optimize=True)

        try:
            image.save(target_path, format=img_format, **save_kwargs)
            logger.info(f"Image saved to disk: {target_path}")

            try:
                conn = get_connection()
                if conn:
                    cursor = conn.cursor()
                    insert_query = """
                                   INSERT INTO images (filename, original_name, size, file_type)
                                   VALUES (%s, %s, %s, %s) \
                                   """
                    approx_size = sys.getsizeof(image.tobytes())
                    cursor.execute(insert_query,
                                   (unique_name, original_filename, approx_size, img_format))
                    conn.commit()
                    cursor.close()
                    conn.close()
                    logger.info(f"Metadata persisted to database: filename={unique_name} size={approx_size} type={img_format}")
                else:
                    logger.error(f"Database connection is None while saving metadata for {unique_name}")
            except Exception as e:
                logger.error(f"Failed to persist metadata for {unique_name}: {e}")
        finally:
            try:
                image.close()
            except Exception:
                logger.debug("Silently ignored error during image.close() for %s", unique_name)

        file_url = f"/images/{unique_name}"
        logger.info(f"Upload completed: original='{original_filename}' "
                    f"stored_as='{unique_name}' format={img_format} url={file_url}")
        return unique_name, file_url

    def handle(self, file_bytes: bytes, original_filename: str) -> Tuple[str, str]:
        """
        Validate uploaded bytes, then save the image and return identifiers.
        Args:
            file_bytes: Raw uploaded bytes.
            original_filename: Client-provided original filename.
        Returns:
            Tuple (unique_filename, file_url).
        """
        logger.info(f"Handling upload for: original_filename")
        image = self.validate_bytes(file_bytes, original_filename)
        return self.save_image(image, original_filename)

    def get_images_list(self) -> List[Dict[str, Any]]:
        """
        Return the full list of images as dictionaries ordered by upload time desc.
        Returns:
            List of dicts with keys: id, filename, original_name, size,
            upload_time (ISO), file_type, url.
        """
        logger.debug("Fetching full image list.")
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                           SELECT id, filename, original_name, size, upload_time, file_type
                           FROM images
                           ORDER BY upload_time DESC
                           """)
            rows = cursor.fetchall()
            logger.info(f"Fetched {len(rows)} image records.")
        finally:
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
        """
        Return a paginated slice of images and pagination metadata.
        Args:
            page: 1-based page index.
            per_page: Number of items per page.

        Returns:
            Dict with keys:
                - "images": list of image dicts
                - "pagination": {current_page, per_page, total, total_pages, has_prev, has_next}
        """
        page = max(1, int(page))
        offset = (page - 1) * per_page
        logger.debug(f"Fetching images page: page={page} per_page={per_page} offset={offset}")

        conn = get_connection()
        if not conn:
            logger.error("Database connection is None in get_images_page.")
            return {"images": [], "pagination": {
                "current_page": page, "per_page": per_page,
                "total": 0, "total_pages": 1,
                "has_prev": False, "has_next": False
            }}

        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM images")
        total = cursor.fetchone()[0] or 0

        try:
            cursor.execute("""
                           SELECT id, filename, original_name, size, upload_time, file_type
                           FROM images
                           ORDER BY upload_time DESC
                               LIMIT %s
                           OFFSET %s
                           """, (per_page, offset))
            rows = cursor.fetchall()
            logger.info(f"Page fetched: page={page} count={len(rows)} total={total}")
        finally:
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
        """
        Delete image metadata from DB and remove the file from disk.
        Args:
            image_id: The database ID of the image to delete.
        Returns:
            True if an image existed and was deleted; False if not found or on DB failure.
        """
        logger.info(f"Deleting image with id={image_id}")
        conn = get_connection()
        if not conn:
            logger.error("DB connection is None in handle_delete_image")
            return False
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT filename FROM images WHERE id = %s", (image_id,))
            result = cursor.fetchone()
            if not result:
                logger.error(f"Image not found for deletion: id={image_id}")
                conn.rollback()
                return False

            filename = result[0]
            file_path = os.path.join(self.upload_dir, filename)

            cursor.execute("DELETE FROM images WHERE id = %s", (image_id,))

            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.debug(f"Removed file from disk: {file_path}")
                else:
                    logger.debug(f"File not found on disk (skip remove): {file_path}")
            except Exception as fe:
                logger.error(f"Failed to delete image {filename}: {fe}")

            conn.commit()
            logger.info(f"Deleted image id='{image_id} name='{filename}'.")
            return True


        except Exception:
            logger.error(f"Error during image deletion for id=%s", image_id, exc_info=True)
            try:
                conn.rollback()
            except Exception:
                logger.debug("Rollback failed (ignored) during deletion for id=%s", image_id)
            return False
        finally:
            try:
                cursor.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass
