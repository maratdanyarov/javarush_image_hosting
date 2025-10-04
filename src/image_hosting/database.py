import os

import psycopg2
from src.image_hosting.config import logger

DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'database': os.environ.get('DB_NAME', 'images_db'),
    'user': os.environ.get('DB_USER', 'postgres'),
    'password': os.environ.get('DB_PASSWORD', 'password'),
    'port': os.environ.get('DB_PORT', '5432'),
}

def get_connection():
    """Create a database connection."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        return None

def test_connection():
    """Check database connection."""
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            logger.info(f"Connected to database: {version}")
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error testing connection to database: {e}")
            return False
    return False

def init_database():
    conn = get_connection()
    if not conn:
        return False

    try:
        cursor = conn.cursor()
        create_table_query = """
                             CREATE TABLE IF NOT EXISTS images
                             (
                                 id SERIAL PRIMARY KEY,
                                 filename TEXT NOT NULL,
                                 original_name TEXT NOT NULL,
                                 size INTEGER NOT NULL,
                                 upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                 file_type TEXT NOT NULL
                             ); 
                             """

        cursor.execute(create_table_query)
        conn.commit()
        logger.info(f"Table created successfully: {create_table_query}")
        cursor.close()
        conn.close()

        return True
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        return False
