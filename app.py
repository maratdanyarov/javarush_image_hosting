import cgi
import http.server
import json
import logging
import os
import io
import uuid
from urllib.parse import urlparse

from PIL import Image, UnidentifiedImageError

STATIC_FILES_DIR = 'static'
UPLOAD_DIR = 'images'
MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = ['JPEG', 'PNG', 'GIF']

os.makedirs(UPLOAD_DIR, exist_ok=True)

# Logging
log_dir = 'logs'
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'app.log')),
        logging.StreamHandler()
    ]
)

# Helpers
def json_response(handler: http.server.BaseHTTPRequestHandler, status: int, payload: dict):
    handler.send_response(status)
    handler.send_header('Content-Type', 'application/json; charset=utf-8')
    handler.end_headers()
    handler.wfile.write(json.dumps(payload).encode('utf-8'))

def infer_ext_from_format(pillow_format: str) -> str:
    """
    Map Pillow's image format to general file extension.
    """
    fmt = (pillow_format or '').upper()
    if fmt == 'JPEG':
        return '.jpg'
    if fmt == 'PNG':
        return '.png'
    if fmt == 'GIF':
        return '.gif'
    return '.img'

def content_type_for_path(path: str) -> str:
    if path.endswith('.html'):
        return 'text/html'
    if path.endswith('.css'):
        return 'text/css'
    if path.endswith('.js'):
        return 'application/javascript'
    if path.endswith(('.png', '.jpg', '.jpeg', '.gif')):
        ext = path.split('.')[-1].lower()
        if ext == 'jpg':
            ext = 'jpeg'
        return f'image/{ext}'
    return 'application/octet-stream'

# Request Handler
class ImageHostingHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        logging.warning(f"Unexpected GET to backend: {self.path}. Static should be handled by Nginx.")
        self.send_response(404)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(b'404 Not Found (Static served by Nginx).')

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path not in ('/upload'):
            logging.warning(f"Unknown POST path: {self.path}")
            return json_response(self, 404, {"status": "error", "message": "Not Found"})

        ctype, pdict = cgi.parse_header(self.headers.get('Content-Type', ''))
        if ctype != 'multipart/form-data' or 'boundary' not in pdict:
            logging.warning("Upload error: wrong Content-Type or missing boundary.")
            return json_response(self, 404, {"status": "error", "message": "Expecting multipart/form-data"})

        try:
            content_length = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            content_length = 0

        if content_length <= 0:
            logging.warning("Upload error: missing or invalid Content-Length.")
            return json_response(self, 411, {"status": "error", "message": "Wrong Content-Length"})

        if content_length > MAX_FILE_SIZE:
            logging.warning(f"Upload error: payload too large ({content_length} bytes).)")
            return json_response(self, 413, {"status": "error", "message": "File is too large"})

        # Parse multipart via FieldStorage
        try:
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={'REQUEST_METHOD': 'POST',
                         'CONTENT_TYPE': self.headers.get('Content-Type', '')
                         }
            )
        except Exception as e:
            logging.error(f"Multipart parsing error: {e}")
            return json_response(self, 400, {"status": "error", "message": "Malformed multipart data"})

        if 'file' not in form:
            logging.warning(f"Upload error: 'file' field not found in form")
            return json_response(self, 400, {"status": "error", "message": "File field not found"})

        file_field = form['file']
        # Normalize form to a single form
        if isinstance(file_field, list):
            file_field = file_field[0]

        if not getattr(file_field, 'filename', None):
            logging.warning("Upload error: filename is missing.")
            return json_response(self, 400, {"status": "error", "message": "Filename is missing"})

        original_filename = file_field.filename
        try:
            file_bytes = file_field.file.read()
        except Exception as e:
            logging.error(f"Upload error: failed to read file content: {e}")
            return json_response(self, 500, {"status": "error", "message": "Failed to read file content"})

        if len(file_bytes) > MAX_FILE_SIZE:
            logging.warning(f"Upload error: file too large {original_filename} ({len(file_bytes)} bytes).")
            return json_response(self, 400, {"status": "error",
                                             "message": f"File exceeds maximum file size {MAX_FILE_SIZE // 1024 * 1024} bytes"})

        try:
            probe = Image.open(io.BytesIO(file_bytes))
            probe.verify()
        except UnidentifiedImageError:
            logging.warning(f"Upload error: not a valid image: {original_filename}")
            return json_response(self, 400, {"status": "error", "message": "Invalid image file"})
        except Exception as e:
            logging.error(f"Upload error: image verification failed: {e}")
            return json_response(self, 400, {"status": "error", "message": "Invalid or corrupted image file"})

        # Re-open after verify (verify() leaves the file in an unusable state)
        try:
            image = Image.open(io.BytesIO(file_bytes))
        except Exception as e:
            logging.error(f"Upload error: cannot reopent image after verification: {e}")
            return json_response(self, 400, {"status": "error", "message": "Failed to reopen image"})

        img_format = (image.format or '').upper()
        if img_format not in ALLOWED_EXTENSIONS:
            logging.warning(f"Upload error: disalloweed format {img_format} for file {original_filename}")
            return json_response(self, 400, {"status": "error", "message": f"Image format {img_format} is not allowed"})

        ext = infer_ext_from_format(pillow_format=img_format)
        unique_name = f"{uuid.uuid4().hex}{ext}"

        target_path = os.path.join(UPLOAD_DIR, unique_name)

        save_kwargs = {}
        if img_format == 'JPEG':
            if image.mode not in ('RGB', 'L'):
                image = image.convert('RGB')
            save_kwargs.update(dict(quality=90, optimize=True, progressive=True))
        elif img_format == 'PNG':
            save_kwargs.update(dict(optimize=True))

        try:
            image.save(target_path, format=img_format, **save_kwargs)
        except Exception as e:
            logging.exception(f"Saving error for {original_filename} -> {target_path}: {e}")
            return json_response(self, 500, {"status": "error", "message": "Uploading file error"})

        file_url = f"/images/{unique_name}"
        logging.info(f"Uploaded '{original_filename}' as '{unique_name}' ({img_format}). URL: {file_url}")
        return json_response(
            self, 200,
            {"status": "success", "message": "File successfully uploaded.", "filename": unique_name, "url": file_url}
        )


def run_server(server_class=http.server.HTTPServer, handler_class=ImageHostingHandler, port=8000):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    logging.info(f"Server is started at port: {port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    logging.info("Server stopped.")


if __name__ == '__main__':
    run_server()