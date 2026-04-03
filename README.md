# NodeBridge RPC Gateway

A multi-tenant RPC gateway that provides controlled, authenticated access to private Ethereum node infrastructure. Users create apps and get API keys that proxy through to your execution and consensus layer nodes, with per-app rate limiting and daily request quotas.

**Stack:** Python · FastAPI · MongoDB (Beanie ODM) · httpx

---

## Quick Start

```bash
git clone <repo>
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your values
uvicorn fastapi_app.main:app --host 0.0.0.0 --port 8888
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `MONGO_URI` | Yes | MongoDB connection string |
| `JWT_SECRET` | Yes | Secret for signing JWTs (min 32 chars) |
| `DEFAULT_MAX_RPS` | No | Default RPS limit per app (default: 200) |
| `DEFAULT_DAILY_REQUESTS` | No | Default daily request limit (default: 1,000,000) |

### Chain Configuration

Chains are discovered automatically from environment variables. Define any number of chains using this pattern:

```
{CHAIN}_EXECUTION_RPC_URL=http://...
{CHAIN}_CONSENSUS_API_URL=http://...
{CHAIN}_PROMETHEUS_URL=http://...   # optional
```

Examples:
```env
SEPOLIA_EXECUTION_RPC_URL=http://172.33.0.9:8545
SEPOLIA_CONSENSUS_API_URL=http://172.33.0.20:3500
ETHEREUM_EXECUTION_RPC_URL=http://192.168.1.10:8545,http://192.168.1.11:8545
ETHEREUM_CONSENSUS_API_URL=http://192.168.1.10:5052
```

The prefix (lowercased) becomes the chain identifier in API paths: `sepolia`, `ethereum`, etc. Multiple URLs per chain are load-balanced randomly.

---

## Running with PM2

```bash
pm2 start start.sh --name fastapi-backend --cwd /path/to/backend
pm2 save
```

`start.sh` runs uvicorn with 4 workers by default. Adjust `--workers` to match your CPU count.

---

## API Overview

Full route reference: [wiki/routes.md](wiki/routes.md)

### Proxy (no auth header needed — API key is in the URL)

```bash
# Execution layer (JSON-RPC)
POST /{chain}/exec/{api_key}
POST /{chain}/exec/{api_key}/{path}

# Consensus layer (Beacon API)
GET  /{chain}/cons/{api_key}/eth/v1/node/syncing
GET  /{chain}/cons/{api_key}/{path}
```

Example:
```bash
curl -X POST https://your-gateway/sepolia/exec/YOUR_API_KEY \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
```

### Auth

```
POST  /auth/register
POST  /auth/login
GET   /auth/account          # requires Bearer token
GET   /auth/export           # export all app data
PATCH /auth/update-email
PATCH /auth/update-password
```

### Apps (requires Bearer token)

```
GET    /apps                     # list apps (paginated)
POST   /apps                     # create app
GET    /apps/dashboard/stats
GET    /apps/{id}
PATCH  /apps/{id}
DELETE /apps/{id}
POST   /apps/{id}/regenerate-key
GET    /apps/{id}/usage
GET    /apps/usage/all
```

### Admin (requires admin Bearer token)

```
GET    /admin/users
PATCH  /admin/users/{id}
GET    /admin/apps
GET    /admin/apps/{id}
PATCH  /admin/apps/{id}
PUT    /admin/apps/{id}/limits
GET    /admin/chains
POST   /admin/chains
PATCH  /admin/chains/{chain_id}
DELETE /admin/chains/{chain_id}
GET    /admin/node-health/{chain}
GET    /admin/settings
PATCH  /admin/settings
```

### System

```
GET /          # gateway info
GET /health    # health check (DB connectivity)
GET /health/{chain}   # proxy health for a chain
GET /metrics   # Prometheus metrics
```
