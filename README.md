# AgentGuard

**Identity + Permissions + Audit Logs control plane for AI agents.**

AgentGuard is an enterprise-grade governance layer for AI agents. It gives teams full visibility and control over what AI agents can do, enforces policies in real time, and creates a tamper-evident audit trail of every action.

## Features

### Core
- **Agent Identity** — Manage AI agents with unique IDs and scoped API keys
- **Policy Engine** — Allow/deny/require-approval rules with wildcard matching and a default-deny posture
- **Audit Logging** — Append-only, cryptographically chained logs of all agent actions
- **Python SDK** — Transparent integration; agents check in with one function call

### Security
- **JWT Authentication** — RS256 signed tokens with automatic key rotation, 1h agent / 8h admin TTL
- **Token Revocation** — Per-token JTI revocation list; `POST /token/revoke`
- **JWKS Endpoint** — `GET /.well-known/jwks.json` for third-party token verification
- **Cryptographic Audit Chain** — Per-agent SHA-256 hash chain; tamper detection via `GET /logs/verify`

### Access Control
- **RBAC** — Four roles: `super-admin > admin > auditor > approver`
- **Named Admin Users** — Registered users with hashed keys and role/team scoping
- **Team Policies** — Per-team deny/allow/approval rules that merge with agent policies
- **Conditional Rules** — Policy rules can carry `conditions: {env, time_range, day_of_week}` guards

### Workflow
- **Human-in-the-Loop (HITL)** — `require_approval` policy rules pause agent actions until a human decides
- **Webhook Notifications** — HTTP POST on `approval.created/approved/denied`; Slack-ready with HMAC signing
- **AI-Assisted Policy Creation** — Generate a starter policy from a natural-language description

### Observability
- **Compliance Reports** — Period-based dashboard: daily activity, approval funnel, top agents, top denied actions
- **Prometheus Metrics** — 10+ metrics, pre-configured alert rules
- **Health Checks** — Kubernetes-ready `/health/ready` and `/health/live` probes
- **Structured Logging** — JSON logs with correlation IDs

### Developer Experience
- **Policy Templates** — Six built-in archetypes (read-only, research, data-analyst, devops, customer-support, full-access-dev)
- **Policy Playground** — Test rules against sample actions before deploying
- **Action Normalization** — Write actions as `read:file`, `read file`, `Read File`, `read-file` — all equivalent
- **Rate Limiting** — 1 000 req/min per agent (SlowAPI)

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│  AI Agents (Python SDK)                                  │
│  agentguard.enforce() → agentguard.log_action()          │
└────────────────────┬─────────────────────────────────────┘
                     │  Bearer <JWT>  (or X-Agent-Key)
                     ▼
┌──────────────────────────────────────────────────────────┐
│  AgentGuard Backend  (FastAPI)                           │
│                                                          │
│  ┌────────────┐  ┌────────────┐  ┌────────────────────┐ │
│  │  Enforce   │  │ Approvals  │  │  Audit Logs        │ │
│  │  + Teams   │  │ + Webhooks │  │  (SHA-256 chain)   │ │
│  └────────────┘  └────────────┘  └────────────────────┘ │
│  ┌────────────┐  ┌────────────┐  ┌────────────────────┐ │
│  │  RBAC /    │  │  JWT /     │  │  Reports /         │ │
│  │  Admin     │  │  JWKS      │  │  Prometheus        │ │
│  └────────────┘  └────────────┘  └────────────────────┘ │
└──────────────────────────────────────────────────────────┘
                     ▲
                     │  Bearer <JWT>  (or X-Admin-Key)
┌────────────────────┴─────────────────────────────────────┐
│  Admin Clients / UI Dashboard (Next.js)                  │
└──────────────────────────────────────────────────────────┘
```

---

## Quick Start (5 minutes)

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Node.js 18+ (for UI)

### 1. Clone and Start

```bash
git clone https://github.com/yourorg/agentguard.git
cd agentguard

# Start all services
make up

# Run migrations
make migrate
```

Services:
- Backend API: http://localhost:8000
- UI Dashboard: http://localhost:3000
- PostgreSQL: localhost:5432

### 2. Set Admin Key

```bash
export ADMIN_API_KEY="admin-secret-key-change-in-production"
```

### 3. Run Demo

```bash
cd sdk

# Normal scenario (allow/deny/log pipeline)
python examples/demo_setup.py
python examples/demo_agent.py

# HITL scenario (approval checkpoint)
python examples/demo_setup.py --with-approval
python examples/demo_agent.py --scenario approval
# Open http://localhost:3000/approvals and click Approve or Deny
```

---

## Authentication

AgentGuard supports two auth modes — JWT (preferred) and static API key headers (legacy).

### JWT — Preferred

```bash
# Exchange a static key for a JWT
POST /token
{"agent_key": "agk_xxx"}          # → agent token (1h)
{"admin_key": "your-admin-key"}   # → admin token (8h)

