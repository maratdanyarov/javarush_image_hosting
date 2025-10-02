"""
Configuration module for image hosting backend.
Defines paths, limits, logging, and supported formats.
"""
import os
import logging
from pathlib import Path

BASE_DIR = Path(os.environ.get("APP_BASE", "/app")).resolve()

STATIC_FILES_DIR = str(BASE_DIR / 'static')
UPLOAD_DIR = str(BASE_DIR / 'images')
LOG_DIR = str(BASE_DIR / 'logs')

MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = ['JPEG', 'PNG', 'GIF']


os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'app.log')),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
