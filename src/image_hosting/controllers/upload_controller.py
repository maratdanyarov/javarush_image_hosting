import cgi
import http.server

from urllib.parse import urlparse

from src.image_hosting.config import MAX_FILE_SIZE, logger
from src.image_hosting.services.image_service import ImageService
from src.image_hosting.utils import json_response

class UploadController:
    """Controller that handles image upload requests.
    Responsibilities:
        - Validate request path, headers, and payload size.
        - Parse multipart/form-data.
        - Delegate image verification/saving to ImageService.
    """

    def __init__(self, image_service: ImageService | None = None):
        self.image_service = image_service or ImageService()

    def handle_post(self, handler: http.server.BaseHTTPRequestHandler) -> None:
        """Entry point for handling HTTP POST upload requests.
        Orchestrates validation, multipart parsing, size checks, and saving.
        Args:
            handler: Active HTTP request handler instance.
        """
        logger.info(f"Received upload request: path={handler.path}")

        if not self._is_upload_path(handler):
            logger.warning(f"Upload rejected: unknown POST path: {handler.path}")
            return json_response(handler, 404, {"status": "error", "message": "Not Found"})

        file_bytes, original_filename = self._validate_and_parse_upload(handler)
        if not file_bytes:
            return

        result = self._save_via_service(handler, file_bytes, original_filename)
        if not result:
            return

        unique_name, file_url = result
        logger.info(f"File uploaded successfully: name={unique_name} url={file_url}")

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
        """
        Return True if the request targets the /upload endpoint.
        Args:
            handler: Active HTTP request handler instance.
        """
        return urlparse(handler.path).path == "/upload"

    def _validate_and_parse_upload(self, handler: http.server.BaseHTTPRequestHandler) -> tuple[bytes | None, str]:
        """Validate headers, parse multipart data, and extract file bytes.
        Args:
            handler: Active HTTP request handler instance.
        Returns:
            Tuple of (file_bytes, original_filename) on success, (None, "") on failure.
        """
        ok, content_length = self._validate_headers(handler)
        if not ok:
            return None, ""

        form = self._parse_multipart(handler, content_length)
        if form is None:
            return None, ""

        file_field = self._extract_file_field(handler, form)
        if file_field is None:
            return None, ""

        original_filename = file_field.filename
        logger.debug(f"Upload filename extracted: {original_filename}")

        file_bytes = self._read_file_bytes(handler, file_field)
        if file_bytes is None:
            return None, ""

        logger.debug(f"Read {len(file_bytes)} bytes from uploaded file: {original_filename}")

        if not self._check_runtime_size(handler, file_bytes):
            return None, ""

        return file_bytes, original_filename

    def _validate_headers(self, handler: http.server.BaseHTTPRequestHandler) -> tuple[bool, int]:
        """
        Validate Content-Type (multipart/form-data with boundary) and Content-Length.
        Args:
            handler: Active HTTP request handler instance.
        Returns:
            Tuple of (is_valid, content_length).
        """
        ctype, pdict = cgi.parse_header(handler.headers.get("Content-Type",""))
        boundary = pdict.get("boundary")
        logger.debug("Parsed headers: Content-Type=%s, boundary=%s", ctype, bool(boundary))

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

        logger.debug(f"Header validation passed: Content-Length={content_length}")
        return True, content_length

    def _parse_multipart(self, handler: http.server.BaseHTTPRequestHandler, content_length: int):
        """Parse multipart form payload and return FieldStorage.
        Sends a 400 JSON response on failure.
        Args:
            handler: Active HTTP request handler instance.
            content_length: Declared request payload size.
        Returns:
            cgi.FieldStorage on success; None on error.
        """
        try:
            return cgi.FieldStorage(
                fp=handler.rfile,
                headers=handler.headers,
                environ={
                    "REQUEST_METHOD": "POST",
                    "CONTENT_TYPE": handler.headers.get("Content-Type", ""),
                    "CONTENT_LENGTH": str(content_length),
                },
            )
        except Exception as e:
            logger.warning(f"Multipart parsing error: {e}")
            json_response(handler, 400, {"status": "error", "message": "Malformed multipart data"})
            return None

    def _extract_file_field(self, handler: http.server.BaseHTTPRequestHandler, form):
        """Extract and validate the 'file' field from the parsed form.
        Args:
            handler: Active HTTP request handler instance.
            form: Parsed cgi.FieldStorage.
        Returns:
            The file field object on success; None on validation error.
        """
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
        """Read bytes from the uploaded file stream.
        Args:
            handler: Active HTTP request handler instance.
            file_field: The file field from FieldStorage.
        Returns:
            Raw bytes on success; None on read error.
        """
        try:
            return file_field.file.read()
        except Exception as e:
            logger.error(f"Upload Error: failed to read file content: {e}")
            json_response(handler, 500, {"status": "error", "message": "Failed to read file content"})
            return None

    def _check_runtime_size(self, handler: http.server.BaseHTTPRequestHandler, file_bytes: bytes) -> bool:
        """
        Validate runtime file size against MAX_FILE_SIZE.
        Args:
            handler: Active HTTP request handler instance.
            file_bytes: Raw uploaded bytes.
        Returns:
            True if size is acceptable; False otherwise (and responds with 413).
        """
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
        """
        Delegate image processing to ImageService and handle service-layer errors.
        Args:
            handler: Active HTTP request handler instance.
            file_bytes: Raw uploaded bytes.
            original_filename: Client-provided original file name.
        Returns:
            Tuple (unique_name, file_url) on success; None on error with response sent.
        """
        try:
            logger.debug(f"Delegating to ImageService.handle for file: {original_filename}")
            return self.image_service.handle(file_bytes, original_filename)
        except ValueError as e:
            msg = str(e)
            status = 400
            logger.error(f"Upload validation error: {msg} ({original_filename})")
            if msg == "Failed to reopen image.":
                status = 400
            elif msg.startswith("File exceeds"):
                status = 400
            logger.warning(f"Upload Error: {msg} ({original_filename})")
            json_response(handler, status, {"status": "error", "message": msg})
            return None
        except Exception as e:
            logger.exception(f"Unexpected upload error for {original_filename}: {e}")
            json_response(handler, 500, {"status": "error", "message": "Uploading file error."})
            return None
