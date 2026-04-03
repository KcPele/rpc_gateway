# AGENTS.md - OpenCode Rules for This Project

## Code Style Rules

### No God Files
- No single file should exceed **500 lines of code**
- If a file is getting too long, split it into focused modules
- Each file should have a **single responsibility**

### Keep It DRY
- Do not repeat logic across files
- Extract shared utilities into `fastapi_app/utils/` or `fastapi_app/services/`
- Reuse schemas, dependencies, and helpers — don't copy-paste
- If two routes do similar validation, make one dependency

### Project Structure
- `config/` — Settings, env, database connection
- `models/` — Beanie/MongoDB document models
- `schemas/` — Pydantic request/response models (keep separate from DB models)
- `routes/` — FastAPI routers, thin — delegate logic to services
- `services/` — Business logic (don't put logic in route handlers)
- `middleware/` — Auth, rate limiting, API key validation
- `utils/` — Shared helpers (response formatting, error handling, etc.)

### General
- Use `async/await` everywhere (this is an async codebase)
- Type hints on all function signatures
- Docstrings on public functions
- No `Any` types — use proper Pydantic models or generics
- All env vars go through `config/settings.py` — never read `os.environ` directly elsewhere
