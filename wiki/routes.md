# API Routes

Base URL: `http://localhost:8888`

Authenticated routes require `Authorization: Bearer <token>` unless noted.

---

## Auth

### POST /auth/register
```json
// Request
{ "email": "user@example.com", "password": "secret123" }

// Response 201
{ "success": true, "data": { "token": "...", "user": { "id": "...", "email": "...", "isAdmin": false } } }
```

### POST /auth/login
```json
// Request
{ "email": "user@example.com", "password": "secret123" }

// Response 200
{ "success": true, "data": { "token": "...", "user": { "id": "...", "email": "...", "isAdmin": false } } }
```

### GET /auth/account
```json
// Response 200
{ "success": true, "data": { "user": { "id": "...", "email": "...", "isActive": true } } }
```

### PATCH /auth/update-email
```json
// Request
{ "email": "new@example.com", "password": "current_password" }
```

### PATCH /auth/update-password
```json
// Request
{ "currentPassword": "old", "newPassword": "new123" }
```

### GET /auth/export
Returns all apps belonging to the authenticated user for data export.

---

## Apps

### GET /apps
```
?page=1&limit=10
```
```json
// Response 200
{
  "success": true,
  "data": {
    "apps": [ { "_id": "...", "name": "...", "chainName": "Sepolia", "isActive": true } ],
    "pagination": { "currentPage": 1, "totalPages": 1, "totalApps": 2 }
  }
}
```

### POST /apps
```json
// Request
{ "name": "My App", "chainName": "Sepolia", "chainId": "11155111", "description": "" }

// Response 201
{ "success": true, "message": "App created successfully.", "data": { "_id": "...", "apiKey": "...", "createdAt": "2026-04-03T14:47:38.602Z" } }
```

### GET /apps/{id}
Returns the app including its `apiKey`.

### PATCH /apps/{id}
```json
// Request (all fields optional)
{ "name": "New Name", "description": "Updated desc" }
```

### DELETE /apps/{id}
```json
// Response 200
{ "success": true, "message": "App deleted successfully." }
```

### POST /apps/{id}/regenerate-key
```json
// Response 200
{ "success": true, "message": "API key regenerated successfully.", "data": "new-uuid-key" }
```

### GET /apps/{id}/usage
```json
// Response 200
{
  "success": true,
  "data": {
    "analytics": {
      "app": { "id": "...", "name": "...", "chainName": "Sepolia" },
      "usage": { "totalRequests": 500, "dailyRequests": 12, "dailyLimit": 1000000, "usagePercentage": 0, "maxRps": 200, "lastResetDate": null },
      "hourlyBreakdown": [ { "hour": 0, "requests": 0 } ]
    }
  }
}
```

### GET /apps/dashboard/stats
```json
// Response 200
{ "success": true, "data": { "stats": { "totalApps": 2, "activeApps": 2, "totalRequests": 500, "todaysRequests": 12, "maxApps": 5 } } }
```

### GET /apps/usage/all
Aggregated usage across all of the authenticated user's apps.

---

## Proxy

No `Authorization` header required — authentication is via the API key in the URL path.

### Execution Layer (JSON-RPC)

```
POST /{chain}/exec/{api_key}
POST /{chain}/exec/{api_key}/{path}
```

```bash
curl -X POST https://gateway/sepolia/exec/YOUR_KEY \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'

# Response
{"jsonrpc":"2.0","id":1,"result":"0xa17919"}
```

### Consensus Layer (Beacon API)

```
GET /{chain}/cons/{api_key}/{path}
```

```bash
curl https://gateway/sepolia/cons/YOUR_KEY/eth/v1/node/syncing

# Response
{"data":{"head_slot":"9957952","sync_distance":"0","is_syncing":false}}
```

Supports all HTTP methods. The full path after `{api_key}` is forwarded to the upstream node.

**Error responses:**
- `403` — invalid/inactive API key, or key used on wrong chain
- `429` — rate limit (RPS) or daily quota exceeded
- `502` — upstream node unreachable

---

## Admin

All routes require a Bearer token from an admin account.

### Users

| Method | Path | Description |
|---|---|---|
| GET | `/admin/users?page=1&limit=10` | List all users |
| PATCH | `/admin/users/{id}` | Update user (`email`, `password`, `isActive`) |

### Apps

| Method | Path | Description |
|---|---|---|
| GET | `/admin/apps?page=1&limit=10&userId=...` | List all apps |
| GET | `/admin/apps/{id}` | Get app details |
| PATCH | `/admin/apps/{id}` | Update app fields |
| PUT | `/admin/apps/{id}/limits` | Update `maxRps` / `dailyRequestsLimit` |

```bash
# Update limits
curl -X PUT http://localhost:8888/admin/apps/APP_ID/limits \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"maxRps": 500, "dailyRequestsLimit": 5000000}'
```

### Chains

| Method | Path | Description |
|---|---|---|
| GET | `/admin/chains` | List all chains in DB |
| POST | `/admin/chains` | Add a chain |
| PATCH | `/admin/chains/{chain_id}` | Update a chain |
| DELETE | `/admin/chains/{chain_id}` | Remove a chain |

Note: chain RPC URLs are configured via environment variables, not through these endpoints. The chain DB entries are for metadata/enable-disable only.

### Node Health

```
GET /admin/node-health/{chain}
```
```json
{
  "success": true,
  "data": {
    "chain": "sepolia",
    "execution": { "status": "healthy", "syncing": false },
    "consensus": { "status": "healthy", "syncing": false, "head_slot": 9957952 }
  }
}
```

### Default App Settings

| Method | Path | Description |
|---|---|---|
| GET | `/admin/settings` | Get default `maxRps` / `dailyRequestsLimit` for new apps |
| PATCH | `/admin/settings` | Update defaults |

---

## System

### GET /health
```json
{ "status": "healthy", "services": { "database": { "status": "healthy" }, "memory_mb": 80.6 } }
```

### GET /health/{chain}
Checks proxy connectivity to a chain's execution and consensus nodes.

### GET /metrics
Prometheus metrics in text format.

### GET /
```json
{ "name": "NodeBridge RPC Gateway", "version": "1.0.0" }
```
