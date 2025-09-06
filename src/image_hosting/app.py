import http.server

from src.image_hosting.config import logger
from src.image_hosting.controllers.upload_controller import UploadController

class ImageHostingHandler(http.server.BaseHTTPRequestHandler):
    controller = UploadController()

    def log_message(self, format: str, *args) -> None:
        logger.info("%s - " + format, self.address_string(), *args)

    def do_GET(self) -> None:
        logger.warning(f"Unexpected GET request to backend {self.path} Static should be handled by Nginx.")
        self.send_response(404)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(b'404 Not Found (Static served by Nginx).')

    def do_POST(self) -> None:
        self.controller.handle_post(self)

def run_server(server_class=http.server.HTTPServer, handler_class=ImageHostingHandler, port: int = 8000) -> None:
    server_address = ("", port)
    httpd = server_class(server_address, handler_class)
    logger.info(f"Server is started at port: {port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        logger.info(f"Server stopped.")

if __name__ == "__main__":
    run_server()
