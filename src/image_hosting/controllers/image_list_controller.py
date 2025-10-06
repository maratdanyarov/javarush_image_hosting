import http
import json

from src.image_hosting.services.image_service import ImageService
from src.image_hosting.config import logger
from src.image_hosting.utils import json_response

class ImageListController:
    """
        Handles image listing logic.
    """
    def __init__(self, image_service: ImageService | None = None):
        self.image_service = image_service or ImageService()

    def handle_get(self, handler: http.server.BaseHTTPRequestHandler):
        """Handles GET requests."""
        try:
            images_list = self.image_service.get_images_list()
            images_list = images_list or []
            logger.info("Images successfully fetched: %d images", len(images_list))
            json_response(handler, 200, {"status": "success", "data": images_list})
        except Exception as e:
            logger.error(f"Error getting image list: {e}")
            json_response(handler, 500, {"status": "error", "message": f"Error getting image list"})
