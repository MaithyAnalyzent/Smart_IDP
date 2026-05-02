# Doc Intelligence Pipeline

A **generic, pipeline-based document intelligence API** — production-ready and fully industry-agnostic. Submit any document; the platform classifies, extracts structured data, and validates it against your rules automatically.

---

## Problem Statement

Organisations across every industry need to process unstructured documents — invoices, contracts, forms, reports, identity cards — and turn them into structured, validated data. Doing this reliably requires:

- Detecting what kind of document it is
- Extracting the right fields for that document type
- Validating the extracted data against business rules

This platform solves all three steps in a single, configurable pipeline with no hard-coded document types, no domain-specific logic, and no proprietary dependencies.

---

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                   REST API (FastAPI)                  │
│   /api/v1/jobs   /api/v1/config   /api/v1/results    │
└────────────────────┬─────────────────────────────────┘
                     │  BackgroundTask
┌────────────────────▼─────────────────────────────────┐
│                  PipelineRunner                       │
│   Threads a single PipelineContext through stages     │
│                                                       │
│  ┌──────────┐  ┌──────────┐  ┌─────────┐  ┌───────┐ │
│  │  Ingest  │→ │ Classify │→ │ Extract │→ │Validate│ │
│  └──────────┘  └──────────┘  └─────────┘  └───────┘ │
└──────────┬──────────────────────────────┬────────────┘
           │                              │
┌──────────▼──────────┐   ┌──────────────▼────────────┐
│  Object Storage      │   │  PostgreSQL (SQLAlchemy)  │
│  (S3 / MinIO)        │   │  TenantProfile            │
│  Raw document files  │   │  DocumentSchema           │
└─────────────────────┘   │  FieldSchema              │
                           │  ProcessingRule           │
┌─────────────────────┐   │  PipelineJob              │
│  LLM Provider        │   └───────────────────────────┘
│  OpenAI or Anthropic │
│  (direct API calls)  │
└─────────────────────┘
```

### Core Design Patterns

| Pattern | Where Used | Why |
|---|---|---|
| **Sequential Pipeline** | `PipelineRunner` | Predictable, debuggable, no hidden state |
| **Protocol / Structural Typing** | `interfaces/` | Swap implementations without inheritance |
| **Factory Function** | `services/llm/__init__.py` | Single switch for all LLM providers |
| **Context Object** | `PipelineContext` | Eliminates inter-stage coupling |
| **Repository (async)** | `services/database/session.py` | Testable, transaction-safe DB access |
| **Event Bus** | `core/events.py` | Decoupled side-effects (webhooks, alerts) |

---

## Project Structure

```
SmartDocPro/
├── src/
│   ├── api/
│   │   ├── server.py          # FastAPI app factory + lifespan
│   │   ├── middleware.py      # Request logging middleware
│   │   └── routes/
│   │       ├── pipeline.py    # Job submission + status endpoints
│   │       ├── config.py      # Tenant + schema management endpoints
│   │       └── results.py     # Job listing + export endpoints
│   └── pipeline/
│       ├── context.py         # PipelineContext dataclass
│       ├── runner.py          # PipelineRunner (sequential executor)
│       └── stages/
│           ├── base.py        # PipelineStage abstract base
│           ├── ingest.py      # File validation + object storage upload
│           ├── classify.py    # LLM-based document type detection
│           ├── extract.py     # LLM-based structured field extraction
│           └── validate.py    # LLM-based rule evaluation
├── core/
│   ├── models.py              # SQLAlchemy ORM models
│   ├── schemas.py             # Pydantic request/response schemas
│   ├── exceptions.py          # Typed exception hierarchy
│   └── events.py              # Async event bus
├── services/
│   ├── database/session.py    # Async engine + session factory
│   ├── storage/
│   │   ├── base.py            # IStorage protocol
│   │   └── s3_store.py        # S3-compatible implementation
│   └── llm/
│       ├── __init__.py        # get_llm_provider() factory
│       ├── openai_provider.py
│       └── anthropic_provider.py
├── configs/
│   ├── settings.py            # Pydantic Settings (env-driven)
│   └── pipeline.yaml          # Stage enable/tune without code changes
├── utils/
│   ├── logger.py              # structlog setup
│   ├── retry.py               # Exponential-backoff decorator
│   └── file_handler.py        # MIME detection from magic bytes
├── interfaces/
│   ├── extractor.py           # IExtractor protocol
│   ├── classifier.py          # IClassifier protocol
│   ├── validator.py           # IValidator protocol
│   └── llm.py                 # LLMProvider protocol
├── .env.example
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

