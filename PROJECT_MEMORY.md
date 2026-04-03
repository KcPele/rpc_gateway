# NodeBridge RPC Gateway - Project Memory

## Project Overview
- **Current Stack:** TypeScript / Express / MongoDB (Mongoose)
- **Porting To:** Python / FastAPI / MongoDB (Beanie or Motor)
- **Purpose:** Multi-tenant RPC gateway for Ethereum-compatible chains

## Key Decisions
- **Date: April 3, 2026** — Decided to port from TS/Express to FastAPI for speed and efficiency
- Model used in OpenCode: qwen3.6-plus-free
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
| jsonwebtoken | PyJWT / python-jose |
| http-proxy-middleware | httpx |
| prom-client | prometheus-client |
| express-rate-limit | slowapi |
| Jest | pytest + pytest-asyncio |

## Files Ported
<!-- Track progress here -->
- [x] Project scaffold (requirements.txt, main.py, config)
- [x] Database connection (MongoDB async via Beanie/Motor)
- [x] Models (User, App, Chain, DefaultAppSettings)
- [x] Auth middleware + routes
- [x] API key middleware
- [x] Rate limiting middleware
- [x] Admin middleware (fixed isAdmin bug)
- [x] Proxy routes + load balancing
- [x] Admin routes (split into chains/nodes/management)
- [x] App management routes
- [x] Prometheus metrics
- [x] Pydantic schemas
- [x] Utils (response helpers)
- [x] Dockerfile
- [x] AGENTS.md (project rules)
- [ ] Tests
- [ ] Full integration testing

## Known Issues in Original Code (to fix in port)
1. `app.ts` is dead code — skip it
2. `metrics.service.ts` uses legacy env vars — use chain-specific config
3. `adminOnly` doesn't check `isAdmin` — fix in port
4. `GET /chains` has no admin guard — add it
5. Fake analytics data in `app.controller.ts` — mark as placeholder or remove
6. No structured logging — add proper logging
7. In-memory rate limiter — consider Redis-ready design

## OpenCode Sessions Log
- **April 3, 2026 09:00** — Initial codebase analysis (completed, found 20 issues)
- **April 3, 2026 09:07** — Phase 1: scaffold (main.py, config, database, requirements) ✅
- **April 3, 2026 09:17** — Phase 2: middleware (auth, api_key, rate_limit, admin) ✅
- **April 3, 2026 09:25** — Phase 3: routes + schemas (auth, proxy, admin, apps, metrics) ✅
- **April 3, 2026 09:35** — Phase 4: Dockerfile, utils, admin split, router wiring ✅
- **April 3, 2026 09:50** — Manual fixes by Claw: bcrypt compat, route wiring, schema fixes ✅

## Bugs Fixed During Port
- passlib + bcrypt 5.x incompatibility → switched to direct bcrypt usage
- Pydantic settings rejecting env vars → added `extra="ignore"`
- Double route prefixes → removed redundant prefix from include_router
- Missing `name` field in RegisterRequest schema
- JWT_SECRET hardcoded check → use settings.jwt_secret
- Missing `@staticmethod` decorator on hash_password
- Missing deps: PyJWT, email-validator, slowapi
- Beanie 2.x + Motor 3.7 compat → pinned Beanie 1.29.0 + Motor 3.6.1

## Test Results (April 3, 2026)
- ✅ Server starts on port 3010
- ✅ POST /auth/register — creates user, returns JWT
- ✅ POST /auth/login — authenticates, returns JWT
- ✅ GET /health — returns healthy status with DB check
- ✅ GET /admin/* — correctly requires auth
- ✅ GET /docs — OpenAPI auto-docs available
