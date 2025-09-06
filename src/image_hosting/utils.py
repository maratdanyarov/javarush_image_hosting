import http.server
import json

def json_response(handler: http.server.BaseHTTPRequestHandler, status: int, payload: dict):
    handler.send_response(status)
    handler.send_header('Content-Type', 'application/json; charset=utf-8')
    handler.end_headers()
    handler.wfile.write(json.dumps(payload).encode('utf-8'))

def infer_ext_from_format(pillow_format: str) -> str:
    fmt = (pillow_format or '').upper()
    if fmt == 'JPEG':
        return '.jpg'
    if fmt == 'PNG':
        return '.png'
    if fmt == 'GIF':
        return '.gif'
    return '.img'

def content_type_for_path(path: str) -> str:
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