---

## Quick Start (Docker)

**Prerequisites:** Docker Desktop installed and running.

```bash
# 1. Clone or copy this project
cd generic-solution

# 2. Create your environment file
cp .env.example .env
# Edit .env — set SECRET_KEY, MASTER_API_KEY, LLM keys, MinIO credentials

# 3. Start all services
docker-compose up --build

# 4. Open the interactive API docs
#    http://localhost:8000/docs
```

Services started:

| Service | URL | Purpose |
|---|---|---|
| API | http://localhost:8000 | REST API + Swagger UI |
| PostgreSQL | localhost:5432 | Relational database |
| MinIO Console | http://localhost:9001 | Object storage browser |

---

## Development Without Docker

```bash
# 1. Start only the infrastructure
docker-compose up -d postgres minio

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Set DATABASE_URL=postgresql://docuser:docpass@localhost:5432/doc_intel
# Set STORAGE_ENDPOINT=http://localhost:9000
# Set STORAGE_USE_SSL=false

# 5. Run the API
uvicorn src.api.server:app --host 0.0.0.0 --port 8000 --reload
```

---

## Configuration Reference

All configuration is driven by environment variables. See `.env.example` for the full list.

| Variable | Required | Default | Description |
|---|---|---|---|
| `SECRET_KEY` | ✅ | — | App secret (min 32 chars) |
| `MASTER_API_KEY` | ✅ | — | Admin-level operations key |
| `DATABASE_URL` | ✅ | — | PostgreSQL or SQLite connection string |
| `STORAGE_ACCESS_KEY` | ✅ | — | S3 / MinIO access key |
| `STORAGE_SECRET_KEY` | ✅ | — | S3 / MinIO secret key |
| `STORAGE_BUCKET` | ✅ | — | Bucket name for document files |
| `STORAGE_ENDPOINT` | | — | Leave blank for real AWS S3 |
| `LLM_PROVIDER` | | `openai` | `openai` or `anthropic` |
| `OPENAI_API_KEY` | ✅ (if openai) | — | OpenAI API key |
| `ANTHROPIC_API_KEY` | ✅ (if anthropic) | — | Anthropic API key |
| `ALLOWED_ORIGINS` | | `` | Comma-separated CORS origins |
| `MAX_FILE_SIZE_MB` | | `50` | Maximum upload size |
| `LOG_FORMAT` | | `json` | `json` or `console` |

### Pipeline YAML

Tune stage behaviour in `configs/pipeline.yaml` — no code changes required:

```yaml
pipeline:
  stages:
    - name: classify
      options:
        confidence_threshold: 0.70   # ← raise for stricter classification
        fallback_type: generic
    - name: validate
      options:
        fail_fast: false             # ← set true to abort on first rule failure
```

---

## API Usage

### 1. Register a Tenant

```bash
curl -X POST http://localhost:8000/api/v1/config/tenants \
  -H "Content-Type: application/json" \
  -d '{"name": "your-organisation"}'
```

Response includes `tenant_id` and a one-time `api_key` — store it securely.

### 2. Define a Document Schema

