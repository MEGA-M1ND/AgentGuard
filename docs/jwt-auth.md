# JWT Authentication & Token Revocation

## What it does

AgentGuard replaces static API keys with asymmetric JWT tokens (RS256). Every agent and admin
receives a short-lived, cryptographically signed token instead of a permanent secret. Tokens
carry embedded identity claims, expire automatically, and can be individually revoked at any
time — even before expiry.

**Why this matters for security buyers:**
- A stolen static key is valid forever. A stolen JWT is valid for at most 1 hour.
- Revocation takes effect on the next request — no key rotation lag.
- The RSA public key is published at `/.well-known/jwks.json` so any service can verify
  tokens independently without calling AgentGuard.
- Every token has a unique `jti` claim that creates an audit trail of which token performed
  which action.

---

## Components

### 1. Keypair (`backend/app/utils/jwt_utils.py`)

AgentGuard uses an **RSA-2048 keypair** (RS256 algorithm):

- The **private key** signs tokens. Never leaves the server.
- The **public key** verifies tokens. Published openly at `/.well-known/jwks.json`.

On startup, AgentGuard loads `JWT_PRIVATE_KEY` from the environment. If it is not set, a
keypair is auto-generated for that session and the private key PEM is printed to the logs so
the operator can persist it.

```
JWT_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEA...
-----END RSA PRIVATE KEY-----"
```

Setting `JWT_PRIVATE_KEY` is required in production — without it, all tokens are invalidated
on every server restart.

---

### 2. Token structure

Every JWT has three parts: `header.payload.signature`

**Header**
```json
{ "alg": "RS256", "typ": "JWT" }
```

**Payload — Agent token** (expires in 1 hour)
```json
{
  "sub": "agt_xxxxxxxxxxxx",
  "jti": "662a450a-af0b-493a-bc13-e77d21d493f3",
  "iat": 1771834409,
  "exp": 1771838009,
  "type": "agent",
  "env": "production",
  "team": "platform"
}
```

**Payload — Admin token** (expires in 8 hours)
```json
{
  "sub": "admin",
  "jti": "8da4c7a0-ebec-4779-b2c0-cf196d8c37a1",
  "iat": 1771833707,
  "exp": 1771862507,
  "type": "admin"
}
```

| Claim | Meaning |
|-------|---------|
| `sub` | Who the token belongs to — agent ID or `"admin"` |
| `jti` | Unique token ID — used for revocation lookup |
| `iat` | Issued at (Unix timestamp) |
| `exp` | Expires at (Unix timestamp) — enforced automatically |
| `type` | `"agent"` or `"admin"` — controls which endpoints are accessible |
| `env` | Agent's environment (`production`, `staging`, `development`) |
| `team` | Agent's owner team — used for future RBAC scoping |

**Signature** — RS256 HMAC of the encoded header + payload, signed with the private key.
Tamper with any claim and the signature check fails.

---

### 3. Token issuance (`POST /token`)

Accepts a static credential and returns a signed JWT.

```
POST /token
Content-Type: application/json

{ "agent_key": "agk_Qi9-RiHoxI7rSz..." }
      OR
{ "admin_key": "admin123" }
```

Response:
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

The static `agk_` key is only ever sent to `/token`. All other API calls use the JWT.

---

### 4. Token verification (`backend/app/api/deps.py`)

Every protected endpoint runs three checks in order:

1. **Signature** — verify the RS256 signature against the public key. Rejects tampered tokens.
2. **Expiry** — reject if `exp` is in the past. Handled by `python-jose`.
3. **Revocation** — query the `revoked_tokens` table for the token's `jti`. Rejects revoked tokens.

**Dual-mode auth** — both `Authorization: Bearer <JWT>` and legacy `X-Admin-Key`/`X-Agent-Key`
headers are accepted. The Bearer path is checked first. This means the existing UI and any
integrations using the old headers continue to work without changes.

---

