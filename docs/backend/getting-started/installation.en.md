# Installation

## Prerequisites

- Python 3.11+ (3.14 recommended)
- [uv](https://docs.astral.sh/uv/) package manager

## Step-by-Step Installation

### 1. Clone the Repository

```bash
git clone https://github.com/jjh4450/wapul.git
cd wapul/wapul-be
```

### 2. Install Dependencies

```bash
# Create .venv and install dependencies (dev group included by default)
uv sync

# Also install docs build dependencies
uv sync --group docs
```

### 3. Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit .env file with your settings
# See Configuration guide for details
```

### 4. Initialize Database

```bash
# Run database migrations
uv run alembic upgrade head
```

!!! note
    There are no migration files yet. During development, tables are created from SQLModel metadata on app startup.

### 5. Start the Server

```bash
# Development server with auto-reload
uv run uvicorn app.main:app --reload --port 2614
```

The server will be available at:
- REST API: http://localhost:2614/docs (Swagger UI)

## Docker Installation

### Using Docker Compose

```bash
# Build and run
docker compose up --build

# Run in background
docker compose up -d

# View logs
docker compose logs -f
```

### Using Pre-built Image

```bash
# Pull the latest image
docker pull ghcr.io/jjh4450/wapul-be:latest

# Run container
docker run -d \
  --name wapul-be \
  -p 2614:2614 \
  -e DATABASE_URL=sqlite:///./data/wapul.db \
  -e OIDC_ENABLED=false \
  -v wapul-data:/app/data \
  ghcr.io/jjh4450/wapul-be:latest
```

## Verify Installation

After starting the server, verify the installation:

```bash
# Health check
curl http://localhost:2614/health

# Expected response:
# {"status":"healthy", ..., "version":"dev", "environment":"development"}
```

## Troubleshooting

### Common Issues

**Port already in use**
```bash
# Use a different port
uv run uvicorn app.main:app --reload --port 8000
```

**Database connection error**
- Check `DATABASE_URL` in `.env` file
- Ensure database server is running (for PostgreSQL)
- Verify database permissions

**Docker: `unable to open database file`**
- The official image's entrypoint grants write permission on the `/app/data` volume. Use `-v wapul-data:/app/data` and `DATABASE_URL=sqlite:///./data/wapul.db` as in the `docker run` example above. Remove any previously failed container, pull the image again, and run.

**Module not found**
```bash
# Re-sync dependencies
uv sync
```
