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
- Model used in OpenCode: qwen3.6-plus-free (coding agent)
- Project-specific memory only (not in Claw's general MEMORY.md)

## Original Architecture
- Dynamic multi-chain support (chains from env var prefixes)
- Multi-node load balancing (comma-separated URLs, random selection)
- API key-based access with per-app keys and chain routing
- Token bucket rate limiting (in-memory, per-key)
- Batched counter writes (5s flush)
- API key caching (60s TTL)
- Prometheus metrics
- Admin panel for chains/users/apps/settings

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

## Files Ported
- [x] Project scaffold (requirements.txt, main.py, config)
- [x] Database connection (MongoDB async via Beanie/Motor)
- [x] Models (User, App, Chain, DefaultAppSettings)
- [x] Auth middleware + routes
- [x] API key middleware
- [x] Rate limiting middleware
- [x] Admin middleware
- [x] Proxy routes + load balancing
- [x] Admin routes (split into chains/nodes/management)
- [x] App management routes
- [x] Prometheus metrics
- [x] Pydantic schemas
- [x] Utils (response helpers)
- [x] Dockerfile (port 8881)
- [x] AGENTS.md (project rules)
- [x] Tests (81 passing)
- [x] Full integration testing

## Known Issues Fixed in Port
1. `adminOnly` checks `isAdmin` ✅ (was missing in original)
2. `GET /chains` has admin guard ✅
3. Fake analytics data — removed
4. In-memory rate limiter — kept (Redis-ready design noted)

## OpenCode Sessions Log
- **April 3, 2026 09:00** — Initial codebase analysis (completed, found 20 issues)
- **April 3, 2026 09:07** — Phase 1: scaffold (main.py, config, database, requirements) ✅
- **April 3, 2026 09:17** — Phase 2: middleware (auth, api_key, rate_limit, admin) ✅
- **April 3, 2026 09:25** — Phase 3: routes + schemas (auth, proxy, admin, apps, metrics) ✅
- **April 3, 2026 09:35** — Phase 4: Dockerfile, utils, admin split, router wiring ✅
- **April 3, 2026 09:50** — Manual fixes by Claw: bcrypt compat, route wiring, schema fixes ✅
- **April 3, 2026 11:30** — OpenCode wrote tests (81 passing) + fixed auth middleware bug ✅

## Bugs Fixed During Port
- passlib + bcrypt 5.x incompatibility → switched to direct bcrypt usage
- Pydantic settings rejecting env vars → added `extra="ignore"`
- Double route prefixes → removed redundant prefix from include_router
- Missing `name` field in RegisterRequest schema
- JWT_SECRET hardcoded check → use settings.jwt_secret
- Missing `@staticmethod` decorator on hash_password
- Missing deps: PyJWT, email-validator, slowapi
- Beanie 2.x + Motor 3.7 compat → pinned Beanie 1.29.0 + Motor 3.6.1
- **Auth middleware:** `User.find_one(User.id == user_id)` failed with string IDs → fixed with `PydanticObjectId(user_id)`
- **Schema:** `UpdateEmailRequest` missing `new_email` field → added it
- **Database:** `.env` not loaded at startup → added `dotenv.load_dotenv()` in main.py

## Test Results (April 3, 2026)
- 81 tests passing (pytest + httpx + mongomock-motor)
- Tests cover: auth, admin chains/mgmt/nodes, apps, proxy routes

## Benchmark Results (April 3, 2026)
| Endpoint | Node.js (Express) | FastAPI (Python) |
|---|---|---|
| /health | 2.0ms, 493 RPS | 2.0ms, 500 RPS |
| /auth/me | 4.1ms, 242 RPS | 2.4ms, 409 RPS |
| /apps/ | 4.3ms, 234 RPS | 4.8ms, 207 RPS |
| /admin/chains | 4.3ms, 233 RPS | 3.4ms, 293 RPS |
| /auth/register | 253ms, 4 RPS | 280ms, 4 RPS |
| /auth/login | 252ms, 4 RPS | 279ms, 4 RPS |

## Production Setup
- **Node.js:** PM2 (`rpc-backend`), port 8888, `test` DB
- **FastAPI:** uvicorn (manual), port 8888, `nodebridge` DB
- **Admin user:** admin@nodebridge.com / Qwerty123456 (is_admin: true)
- **Dockerfile:** port 8881 (for containerized deployment)