### 5. Token revocation (`POST /token/revoke`)

```
POST /token/revoke
Authorization: Bearer eyJhbGciOiJSUzI1NiJ9...
```

Response:
```json
{ "revoked": true }
```

The token's `jti` is inserted into the `revoked_tokens` table along with the token's original
`expires_at`. On every subsequent request, the `jti` lookup returns a hit and the request is
rejected with `401 Token has been revoked`.

The `expires_at` column enables periodic cleanup — rows can be safely deleted once the token
would have expired naturally anyway.

---

### 6. JWKS endpoint (`GET /.well-known/jwks.json`)

```
GET /.well-known/jwks.json
(no authentication required)
```

Response:
```json
{
  "keys": [
    {
      "kty": "RSA",
      "use": "sig",
      "alg": "RS256",
      "n": "6VVWh9hFY_84edAaHOeXSls...",
      "e": "AQAB"
    }
  ]
}
```

`n` is the RSA modulus and `e` is the public exponent, both base64url-encoded. Any service
that receives an AgentGuard JWT can fetch this endpoint once, cache the key, and verify tokens
independently — without making any other call to AgentGuard. This is the standard OAuth2 /
OpenID Connect pattern for federated token verification.

---

### 7. SDK transparent exchange (`sdk/agentguard/client.py`)

The Python SDK handles the entire auth flow invisibly:

```python
client = AgentGuardClient(
    base_url="http://localhost:8000",
    agent_key="agk_Qi9-RiHoxI7rSz..."
)

# This call automatically exchanges the agent_key for a JWT first
result = client.enforce("read:file", resource="report.pdf")
```

Internally:
1. On the first call, `_ensure_token()` calls `POST /token` with the static key.
2. The JWT and its expiry are cached in memory.
3. Subsequent calls reuse the cached JWT.
4. 60 seconds before expiry, the SDK fetches a fresh token automatically.
5. The static key is never sent to any endpoint other than `/token`.

To explicitly revoke the current token:
```python
client.revoke_token(auth_type="agent")   # or "admin"
```

---

### 8. Database table (`revoked_tokens`)

```sql
CREATE TABLE revoked_tokens (
    id         INTEGER PRIMARY KEY,
    jti        VARCHAR(36) UNIQUE NOT NULL,   -- the token's jti claim
    revoked_at DATETIME NOT NULL,             -- when it was revoked
    expires_at DATETIME NOT NULL              -- original token expiry (for cleanup)
);
CREATE UNIQUE INDEX ix_revoked_tokens_jti       ON revoked_tokens (jti);
CREATE        INDEX ix_revoked_tokens_expires_at ON revoked_tokens (expires_at);
```

Created by Alembic migration `003_add_jwt_revocation`.

---

## Configuration reference

Add to `backend/.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `JWT_PRIVATE_KEY` | *(auto-generated)* | RSA-2048 private key PEM. Set this in production or tokens are lost on restart. |
| `JWT_ALGORITHM` | `RS256` | Signing algorithm. `RS256` (RSA) or `ES256` (ECDSA). |
| `JWT_AGENT_EXPIRE_SECONDS` | `3600` | Agent token lifetime in seconds (1 hour). |
| `JWT_ADMIN_EXPIRE_SECONDS` | `28800` | Admin token lifetime in seconds (8 hours). |
| `JWT_KEY_ID` | *(none)* | Optional `kid` claim added to tokens and JWKS. Useful for key rotation — run two keys simultaneously with different `kid` values. |

---

## Demo script

### Prerequisites

```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

---

### Step 1 — Get an admin JWT

```bash
curl -s -X POST http://localhost:8000/token \
  -H "Content-Type: application/json" \
  -d '{"admin_key": "admin123"}'
```

