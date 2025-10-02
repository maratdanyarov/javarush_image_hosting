"""
    HTTP upload controller
    Handles HTTP POST requests for uploading images via multipart/form-data.
"""
import cgi
import http.server

from urllib.parse import urlparse

from src.image_hosting.config import MAX_FILE_SIZE, logger
from src.image_hosting.services.image_service import ImageService
from src.image_hosting.utils import json_response

class UploadController:
    """
    Handles the HTTP upload logic.
    - Validates path, headers, and content.
    - Parses multipart form data.
    - Delegates image processing to ImageService.
    """

    def __init__(self, image_service: ImageService | None = None):
        """Initialize UploadController with optional custom ImageService."""
        self.image_service = image_service or ImageService()

    def handle_post(self, handler: http.server.BaseHTTPRequestHandler) -> None:
        """Main POST handler: orchestrates file upload validation, parsing and saving."""
        if not self._is_upload_path(handler):
            logger.warning(f"Unknown POST path: {handler.path}")
            json_response(handler, 404, {"status": "error", "message": "Not Found"})
            return

        ok, content_length = self._validate_headers(handler)
        if not ok:
            return

        form = self._parse_multipart(handler, content_length)
        if form is None:
            return

        file_field = self._extract_file_field(handler, form)
        if file_field is None:
            return

        original_filename = file_field.filename

        file_bytes = self._read_file_bytes(handler, file_field)
        if file_bytes is None:
            return

        if not self._check_runtime_size(handler, file_bytes):
            return

        result = self._save_via_service(handler, file_bytes, original_filename)
        if result is None:
            return
        unique_name, file_url = result

        json_response(
            handler,
            200,
            {
                "status": "success",
                "message": "File successfully uploaded.",
                "filename": unique_name,
                "url": file_url,
            },
        )

    def _is_upload_path(self, handler: http.server.BaseHTTPRequestHandler) -> bool:
        """Check whether the request is targeting the correct /upload path."""
        return urlparse(handler.path).path == "/upload"

    def _validate_headers(self, handler: http.server.BaseHTTPRequestHandler) -> tuple[bool, int]:
        """Validate Content-Type (multipart/form-data with boundary) and Content-Length."""
        ctype, pdict = cgi.parse_header(handler.headers.get("Content-Type",""))
        boundary = pdict.get("boundary")
        if ctype != "multipart/form-data" or not boundary:
            logger.warning("UploadError: wrong Content-Type or missing boundary.")
            json_response(handler, 400, {"status": "error", "message": "Expecting multipart/form-data"})
            return False, 0

        try:
            content_length = int(handler.headers.get("Content-Length", 0))
        except ValueError:
            content_length = 0

        if content_length <= 0:
            logger.warning("UploadError: missing or invalid Content-Length.")
            json_response(handler, 411, {"status": "error", "message": "Wrong Content-Length"})
            return False, 0

        if content_length > MAX_FILE_SIZE:
            logger.warning(f"Upload error: payload is too large {content_length} bytes.")
            json_response(handler, 413, {"status": "error", "message": "File is too large"})
            return False, 0

        return True, content_length

    def _parse_multipart(self, handler: http.server.BaseHTTPRequestHandler, content_length: int):
        """Parse multipart form and return FieldStorage. Respond one error."""
        try:
            return cgi.FieldStorage(
                fp=handler.rfile,
                headers=handler.headers,
                environ={
                    "REQUEST_METHOD": "POST",
                    "CONTENT_TYPE": handler.headers.get("Content-Length", ""),
                    "CONTENT_LENGTH": str(content_length),
                },
            )
        except Exception as e:
            logger.warning(f"Multipart parsing error: {e}")
            json_response(handler, 400, {"status": "error", "message": "Malformed multipart data"})
            return None

    def _extract_file_field(self, handler: http.server.BaseHTTPRequestHandler, form):
        """Extract and validate 'file' field from multipart form; respond with error if invalid."""
        if "file" not in form:
            logger.warning("Upload Error: 'file' field not found in form.")
            json_response(handler, 400, {"status": "error", "message": "File field not found in form"})
            return None

        file_field = form["file"]
        if isinstance(file_field, list):
            file_field = file_field[0]

        if not getattr(file_field, "filename", None):
            logger.warning("Upload Error: 'filename' is missing")
            json_response(handler, 400, {"status": "error", "message": "Fail name is missing."})
            return None

        return file_field

    def _read_file_bytes(self, handler: http.server.BaseHTTPRequestHandler, file_field):
        """Read bytes from uploaded file; respond with error if reading fails."""
        try:
            return file_field.file.read()
        except Exception as e:
            logger.error(f"Upload Error: failed to read file content: {e}")
            json_response(handler, 500, {"status": "error", "message": "Failed to read file content"})
            return None

    def _check_runtime_size(self, handler: http.server.BaseHTTPRequestHandler, file_bytes: bytes) -> bool:
        """Ensure uploaded file does not exceed runtime MAX_FILE_SIZE limit."""
        if len(file_bytes) > MAX_FILE_SIZE:
            logger.warning(f"Upload Error: file is too large {len(file_bytes)} bytes.")
            json_response(
                handler,
                413,
                {"status": "error", "message": f"File exceeds maximum file size {MAX_FILE_SIZE} bytes."},
            )
            return False
        return True

    def _save_via_service(
            self, handler: http.server.BaseHTTPRequestHandler, file_bytes: bytes, original_filename: str
    ):
        """Delegate image processing to ImageService and handle potential exceptions."""
        try:
            return self.image_service.handle(file_bytes, original_filename)
        except ValueError as e:
            msg = str(e)
            status = 400
            if msg == "Failed to reopen image.":
                status = 400
            elif msg.startswith("File exceeds"):
                status = 400
            logger.warning(f"Upload Error: {msg} ({original_filename})")
            json_response(handler, status, {"status": "error", "message": msg})
            return None
        except Exception as e:
            logger.exception(f"Uploading error for {original_filename}: {e}")
            json_response(handler, 500, {"status": "error", "message": "Uploading file error."})
            return None