```bash
curl -X POST http://localhost:8000/api/v1/config/tenants/{tenant_id}/schemas \
  -H "Content-Type: application/json" \
  -d '{
    "doc_type": "invoice",
    "description": "Standard vendor invoice",
    "field_schemas": [
      {"field_name": "invoice_number", "field_type": "string", "required": true},
      {"field_name": "total_amount",   "field_type": "number", "required": true},
      {"field_name": "issue_date",     "field_type": "date",   "required": true}
    ],
    "rules": [
      {"rule_description": "total_amount must be greater than zero", "severity": "error"},
      {"rule_description": "issue_date must not be in the future",   "severity": "warning"}
    ]
  }'
```

### 3. Submit a Document

```bash
curl -X POST http://localhost:8000/api/v1/jobs/ \
  -F "file=@/path/to/document.pdf" \
  -F "tenant_id={tenant_id}"
```

Returns `{"job_id": "...", "status": "queued"}` immediately.

### 4. Poll for Results

```bash
curl http://localhost:8000/api/v1/jobs/{job_id}
```

### 5. Export Extracted Fields

```bash
curl http://localhost:8000/api/v1/results/jobs/{job_id}/export
```

---

## Extending the Platform

### Add a New Pipeline Stage

1. Create `src/pipeline/stages/your_stage.py` subclassing `PipelineStage`.
2. Implement `name` and `process(ctx)`.
3. Add an instance to the `PipelineRunner` list in `src/api/routes/pipeline.py`.

```python
class EnrichStage(PipelineStage):
    name = "enrich"

    async def process(self, ctx: PipelineContext) -> PipelineContext:
        # Read from ctx, write back to ctx.extracted_fields or ctx.metadata
        ctx.metadata["enriched"] = True
        return ctx
```

### Switch LLM Provider

Set `LLM_PROVIDER=anthropic` in `.env` — no code changes needed.

To add a third provider (e.g. Gemini):

1. Create `services/llm/gemini_provider.py` implementing the `LLMProvider` protocol.
2. Add a branch in `services/llm/__init__.py`'s `get_llm_provider()`.

### Add a New Document Type

No code changes required — it is pure configuration:

1. Call `POST /api/v1/config/tenants/{id}/schemas` with the new `doc_type`.
2. Add field definitions and validation rules.
3. The pipeline uses them automatically the next time a document of that type is submitted.

---

## Production Deployment

### Security Checklist

- [ ] Set a strong random `SECRET_KEY` (≥ 32 bytes).
- [ ] Set `MASTER_API_KEY` to a strong random value.
- [ ] Replace all MinIO credentials (`MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`).
- [ ] Set `APP_ENV=production` and `DEBUG=false`.
- [ ] Populate `ALLOWED_ORIGINS` with your actual frontend domain(s).
- [ ] Store all secrets in a secrets manager — not in `.env` files on disk.
- [ ] Enable HTTPS via a reverse proxy (nginx, Caddy, API Gateway).
- [ ] Set a strong PostgreSQL password; use a dedicated application user.
- [ ] Set S3 bucket policy to private.

### Secrets Management

| Platform | Recommended approach |
|---|---|
| Kubernetes | Secrets + ConfigMaps |
| AWS ECS / Fargate | AWS Secrets Manager or Parameter Store |
| Railway / Render / Fly.io | Platform-native environment variable management |
| Docker Swarm | Docker Secrets |

### Horizontal Scaling

The API is fully stateless — scale by adding replicas behind a load balancer. All replicas share the same PostgreSQL and S3 configuration; no sticky sessions required.

---

## Contributing

1. Fork and create a feature branch.
2. Install dev dependencies: `pip install -r requirements.txt`
3. Run linting: `ruff check . && black --check .`
4. Run tests: `pytest`
5. Open a pull request with a clear description.

---
Inspired by agent-based AI systems, I redesigned the architecture into a deterministic pipeline model to improve observability, reduce complexity, and remove heavy framework dependencies.

## License

Released under the [MIT License](LICENSE).
