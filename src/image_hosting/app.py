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
    Custom HTTP request handler for the image hosting backend.
    Routes:
        - GET /images-list  -> ImageListController.handle_get
        - POST /upload      -> UploadController.handle_post
        - DELETE /delete/:id-> DeleteImageController.delete_image
    All other routes return 404 (static assets should be served by Nginx).
    """
    upload_controller = UploadController()
    image_list_controller = ImageListController()
    delete_image_controller = DeleteImageController()

    def log_message(self, format: str, *args) -> None:
        """
        Log HTTP request messages using the configured logger.
        Args:
            format: printf-style format string.
            *args:  values to interpolate into the format string.
        """
        logger.info("%s - " + format, self.address_string(), *args)

    def do_GET(self) -> None:
        """
        Handle HTTP GET requests.
        Delegates /images-list to ImageListController. All other GETs are rejected
        because static files should be served by Nginx.
        """
        logger.info(f"GET {self.path}")
        parsed_path = urlparse(self.path)
        if parsed_path.path == "/images-list":
            logger.debug("Delegating to ImageListController.handle_get")
            self.image_list_controller.handle_get(self)
            return

        logger.warning(f"Unexpected GET request to backend {self.path}. Static should be handled by Nginx.")
        json_response(self, 404, {"status": "error", "message": "Not Found"})

    def do_POST(self) -> None:
        """
        Handle HTTP POST requests.
        Delegates /upload to UploadController; controller itself validates the path.
        """
        logger.info(f"POST {self.path}")
        logger.debug("Delegating to UploadController.handle_post")
        self.upload_controller.handle_post(self)

    def do_DELETE(self) -> None:
        """
        Handle HTTP DELETE requests.
        Expects paths in the form /delete/<id>. If the pattern does not match, responds with 404.
        """
        logger.info(f"DELETE {self.path}")
        parsed_path = urlparse(self.path)
        match = re.match(r'/delete/(\d+)', parsed_path.path)
        if match:
            image_id = int(match.group(1))
            logger.debug(f"Delegating deletion to DeleteImageController for id={image_id}")
            self.delete_image_controller.delete_image(self, image_id)
            return

        logger.warning(f"Unknown DELETE path: {self.path}")
        json_response(self, 404, {"status": "error", "message": "Not Found"})


def run_server(server_class=http.server.HTTPServer,
               handler_class=ImageHostingHandler,
               port: int = 8000) -> None:
    """
    Start the HTTP server and serve forever until interrupted.
    Args:
        server_class: HTTP server class to instantiate.
        handler_class: Request handler class to use.
        port: TCP port to bind on.
    """
    server_address = ("", port)
    httpd = server_class(server_address, handler_class)
    logger.info(f"Server is started at port: {port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down server...")
    finally:
        httpd.server_close()
        logger.info(f"Server stopped.")


def initialize_app():
    """
    Initialize application dependencies (DB connection and schema).
    Returns:
        True if initialization succeeded; False otherwise.
    """
    logger.info("Initializing application (DB connection + schema check).")

    if not test_connection():
        logger.error("Database connection failed. Check docker-compose settings.")
        return False

    logger.info("Database connection established.")

    if not init_database():
        logger.error("Database initialization failed: required table was not created.")
        return False

    logger.info("Database is initialized and ready.")
    return True



if __name__ == "__main__":
    if initialize_app():
        run_server()
    else:
        logger.error("ERROR: Application initialization failed. Server is not started.")
