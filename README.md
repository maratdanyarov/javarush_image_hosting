# Image Hosting Server

A minimalistic self-hosted image hosting service with a modern web interface. Upload, store, and share images (JPG, PNG, GIF) with ease.

## Features

- Upload images via web UI or `POST /upload` endpoint
- JPG, PNG, and GIF support
- Maximum file size: 5MB
- Drag & drop or file browser support
- Persistent storage using Docker volumes
- Beautiful UI with light/dark theme support
- Frontend-only image history (via LocalStorage)
- Copy-to-clipboard shareable links
- Nginx reverse proxy support
- Built with Python, Pillow, Docker, and pure HTML/CSS/JS

## 📂 Project Structure

```
image_hosting/
├── images/                  # Uploaded files (Docker volume)
├── logs/                    # Logs (Docker volume)
├── src/
│   └── image_hosting/
│       ├── app.py           # Main HTTP server
│       ├── config.py        # Settings (upload dir, file size, logging)
│       ├── utils.py         # JSON responses, extension inference, etc.
│       ├── controllers/
│       │   └── upload_controller.py
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
- Web interface available at: http://localhost:8080  
- API available at: http://localhost:8000/upload

## API

### POST `/upload`

Upload an image file via `multipart/form-data`.

#### Request
```http
POST /upload HTTP/1.1
Content-Type: multipart/form-data; boundary=...

--boundary
Content-Disposition: form-data; name="file"; filename="image.jpg"
Content-Type: image/jpeg

(binary image data)
```

#### Response
```json
{
  "status": "success",
  "url": "http://localhost:8000/images/your_unique_file.jpg"
}
```

## Frontend

- Responsive, minimal, clean interface
- Image previews stored in browser memory (localStorage)
- Dark mode friendly
- JS-powered drag-and-drop, upload, delete, copy link, etc.

## Configuration

You can configure the following in `config.py`:
- `UPLOAD_DIR`: Path to store uploaded images
- `MAX_FILE_SIZE`: Max upload size (in bytes)
- `ALLOWED_EXTENSIONS`: Permitted file types

## Database backup (PostgreSQL в Docker)

**Manual backup (via embedded pg_dump):**
```bash
ts=$(date +'%F_%H%M%S') \
&& docker exec -t postgres_container \
   pg_dump -U postgres images_db > "backups/backup_${ts}.sql"
```

## Notes

- This project is for educational or private use; not recommended for public internet deployment without further hardening.
- Currently, image deletion is only client-side (localStorage). Server-side delete is **not** implemented.

## Example Use Cases

- Quickly share screenshots or memes with friends
- Educational backend + frontend project

## License

MIT License © 2025