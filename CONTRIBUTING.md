# Contributing

## Dev Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn fastapi_app.main:app --reload --port 8888
```

## Project Structure

```
fastapi_app/
├── main.py          # App factory, lifespan, middleware
├── database.py      # Beanie document models
├── config/          # Settings (env var parsing, chain discovery)
├── routes/          # Route handlers (auth, apps, proxy, admin)
├── middleware/      # API key validation, rate limiting
├── services/        # Business logic (admin, metrics, node health)
├── schemas/         # Pydantic request/response models
└── utils/           # Shared helpers (response formatting)
```

## Running Tests

```bash
pytest tests/
```

## Pull Requests

- Keep changes focused — one concern per PR
- Update `wiki/routes.md` if you add or change any endpoints
- Don't break the proxy hot path (`routes/proxy.py`) without benchmarking
