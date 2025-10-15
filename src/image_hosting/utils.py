import http.server
import json
import image_format

def json_response(handler: http.server.BaseHTTPRequestHandler, status: int, payload: dict):
    """
    Send a JSON response to the client.
    Args:
        handler: The HTTP request handler.
        status: HTTP status code to return.
        payload: Dictionary to be serialized as JSON body.
    """
    handler.send_response(status)
    handler.send_header('Content-Type', 'application/json; charset=utf-8')
    handler.end_headers()
    handler.wfile.write(json.dumps(payload).encode('utf-8'))

def infer_ext_from_format(pillow_format: str) -> str:
    """
    Infer file extension based on Pillow image format.
    Args:
        pillow_format: Format string (e.g., 'JPEG', 'PNG').
    Returns:
        File extension including dot (e.g., '.jpg').
    """
    fmt = (pillow_format or '').upper()
    if fmt == image_format.JPEG:
        return '.jpg'
    if fmt == image_format.PNG:
        return '.png'
    if fmt == image_format.GIF:
        return '.gif'
    return '.img'

def content_type_for_path(path: str) -> str:
    """
    Guess the Content-Type header based on file extension.
    Args:
        path: File path or URL.
    Returns:
        MIME type string.
    """
    if path.endswith('.html'):
        return 'text/html'
    if path.endswith('.css'):
        return 'text/css'
    if path.endswith('.js'):
        return 'application/javascript'
    if path.endswith(('.png', '.jpg', '.jpeg', '.gif')):
        ext = path.split('.')[-1].lower()
        if ext == 'jpg':
            return 'image/jpeg'
        return f'image/{ext}'
    return 'application/octet-stream'
