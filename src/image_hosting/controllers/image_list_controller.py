import http
import urllib.parse

from src.image_hosting.config import logger
from src.image_hosting.services.image_service import ImageService
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
            qs = urllib.parse.urlparse(handler.path).query
            params = urllib.parse.parse_qs(qs)
            page = int(params.get("page", ["1"])[0])

            payload = self.image_service.get_images_page(page=page, per_page=10)
            logger.info("Images page fetched: page=%d, items=%d",
                        page, len(payload["images"]))

            json_response(handler, 200, {
                "status": "success",
                "images": payload["images"],
                "pagination": payload["pagination"],
            })
        except Exception as e:
            logger.error(f"Error getting image list: {e}")
            json_response(handler, 500, {
                "status": "error",
                "message": "Error getting image list"
            })