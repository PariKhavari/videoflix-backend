# Videoflix Backend 🎬

A Django REST Framework backend for a video streaming platform with HLS support, JWT authentication, background video processing using Django RQ, and Docker-based deployment.

---

## Features

- User registration with email activation
- JWT authentication (login, refresh, logout)
- Password reset functionality
- Video upload via Django Admin
- Automatic thumbnail generation (FFmpeg)
- HLS video conversion (480p, 720p, 1080p)
- Background processing using Redis + Django RQ
- Protected HLS streaming endpoints (JWT required)
- Dockerized setup (PostgreSQL, Redis, Web, Worker)

---

## Tech Stack

- Python 3.12
- Django
- Django REST Framework
- SimpleJWT
- PostgreSQL
- Redis
- Django RQ
- FFmpeg
- Docker & Docker Compose

---

## Project Structure

videos/
- models.py
- signals.py
- tasks.py
- api/
  - serializers.py
  - views.py
  - urls.py

media/
- videos/
- thumbnail/
- hls/

---

## Environment Configuration ⚙️

Create a `.env` file in the project root with the following variables:

DB_NAME=videoflix
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=db
DB_PORT=5432

DJANGO_SECRET_KEY=your-secret-key
DJANGO_DEBUG=True

DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@example.com
DJANGO_SUPERUSER_PASSWORD=adminpassword

EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=Videoflix <your-email@gmail.com>

---

## Running the Project

### 1. Build and start containers

docker-compose up --build

### 2. Access services

Backend API:
http://127.0.0.1:8000/

Django Admin:
http://127.0.0.1:8000/admin/

Django RQ Dashboard:
http://127.0.0.1:8000/django-rq/

---

## Authentication Flow

### Register
POST /api/register/

An activation email will be sent to the user.

### Activate Account
GET /api/activate/<uidb64>/<token>/

### Login
POST /api/login/

Returns:
- access token
- refresh token

### Refresh Token
POST /api/token/refresh/

---

## Video Processing Flow 🎥

1. Upload video via Django Admin.
2. post_save signal triggers background conversion task.
3. Worker converts video into HLS format:
   - 480p
   - 720p
   - 1080p
4. Thumbnail is generated automatically.
5. HLS files are stored in:

media/hls/<video_id>/<resolution>/

---

## Streaming Endpoints

HLS Manifest:
GET /api/video/<id>/<resolution>/index.m3u8

HLS Segment:
GET /api/video/<id>/<resolution>/<segment>.ts

JWT authentication required.

---

## Worker Setup

Worker runs as a separate Docker service:

docker-compose up worker

Multiple workers can be started for parallel video processing.

---

## Notes

- media/ is excluded from Git (.gitignore)
- Static files are collected automatically on container start
- FFmpeg must be installed in the Docker image
- Redis is required for background jobs

---

## License

This project was created for educational purposes.
