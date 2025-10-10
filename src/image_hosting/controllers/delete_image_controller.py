import http.server

from src.image_hosting.config import logger
from src.image_hosting.services.image_service import ImageService
from src.image_hosting.utils import json_response


class DeleteImageController:
    """
    Controller responsible for handling image deletion requests.
    """
    def __init__(self, image_service: ImageService | None = None):
        self.image_service = image_service or ImageService()

    def delete_image(self, handler: http.server.BaseHTTPRequestHandler, image_id: int):
        """Handle the HTTP DELETE request for removing an image by its ID.
            Args:
                handler: The active HTTP request handler instance.
                image_id: The ID of the image to delete.

            Returns:
                JSON response indicating the result of the deletion attempt.
        """
        logger.info("Received request to delete image with ID: %s", image_id)
        try:
            deleted = self.image_service.handle_delete_image(image_id)
            if not deleted:
                logger.info(f"Image with ID {image_id} not found in database.")
                return json_response(handler, 404, {"status": "error", "message": "Not found"})
            logger.info(f"Image with ID {image_id} deleted successfully.")
            return json_response(handler, 200, {"status": "success", "message": f"Image {image_id} deleted"})
        except Exception as e:
            logger.error(f"Failed to delete image with ID {image_id}: {e}")
            json_response(handler, 500, {"status": "error", "message": f"Image {image_id} could not be deleted"})