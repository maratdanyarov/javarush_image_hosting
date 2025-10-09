# Image Hosting Server

A minimalistic self-hosted image hosting service with a modern web interface. Upload, store, and share images (JPG, PNG, GIF) with ease.

## Features

- Upload images via web UI or API (POST /upload)
- JPG, PNG, and GIF support
- Metadata stored in PostgreSQL
- View uploaded images on /images-list
- Delete images (DB record + physical file)
- Pagination (10 images per page)
- Drag & drop upload support
- Copy-to-clipboard share links
- Persistent storage via Docker volumes
- Database backups (pg_dump automated/manual)
- Logging of all actions (logs/app.log)
- Nginx reverse proxy
- Built with Python, Pillow, psycopg2, Docker, HTML/CSS/JS

## 📂 Project Structure

```
image_hosting/
├── backups/                 # PostgreSQL backups (pg_dump)
├── images/                  # Uploaded files (Docker volume)
├── logs/                    # Logs (Docker volume)
├── src/
│   └── image_hosting/
│       ├── app.py           # Main HTTP server
│       ├── config.py        # Settings (upload dir, file size, logging)
│       ├── utils.py         # JSON responses, extension inference, etc.
│       ├── controllers/
│       │   └── upload_controller.py
│       │   └── list_controller.py
│       │   └── delete_controller.py
│       └── services/
│           └── image_service.py
├── static/
│   ├── index.html           # Web interface
│   ├── style.css
│   └── script.js
├── Dockerfile
├── docker-compose.yml
├── nginx.conf
└── pyproject.toml
```

## Running with Docker

```bash
docker compose up --build
```
- Web UI: http://localhost:8080
- Backend API: http://localhost:8000

## Database Schema
PostgreSQL table images:
```sql
CREATE TABLE images (
    id SERIAL PRIMARY KEY,
    filename TEXT NOT NULL,
    original_name TEXT NOT NULL,
    size INTEGER NOT NULL,
    upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    file_type TEXT NOT NULL
);
```
Each uploaded image stores metadata in PostgreSQL after successful save.

## API Endpoints

### POST `/upload`

Upload an image file via `multipart/form-data`.

#### Request
```http
POST /upload HTTP/1.1
Content-Type: multipart/form-data; boundary=...

--boundary
Content-Disposition: form-data; name="file"; filename="photo.png"
Content-Type: image/png

(binary data)
```

#### Response
```json
{
  "status": "success",
  "url": "http://localhost:8000/images/your_unique_file.jpg"
}
```

### GET /images-list?page=<n>

Get paginated list of uploaded images (10 per page).

Response Example
```json
{
  "status": "success",
  "page": 1,
  "pagination": {
    "total_pages": 3,
    "total_items": 25
  },
  "data": [
    {
      "id": 1,
      "filename": "img_001.jpg",
      "original_name": "photo.jpg",
      "size_kb": 245,
      "upload_time": "2025-01-24T15:30:00",
      "file_type": "jpg",
      "url": "/images/img_001.jpg"
    }
  ]
}
```

### DELETE /delete/<id>
Deletes an image and its metadata.

Behavior
	•	Removes the DB record (DELETE FROM images WHERE id = <id>)
	•	Deletes the file from /images
	•	Logs the result

Response
```json
{ "status": "success", "message": "Image deleted successfully." }
```

## Database Backup (PostgreSQL)
### Manual Backup
```bash
ts=$(date +'%F_%H%M%S') \
&& docker exec -t postgres_container \
   pg_dump -U postgres images_db > "backups/backup_${ts}.sql"
```
### Restore from Backup
```bash
docker exec -i postgres_container \
  psql -U postgres images_db < backups/backup_2025-01-24_153000.sql
```

## Frontend

- Responsive, minimal, light/dark UI
- Drag & drop uploads
- Paginated image table with delete buttons
- Copy shareable image URLs
- LocalStorage-based caching
- Smooth user interactions via JS fetch API

## Configuration (config.py)
You can configure the following in `config.py`:
- `UPLOAD_DIR`: Folder for uploaded files
- `MAX_FILE_SIZE`: Max upload size in bytes
- `ALLOWED_EXTENSIONS`: Allowed file types
- `DB_CONFIG`: PostgreSQL connection params
- `logger` - Logging configuration

## Logs
All major actions are logged to logs/app.log:
- Image uploads
- Deletions
- Database connections
- Errors & exceptions
- Backup operations

## Example Use Cases

- Share screenshots or memes quickly
- Host personal project assets
- Educational backend + frontend app
- Example for learning full-stack Dockerized Python web development

## Notes
This project is for educational or private use; not recommended for public internet deployment without further hardening.

## License

MIT License © 2025