# Use the token
Authorization: Bearer <jwt>
```

Token claims: `sub`, `jti`, `iat`, `exp`, `type` (`agent`|`admin`), `env`, `team`, `role` (admin only).

Revoke a token:
```bash
POST /token/revoke
Authorization: Bearer <jwt>
```

JWKS for third-party verification: `GET /.well-known/jwks.json`

### Static Key Headers — Legacy

```
X-ADMIN-KEY: <admin-key>      # admin operations
X-AGENT-KEY: <agent-api-key>  # agent operations
```

Both modes are accepted on every endpoint for backward compatibility.

---

## API Reference

### Token Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/token` | Exchange static key → JWT |
| `POST` | `/token/revoke` | Revoke a JWT by JTI |
| `GET`  | `/.well-known/jwks.json` | Public key set (RS256) |

### Agent Management

| Method | Path | Auth |
|--------|------|------|
| `POST` | `/agents` | Admin |
| `GET`  | `/agents` | Admin |
| `GET`  | `/agents/{id}` | Admin |
| `DELETE` | `/agents/{id}` | Admin |

```bash
POST /agents
{"name": "support-bot", "owner_team": "customer-success", "environment": "prod"}
# Returns: {"agent_id": "agt_abc123", "api_key": "agk_xyz789..."}  ← shown once
```

### Policy Management

| Method | Path | Description |
|--------|------|-------------|
| `PUT`  | `/agents/{id}/policy` | Set agent policy |
| `GET`  | `/agents/{id}/policy` | Get agent policy |
| `POST` | `/agents/{id}/policy/generate` | AI-generate starter policy |
| `GET`  | `/policy-templates` | List built-in templates |

**Policy rule format:**
```json
{
  "allow": [
    {"action": "read:file", "resource": "s3://docs/*"},
    {"action": "search:web", "resource": "*",
     "conditions": {"env": "prod", "time_range": {"start": "09:00", "end": "18:00"}}}
  ],
  "deny": [
    {"action": "delete:*", "resource": "*"}
  ],
  "require_approval": [
    {"action": "write:database", "resource": "users"}
  ]
}
```

**Conditions** (all AND-ed):
- `env` — matches agent environment field
- `time_range` — `{"start": "HH:MM", "end": "HH:MM"}` (UTC)
- `day_of_week` — list of day names, e.g. `["Monday", "Tuesday"]`

**Action format** — all of these are equivalent:
```
read:file  |  read file  |  Read File  |  read-file  |  read_file  |  readFile
```

### Enforcement

```bash
POST /enforce
Authorization: Bearer <agent-jwt>

{"action": "read:file", "resource": "invoice.pdf", "context": {"user_id": "u1"}}

# Response — allowed
{"allowed": true, "reason": "Matched allow rule: read:file on s3://docs/*"}

# Response — pending approval
{"allowed": false, "status": "pending", "approval_id": "ap_xxxxxxxx..."}
```

### Audit Logs

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/logs` | Submit a log entry |
| `GET`  | `/logs` | Query logs (agent\_id, action, allowed, start\_time, limit) |
| `GET`  | `/logs/verify?agent_id=xxx` | Verify per-agent SHA-256 chain |

```bash
GET /logs/verify?agent_id=agt_abc123
# Returns: {"valid": true, "total_entries": 42, "broken_at": null}
```

### Approvals (Human-in-the-Loop)

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/approvals` | List pending/all approvals |
| `GET`  | `/approvals/{id}` | Get approval status (agent polls this) |
| `POST` | `/approvals/{id}/approve` | Approve with optional reason |
| `POST` | `/approvals/{id}/deny` | Deny with optional reason |

### Admin Users & RBAC

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/admin/users` | Create named admin user |
| `GET`  | `/admin/users` | List admin users |
| `DELETE` | `/admin/users/{id}` | Delete admin user |
| `PUT`  | `/teams/{team}/policy` | Set team-level policy |
| `GET`  | `/teams/{team}/policy` | Get team policy |

Roles (highest to lowest): `super-admin (4)` › `admin (3)` › `auditor (2)` › `approver (1)`

Team policies merge with agent policies: team deny rules fire first (highest priority).

### Reports

```bash
GET /reports/summary?days=30
Authorization: Bearer <admin-jwt>

# Returns:
{
  "overview":  {"total_actions", "allowed", "denied", "allow_rate", "deny_rate"},
  "approvals": {"total", "pending", "approved", "denied", "approval_rate"},
  "top_agents": [...],
  "top_denied_actions": [...],
  "daily_breakdown": [...]
}
```

---

## Python SDK

### Installation

```bash
pip install agentguard
```

### Usage

```python
from agentguard import AgentGuardClient

# Admin client — static key auto-exchanged for JWT internally
admin = AgentGuardClient(base_url="http://localhost:8000", admin_key="your-admin-key")

# Create agent
agent = admin.create_agent(name="my-agent", owner_team="engineering", environment="prod")
agent_key = agent["api_key"]  # save this

# Set policy
admin.set_policy(
    agent_id=agent["agent_id"],
    allow=[{"action": "read:file", "resource": "*"}],
    deny=[{"action": "delete:*", "resource": "*"}],
    require_approval=[{"action": "write:database", "resource": "users"}],
)

