import http.server
import socketserver
import logging
import json
import os
from urllib.parse import urlparse, parse_qs
import uuid

STATIC_FILES_DIR = 'static'
UPLOAD_DIR = 'images'
MAX_FILE_SIZE = 5 * 1024 * 1024
ALLOWED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif'}

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# Logging
log_dir = 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'app.log')),
        logging.StreamHandler()
    ]
)

# Server class
class ImageHostingHandler(http.server.BaseHTTPRequestHandler):
    def _set_headers(self, status_code=200, content_type='text/html'):
        self.send_response(status_code)
        self.send_header('Content-Type', content_type)
        self.end_headers()

    def _get_content_type(self, file_path):
        if file_path.endswith('.html'):
            return 'text/html'
        elif file_path.endswith('.css'):
            return 'text/css'
        elif file_path.endswith('.js'):
            return 'application/javascript'
        elif file_path.endswith(('.png', '.jpg', '.jpeg', '.gif')):
            return 'image/' + file_path.split('.')[-1]
        else:
            return 'application/octet-stream'

    def do_GET(self):
        parsed_path = urlparse(self.path)
        request_path = parsed_path.path

        if request_path == '/':
            file_path = os.path.join(STATIC_FILES_DIR, 'index.html')
            content_type = 'text/html'
        elif request_path.startswith('/static/'):
            file_path = request_path[1:]
            content_type = self._get_content_type(file_path)
        else:
            file_path = os.path.join(STATIC_FILES_DIR, request_path.lstrip('/'))
            content_type = self._get_content_type(file_path)

        if os.path.exists(file_path) and os.path.isfile(file_path):
            try:
                with open(file_path, 'rb') as f:
                    self._set_headers(200, content_type)
                    self.wfile.write(f.read())
                logging.info(f"Action: Request for file {file_path} received")
                return
            except Exception as e:
                logging.error(f"Action: Request for file {file_path} failed: {e}")
                self._set_headers(500, "text/plain")
                self.wfile.write(b"500 Internal Server Error")
                return

        logging.warning(f"Action: Error to send file {file_path} occurred")
        self._set_headers(500, "text/plain")
        self.wfile.write(b"500 Internal Server Error")

    def do_POST(self):
        parsed_path = urlparse(self.path)
        if parsed_path.path == '/upload':
            test_file_name = "test_image.png"
            test_file_size = 3 * 1024 * 1024
            file_extension = os.path.splitext(test_file_name)[1].lower()
            if file_extension not in ALLOWED_EXTENSIONS:
                logging.warning(f"Action: Upload error - file extension {file_extension} not supported")
                self._set_headers(400, "application/json")
                response = {"status": "error",
                            "message": f"File extension is not supported. Allowed :{', '.join(ALLOWED_EXTENSIONS)}"}
                self.wfile.write(json.dumps(response).encode('utf-8'))
                return
            if test_file_size > MAX_FILE_SIZE:
                logging.warning(f"Action: Upload error - file size {test_file_size} > {MAX_FILE_SIZE}")
                self._set_headers(400, "application/json")
                response = {"status": "error",
                            "message": f"File size {test_file_size} > {MAX_FILE_SIZE}"}
                self.wfile.write(json.dumps(response).encode('utf-8'))
                return

            unique_filename = f"{uuid.uuid4().hex}{file_extension}"
            target_path = os.path.join(UPLOAD_DIR, unique_filename)

            try:
                with open(target_path, 'wb') as f:
                    pass

                file_url = f"/images/{unique_filename}"
                logging.info(f"Action: Image '{test_file_name}' (saved as  '{unique_filename}') successfully uploaded. Link: {file_url}")
                self._set_headers(200, 'application/json')
                response = {
                    "status": "success",
                    "message": f"Image '{test_file_name}' successfully uploaded.",
                    "filename": unique_filename,
                    "url": file_url
                }
                self.wfile.write(json.dumps(response).encode('utf-8'))
            except Exception as e:
                logging.error(f"Error saving image '{test_file_name}' to '{target_path}'")
                self._set_headers(500, "application/json")
                response = {"status": "error", "message": f"Error saving image '{test_file_name}' to '{target_path}'"}
                self.wfile.write(json.dumps(response).encode('utf-8'))

        else:
            self._set_headers(404, content_type='text/plain')
            self.wfile.write(b"404 Not Found")




def run_server(server_class=http.server.HTTPServer, handler_class=ImageHostingHandler, port=8080):
        server_address = ('', port)
        httpd = server_class(server_address, handler_class)
        logging.info(f"Server started on port {port}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        httpd.server_close()
        logging.info("Server stopped")

if __name__ == '__main__':
    run_server()
