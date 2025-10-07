"""Entry point and HTTP handler for the image hosting backend server."""
import http.server
import re
from urllib.parse import urlparse

from src.image_hosting.config import logger
from src.image_hosting.controllers.delete_image_controller import DeleteImageController
from src.image_hosting.controllers.image_list_controller import ImageListController
from src.image_hosting.controllers.upload_controller import UploadController
from src.image_hosting.database import test_connection, init_database
from src.image_hosting.utils import json_response


class ImageHostingHandler(http.server.BaseHTTPRequestHandler):
    """
    Custom HTTP request handler for image hosting
    - Delegates POST /upload to UploadController.
    - Rejects GET requests (static files expected via Nginx).
    """
    upload_controller = UploadController()
    image_list_controller = ImageListController()
    delete_image_controller = DeleteImageController()

    def log_message(self, format: str, *args) -> None:
        """Log HTTP requests using the configured logger."""
        logger.info("%s - " + format, self.address_string(), *args)

    def do_GET(self) -> None:
        """Handle GET requests and delegate them to ImageListController."""
        parsed_path = urlparse(self.path)
        if parsed_path.path == "/images-list":
            self.image_list_controller.handle_get(self)
        else:
            logger.warning(f"Unexpected GET request to backend {self.path}. Static should be handled by Nginx.")
            json_response(self, 404, {"status": "error", "message": "Not Found"})

    def do_POST(self) -> None:
        """Delegate POST requests to the UploadController."""
        self.upload_controller.handle_post(self)

    def do_DELETE(self) -> None:
        """Delegate DELETE requests to the DeleteController."""
        parsed_path = urlparse(self.path)
        match = re.match(r'/delete/(\d+)', parsed_path.path)
        if match:
            image_id = int(match.group(1))
            self.delete_image_controller.delete_image(self, image_id)
        return json_response(self, 404, {"status": "error", "message": "Not Found"})


def run_server(server_class=http.server.HTTPServer, handler_class=ImageHostingHandler, port: int = 8000) -> None:
    """
    Start the HTTP server on the given port.
    Runs until interrupted (Ctrl+C), then gracefully shuts down.
    """
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


def initialize_app():
    """Application initialization: test DB connection and create table."""
    logger.info("Initializing app...")

    if test_connection():
        logger.info("Database connection established.")

        if init_database():
            logger.info("Database is initialized and ready.")
        else:
            logger.error("Database initialization error: table is not created.")
            return False
    else:
        logger.error("ERROR: Database connection failed. Check docker compose settings.")
        return False

    return True


if __name__ == "__main__":
    if initialize_app():
        run_server()
    else:
        logger.error("ERROR: Application initialization failed. Server is not started.")
