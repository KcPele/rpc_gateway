# NodeBridge RPC Gateway - Project Memory

## Project Overview
- **Current Stack:** TypeScript / Express / MongoDB (Mongoose) — running on PM2 port 8888 (live production)
- **New Stack:** Python / FastAPI / MongoDB (Beanie/Motor) — ported and running on port 8888 (separate `nodebridge` DB)
- **Purpose:** Multi-tenant RPC gateway for Ethereum-compatible chains
- **Repo:** https://github.com/KcPele/rpc_gateway

## Key Decisions
- **Date: April 3, 2026** — Decided to port from TS/Express to FastAPI for speed and efficiency
- **Database:** FastAPI uses `nodebridge` DB (separate from Node.js `test` DB) to avoid schema conflicts
- **Port:** Both use 8888 — run one at a time, switch between them
- **Frontend:** rpc_frontend uses NextAuth with `/api/auth/callback/credentials`
- **Frontend URL:** https://nodebridge.xyz
- **Backend URL:** https://eth.nodebridge.xyz
- **CORS:** nginx proxies `eth.nodebridge.xyz` → `localhost:8888`

## Stack Mapping (TS → Python)
| TS/Express | FastAPI |
|---|---|
| Express | FastAPI + uvicorn |
| Mongoose | Beanie/Motor |
| jsonwebtoken | PyJWT |
| http-proxy-middleware | httpx |
| prom-client | prometheus-client |
| express-rate-limit | slowapi |
| Jest | pytest + pytest-asyncio |

## Files Ported (All Complete)
- Project scaffold, Database connection, Models, Auth middleware + routes
- API key middleware, Rate limiting middleware, Admin middleware
- Proxy routes + load balancing, Admin routes (chains/nodes/management)
- App management routes, Prometheus metrics, Pydantic schemas
- Utils, Dockerfile (port 8881), AGENTS.md
- Tests (81 passing) + Live integration test script

## Critical Bugs Fixed (April 3, 2026)

### Database & Models
- `.env` not loaded at startup → added `dotenv.load_dotenv()` in main.py
- `User.find_one(User.id == user_id)` failed with string IDs → fixed with `PydanticObjectId(user_id)`
- Chain model missing `created_at`/`updated_at` fields → added
- Chain model `chain_id: str` rejected int from frontend → changed to `str | int`
- Service converts chain_id to str on save → `chain_id=str(chain_id)`
- Default DB name was `test` → changed to `nodebridge`
- Index conflicts with existing MongoDB indexes → removed Beanie index definitions
- Mongoose camelCase vs Beanie snake_case mismatch → used separate DB

### Request/Response Format
- Response not wrapped in `{success, data}` → fixed all routes to match Node.js format
- Error format used `{detail}` not `{error}` → added custom exception handler
- Field names were snake_case, frontend expects camelCase → added aliases in schemas
- `UpdateEmailRequest` missing `new_email` field → added

### Routes & Schemas
- Trailing slashes caused 307 redirects (POST→GET) → removed from `/apps` routes
- Request schemas rejected camelCase input → added `Field(alias=...)` with `populate_by_name=True`
- `|` operator in Beanie queries didn't work → used `{"$or": [...]}` dict queries
- `pwd_context` import error in admin_management service → used `User.hash_password()`

### CORS & Middleware
- CORS preflight (OPTIONS) returned 405 → added CORS middleware
- JWT middleware used `os.getenv()` not Pydantic Settings → added `dotenv.load_dotenv()`
- Default JWT_SECRET in Pydantic Settings not configured → set in .env

### API Key Middleware
- API key lookup failed with snake_case fields → fixed field name lookups
- Daily request tracking used wrong field names → added camelCase fallbacks

## OpenCode Sessions Log
- **09:00** — Initial codebase analysis
- **09:07-09:35** — Phase 1-4: scaffold, middleware, routes, Dockerfile
- **11:30** — Wrote 81 tests + fixed auth middleware bug
- **12:49** — Fixed response format to match frontend (camelCase)
- **13:21** — All 81 tests pass, endpoints match Node.js format
- **14:44** — Fixed Chain model missing created_at/updated_at
- **14:54** — Fixed request schemas to accept camelCase from frontend
- **15:05** — Fixed Chain model to accept int chainId
- **15:21** — Fixed trailing slash redirect bug on /apps routes

## Test Results
- 81 tests passing (pytest + httpx + mongomock-motor)
- Live integration test script: `tests/test_live_endpoints.py`
- Tests cover: auth, admin chains/mgmt/nodes, apps, proxy routes

## Benchmark Results
| Endpoint | Node.js | FastAPI |
|---|---|---|
| /health | 2.0ms, 493 RPS | 2.0ms, 500 RPS |
| /auth/me | 4.1ms, 242 RPS | 2.4ms, 409 RPS |
| /admin/chains | 4.3ms, 233 RPS | 3.4ms, 293 RPS |
| /auth/register | 253ms, 4 RPS | 280ms, 4 RPS |

## Production Setup
- **Node.js:** PM2 (`rpc-backend`), port 8888, `test` DB
- **FastAPI:** uvicorn (manual), port 8888, `nodebridge` DB
- **Nginx:** `eth.nodebridge.xyz` → `localhost:8888` with SSL
- **Admin user:** admin@nodebridge.com / Qwerty123456 (is_admin: true)
- **Dockerfile:** port 8881 (for containerized deployment)
