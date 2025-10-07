import http.server

from src.image_hosting.services import image_service
from src.image_hosting.services.image_service import ImageService
from src.image_hosting.config import logger
from src.image_hosting.utils import json_response


class DeleteImageController:
    """
    Handles image deletion.
    """
    def __init__(self, image_service: ImageService | None = None):
        self.image_service = image_service or ImageService()

    def delete_image(self, handler: http.server.BaseHTTPRequestHandler, image_id: int):
        try:
            deleted = self.image_service.handle_delete_image(image_id)
            if not deleted:
                logger.info(f"Image {image_id} was not found.")
                return json_response(handler, 404, {"status": "error", "message": "Not found"})
            logger.info(f"Image {image_id} deleted")
            return json_response(handler, 200, {"status": "success", "message": f"Image {image_id} deleted"})
        except Exception as e:
            logger.info(f"Image {image_id} could not be deleted: {e}")
            json_response(handler, 500, {"status": "error", "message": f"Image {image_id} could not be deleted"})