# Agent client
client = AgentGuardClient(base_url="http://localhost:8000", agent_key=agent_key)

# Check permission + log
result = client.enforce(action="read:file", resource="invoice.pdf")
if result["allowed"]:
    client.log_action(action="read:file", resource="invoice.pdf", allowed=True, result="success")
elif result.get("status") == "pending":
    # Poll until human decides
    approval_id = result["approval_id"]
    decision = client.poll_approval(approval_id)   # blocks with spinner in demo
```

The SDK transparently exchanges static keys for JWTs on first use, caches them, and refreshes 60 s before expiry.

---

## Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://agentguard:password@localhost:5432/agentguard

# Auth
ADMIN_API_KEY=your-secret-admin-key-change-me

# JWT (auto-generated RS256 keypair if absent, warn in logs)
JWT_PRIVATE_KEY=<PEM-encoded RSA private key>

# Webhooks (optional)
WEBHOOK_URL=https://hooks.slack.com/services/T.../B.../xxx
WEBHOOK_SECRET=my-hmac-signing-secret

# Server
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000
```

UI (`.env.local`):
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Webhook Notifications

AgentGuard fires webhook events on approval lifecycle:

| Event | Trigger |
|-------|---------|
| `approval.created` | An agent action triggers a `require_approval` rule |
| `approval.approved` | A human approves the request |
| `approval.denied` | A human denies the request |

Requests are signed with `X-AgentGuard-Signature: sha256=<hmac>` when `WEBHOOK_SECRET` is set.
Slack incoming webhook URLs are auto-detected and receive formatted Slack messages.

---

## Database Schema

### Core tables
- **agents** — identity, team, environment, is_active
- **agent_keys** — key_hash (SHA256), key_prefix, is_active
- **policies** — allow_rules / deny_rules / require_approval_rules (JSONB)
- **audit_logs** — log_id (UUID), chain_hash (SHA-256), prev_log_id, action, resource, context, allowed, result

### Extended tables
- **approval_requests** — action, resource, context, status, decision_by, decision_reason
- **admin_users** — name, key_hash, role, team
- **revoked_tokens** — jti, revoked_at
- **team_policies** — team, deny_rules / allow_rules / require_approval_rules (JSONB)

---

## Production Deployment

See [PRODUCTION.md](PRODUCTION.md) | [Production Checklist](PRODUCTION_CHECKLIST.md) | [Production Features](PRODUCTION_FEATURES.md)

Key hardening steps:
- Use a secrets manager for `ADMIN_API_KEY` and `JWT_PRIVATE_KEY`
- Enable TLS/HTTPS
- Set `CORS_ORIGINS` to your actual UI origin
- Configure `WEBHOOK_SECRET` for signed notifications
- Enable database encryption at rest and backups

---

## Makefile Commands

```bash
make up          # Start all services
make down        # Stop all services
make logs        # View logs
make migrate     # Run database migrations
make rollback    # Rollback last migration
make test        # Run tests
make format      # Format code (black + ruff)
make lint        # Lint code
make clean       # Clean containers and volumes
```

---

## Project Structure

```
agentguard/
├── backend/
│   ├── app/
│   │   ├── api/          # agents, enforce, logs, policies, approvals,
│   │   │                 # tokens, admin, reports, playground
│   │   ├── models/       # SQLAlchemy models
│   │   ├── schemas/      # Pydantic schemas
│   │   └── utils/        # jwt_utils, chain, conditions, webhook
│   └── alembic/          # Migrations (001–005)
├── sdk/
│   ├── agentguard/       # Python SDK
│   └── examples/         # demo_agent.py, demo_setup.py
└── ui/
    └── src/app/          # agents, policies, logs, approvals,
                          # reports, playground, admin
```

---

## Roadmap

- [x] Agent identity management
- [x] Policy engine (allow/deny + wildcard)
- [x] Audit logging
- [x] Python SDK
- [x] Rate limiting + Prometheus metrics
- [x] Human-in-the-Loop approval checkpoints
- [x] AI-assisted policy generation
- [x] JWT authentication (RS256) + token revocation + JWKS
- [x] Cryptographic audit log chaining + tamper verification
- [x] Conditional policy rules (env / time / day-of-week)
- [x] RBAC (super-admin / admin / auditor / approver)
- [x] Team policies with merge semantics
- [x] Webhook / Slack notifications
- [x] Policy templates
- [x] Compliance reports dashboard
- [x] Policy playground
- [ ] Go / JavaScript SDKs
- [ ] Log retention policies
- [ ] Terraform provider
- [ ] SSO / SAML integration

---

## Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/amazing`)
3. Run tests (`make test`)
4. Format code (`make format`)
5. Commit and open a Pull Request

---

## License

MIT License — see LICENSE file

---

## Support

- Issues: https://github.com/yourorg/agentguard/issues
- Docs: https://docs.agentguard.dev
- Email: support@agentguard.dev

---

**Built for enterprises who need AI agent governance. Simple. Secure. Scalable.**
