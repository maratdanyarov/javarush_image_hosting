import os

import psycopg2
from src.image_hosting.config import logger

DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'db'),
    'database': os.environ.get('DB_NAME', 'images_db'),
    'user': os.environ.get('DB_USER', 'postgres'),
    'password': os.environ.get('DB_PASSWORD', 'password'),
    'port': os.environ.get('DB_PORT', '5432'),
}

def get_connection():
    """
    Create and return a new PostgreSQL database connection.
    Returns:
        psycopg2 connection object if successful, otherwise None.
    """
    try:
        logger.debug(f"Attempting to connect to database at {DB_CONFIG["host"]}:{DB_CONFIG["port"]}")
        conn = psycopg2.connect(**DB_CONFIG)
        logger.debug("Database connection established.")
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        return None

def test_connection():
    """
    Verify database connectivity by executing a simple query.
    Returns:
        True if the connection and query succeeded, False otherwise.
    """
    logger.debug("Testing database connection...")
    conn = get_connection()
    if not conn:
        logger.error("Database connection test failed: unable to establish connection.")
        return False

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        logger.info("Connected to database: %s", version[0] if version else "Unknown version")
        return True
    except Exception as e:
        logger.error("Error testing connection to database: %s", e, exc_info=True)
        return False
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass

def init_database():
    """
    Initialize the database by ensuring that the 'images' table exists.
    Creates the table if it does not already exist.
    Returns:
        True if initialization succeeded, False otherwise.
    """
    logger.debug("Initializing database schema (images table).")
    conn = get_connection()
    if not conn:
        logger.error("Database initialization failed: connection is None.")
        return False

    create_table_query = """
                         CREATE TABLE IF NOT EXISTS images
                         (
                             id SERIAL PRIMARY KEY,
                             filename TEXT NOT NULL,
                             original_name TEXT NOT NULL,
                             size INTEGER NOT NULL,
                             upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                             file_type TEXT NOT NULL
                         ); \
                         """

    try:
        cursor = conn.cursor()
        cursor.execute(create_table_query)
        conn.commit()
        logger.info(f"Table created successfully: {create_table_query}")
        return True
    except Exception as e:
        logger.error("Error initializing database: %s", e, exc_info=True)
        return False
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        try:
            conn.close()
        finally:
            pass