Expected response:
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 28800
}
```

Save the token:
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/token \
  -H "Content-Type: application/json" \
  -d '{"admin_key": "admin123"}' | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

---

### Step 2 — Decode the token (show claims)

```bash
echo $TOKEN | python -c "
import sys, base64, json, datetime
token = sys.stdin.read().strip()
payload_b64 = token.split('.')[1]
payload_b64 += '=' * (4 - len(payload_b64) % 4)
payload = json.loads(base64.urlsafe_b64decode(payload_b64))
payload['exp_human'] = datetime.datetime.fromtimestamp(payload['exp']).isoformat()
print(json.dumps(payload, indent=2))
"
```

Point out: `sub`, `jti`, `type`, and the human-readable expiry.

---

### Step 3 — Use the JWT on a protected endpoint

```bash
curl -s http://localhost:8000/agents \
  -H "Authorization: Bearer $TOKEN"
```

Expected: list of agents. The `X-Admin-Key` header is not sent — this is a pure JWT call.

---

### Step 4 — Show that a tampered token is rejected

```bash
curl -s http://localhost:8000/agents \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJhZG1pbiIsInR5cGUiOiJhZG1pbiJ9.FAKESIGNATURE"
```

Expected:
```json
{ "detail": "Invalid or expired token" }
```

---

### Step 5 — Show that an agent token cannot hit admin endpoints

```bash
# Create an agent and get its key
AGENT_KEY=$(curl -s -X POST http://localhost:8000/agents \
  -H "X-Admin-Key: admin123" \
  -H "Content-Type: application/json" \
  -d '{"name":"DemoAgent","owner_team":"platform","environment":"production"}' \
  | python -c "import sys,json; print(json.load(sys.stdin)['api_key'])")

# Exchange for agent JWT
AGENT_TOKEN=$(curl -s -X POST http://localhost:8000/token \
  -H "Content-Type: application/json" \
  -d "{\"agent_key\": \"$AGENT_KEY\"}" \
  | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Agent JWT on an admin-only endpoint
curl -s http://localhost:8000/agents \
  -H "Authorization: Bearer $AGENT_TOKEN"
```

Expected:
```json
{ "detail": "Admin token required" }
```

---

### Step 6 — Revoke the admin token

```bash
# Revoke it
curl -s -X POST http://localhost:8000/token/revoke \
  -H "Authorization: Bearer $TOKEN"
```

Expected:
```json
{ "revoked": true }
```

```bash
# Same token is now dead
curl -s http://localhost:8000/agents \
  -H "Authorization: Bearer $TOKEN"
```

Expected:
```json
{ "detail": "Token has been revoked" }
```

---

### Step 7 — Show the JWKS public key

```bash
curl -s http://localhost:8000/.well-known/jwks.json
```

Point out: this endpoint requires no authentication. Any downstream service — a Lambda, a
sidecar, a third-party audit tool — can fetch this key and verify AgentGuard tokens without
calling AgentGuard again.

---

### Step 8 — Legacy headers still work (backward compat)

```bash
curl -s http://localhost:8000/agents \
  -H "X-Admin-Key: admin123" \
  | python -c "import sys,json; d=json.load(sys.stdin); print(f'Got {len(d)} agents via legacy header')"
```

Point out: the existing UI and old SDK calls continue to work. JWT is opt-in, not a forced
migration.

---

## Security properties summary

| Property | How it is achieved |
|----------|--------------------|
| Tamper-proof identity | RS256 signature — modifying any claim breaks the signature |
| Short-lived access | `exp` claim enforced on every request — 1h agents, 8h admins |
| Immediate revocation | `jti` blocklist in `revoked_tokens` table, checked on every request |
| No credential exposure | Static key only sent to `/token`; all other calls use Bearer JWT |
| Federation-ready | JWKS endpoint allows third-party verification without trusting AgentGuard |
| Role separation | `type` claim gates access — agent tokens cannot reach admin endpoints |
| Audit trail | Each `jti` is unique — links every API call to a specific issued token |
| Backward compatible | Legacy `X-Admin-Key`/`X-Agent-Key` headers still accepted alongside Bearer |
