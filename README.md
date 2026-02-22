# FIRE — Freedom Intelligent Routing Engine

Automatic ticket processing, AI enrichment (classification, sentiment, geocoding), and smart manager assignment with strict business rules.

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+ (for local dev)
- Node.js 18+ (for frontend, later)

### 1. Start with Docker Compose

```bash
# Copy env and set your OpenAI key
cp .env.example .env
# Edit .env and set OPENAI_API_KEY

# Start Postgres + Backend
docker compose up -d

# Backend will be available at http://localhost:8000
# API docs at http://localhost:8000/docs
# Health check at http://localhost:8000/api/health
```

### 2. Local Development (without Docker)

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or: .venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Start Postgres (via Docker or local install)
docker compose up postgres -d

# Run migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload --port 8000
```

### 3. Run Tests

```bash
pytest tests/ -v
```

### 4. Run Linter

```bash
ruff check app/ tests/
black --check app/ tests/
```

## Project Structure (Clean Architecture)

```
app/
├── domain/          # Entities, value objects, business policies (pure Python)
├── application/     # Use cases, port interfaces, DTOs
├── adapters/        # SQLAlchemy repos, OpenAI adapter, geocoder, CSV parser
└── infrastructure/  # FastAPI routes, DI wiring, middleware
```

**Dependency rule**: Domain ← Application ← Adapters ← Infrastructure

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check (DB connectivity) |
| GET | `/api/tickets` | List tickets with analytics |
| GET | `/api/tickets/{id}` | Ticket detail |
| POST | `/api/process/ingest` | Load CSVs into DB |
| POST | `/api/process` | Process all tickets (AI + assign) |
| GET | `/api/analytics/summary` | Aggregate stats |
| POST | `/api/analytics/assistant` | AI assistant (star task) |

## Database

PostgreSQL with tables: `offices`, `managers`, `tickets`, `ticket_analytics`, `assignments`, `round_robin_state`.

Migrations managed by Alembic: `alembic upgrade head`
