import http
import urllib.parse

from src.image_hosting.config import logger
from src.image_hosting.services.image_service import ImageService
from src.image_hosting.utils import json_response


class ImageListController:
    """
        Controller responsible for handling image listing requests.
    """
    def __init__(self, image_service: ImageService | None = None):
        self.image_service = image_service or ImageService()

    def handle_get(self, handler: http.server.BaseHTTPRequestHandler):
        """Handle HTTP GET requests to retrieve a paginated list of images.
        Args:
            handler: The active HTTP request handler instance.
        Returns:
            JSON response containing image data and pagination info.
        """
        try:
            qs = urllib.parse.urlparse(handler.path).query
            params = urllib.parse.parse_qs(qs)
            page = int(params.get("page", ["1"])[0])
            logger.debug("Parsed query parameters: page=%d", page)

            payload = self.image_service.get_images_page(page=page, per_page=10)
            logger.info(f"Fetched image list: page={page}, count={len(payload["images"])}")

            json_response(handler, 200, {
                "status": "success",
                "images": payload["images"],
                "pagination": payload["pagination"],
            })
        except Exception as e:
            logger.error(f"Error fetching image list: {e}")
            json_response(handler, 500, {
                "status": "error",
                "message": "Error getting image list"
            })