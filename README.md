# AgentGuard

**Identity + Permissions + Audit Logs control plane for AI agents.**

AgentGuard provides enterprises with visibility and control over AI agent actions through:
- **Agent Identity**: Manage AI agents with unique identities and API keys
- **Permission Scopes**: Define allow/deny policies for agent actions
- **Audit Logs**: Append-only tamper-evident logs of all agent activities
- **Dashboard**: Minimal UI to view and filter audit logs
- **Python SDK**: Easy integration for your AI agents

## 🚀 Production-Ready Features

AgentGuard is **production-ready** with enterprise-grade capabilities:
- ⚡ **Rate Limiting** - Protect against abuse (1000 req/min per agent)
- 📊 **Prometheus Metrics** - Full observability with 10+ metrics
- 🏥 **Health Checks** - Kubernetes-ready probes (`/health/ready`, `/health/live`)
- 📝 **Structured Logging** - JSON logs with correlation IDs
- 🔌 **Connection Pooling** - Efficient database resource management
- 🚨 **Alerting Rules** - Pre-configured Prometheus alerts
- 🔐 **Security Hardening** - Rate limits, error handling, secrets management

**📖 Deploy to Production**: See [PRODUCTION.md](PRODUCTION.md) | [Production Checklist](PRODUCTION_CHECKLIST.md) | [Production Features](PRODUCTION_FEATURES.md)

---

## Architecture Overview

```
┌─────────────┐
│  AI Agent   │
│  (w/ SDK)   │
└──────┬──────┘
       │ X-AGENT-KEY
       ▼
┌─────────────────────────────────┐
│      AgentGuard Backend         │
│  ┌──────────┐  ┌─────────────┐ │
│  │  Enforce │  │ Audit Logs  │ │
│  │  Policy  │  │  (append)   │ │
│  └──────────┘  └─────────────┘ │
└─────────────────────────────────┘
       ▲
       │
┌──────┴──────┐
│ Admin APIs  │ (X-ADMIN-KEY)
└─────────────┘
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

# Check status
make ps
```

Services will be available at:
- Backend API: http://localhost:8000
- UI Dashboard: http://localhost:3000
- PostgreSQL: localhost:5432

### 2. Set Admin Key

```bash
export ADMIN_API_KEY="admin-secret-key-change-in-production"
```

### 3. Run Quickstart Demo

```bash
cd sdk
pip install -e .
python examples/quickstart.py
```

This will:
1. Create an agent
2. Set a policy (allow `read:file`, deny `delete:*`)
3. Test enforcement
4. Submit audit logs
5. Query logs

### 4. View in Dashboard

Open http://localhost:3000 to see audit logs with filters.

---

## Authentication

AgentGuard uses two authentication levels:

### Admin Authentication
Used for management operations (create agents, set policies)
```
X-ADMIN-KEY: <your-admin-key>
```

Set via environment variable:
```bash
ADMIN_API_KEY=your-secret-admin-key
```

### Agent Authentication
Used by agents for enforcement and log submission
```
X-AGENT-KEY: <agent-api-key>
```

API keys are:
- Generated automatically when creating an agent
- Stored hashed (SHA256) in database
- Never logged in plaintext

---

## API Reference

### Agent Management (Admin)

#### Create Agent
```bash
POST /agents
X-ADMIN-KEY: <admin-key>

{
  "name": "support-bot",
  "owner_team": "customer-success",
  "environment": "prod"
}

Response:
{
  "agent_id": "agt_abc123",
  "api_key": "agk_xyz789..."  # Only shown once!
}
```

#### List Agents
```bash
GET /agents
X-ADMIN-KEY: <admin-key>
```

#### Get Agent
```bash
GET /agents/{agent_id}
X-ADMIN-KEY: <admin-key>
```

#### Delete Agent
```bash
DELETE /agents/{agent_id}
X-ADMIN-KEY: <admin-key>
```

### Policy Management (Admin)

#### Set Policy
```bash
PUT /agents/{agent_id}/policy
X-ADMIN-KEY: <admin-key>

{
  "allow": [
    {"action": "read:file", "resource": "s3://docs/*"},
    {"action": "call:internal_api", "resource": "api.internal.com/v1/*"}
  ],
  "deny": [
    {"action": "delete:*", "resource": "*"},
    {"action": "send:external_email", "resource": "*"}
  ]
}
```

#### Action Format - Type Naturally! ✨

AgentGuard intelligently parses action patterns, so you can type them in any format you prefer. All of these work the same:

| Format | Example | Description |
|--------|---------|-------------|
| **Standard** | `read:file` | Traditional verb:noun pattern |
| **Natural** | `read file` | Space-separated (easiest!) |
| **Capitalized** | `Read File` | Natural with capitals |
| **Hyphenated** | `read-file` | Kebab-case |
| **Snake case** | `read_file` | Underscore-separated |
| **CamelCase** | `readFile` | No spaces |

**Real Examples:**
```json
{
  "allow": [
    {"action": "read file", "resource": "*.txt"},
    {"action": "Send Email", "resource": "*"},
    {"action": "query database", "resource": "users_table"},
    {"action": "delete *", "resource": "temp/*"}
  ]
}
```

All actions are automatically normalized to lowercase `verb:noun` format internally (e.g., `"Read File"` → `"read:file"`).

**Wildcards:**
- `read:*` or `read *` - Matches any read action
- `*:file` or `* file` - Matches any action on files
- `*` - Matches everything (use with caution!)

#### Get Policy
```bash
GET /agents/{agent_id}/policy
X-ADMIN-KEY: <admin-key>
```

### Enforcement (Agent)

#### Check Permission
```bash
POST /enforce
X-AGENT-KEY: <agent-key>

{
  "action": "read:file",
  "resource": "s3://docs/invoice.pdf",
  "context": {"user_id": "usr_123"}
}

Response:
{
  "allowed": true,
  "reason": "Matched allow rule: read:file on s3://docs/*"
}
```

### Audit Logs (Agent)

#### Submit Log
```bash
POST /logs
X-AGENT-KEY: <agent-key>

{
  "action": "read:file",
  "resource": "s3://docs/invoice.pdf",
  "context": {"user_id": "usr_123"},
  "allowed": true,
  "result": "success",
  "metadata": {"bytes_read": 1024}
}
```

#### Query Logs
```bash
GET /logs?agent_id=agt_abc123&action=read:file&allowed=true&start_time=2024-01-01T00:00:00Z&limit=100
X-AGENT-KEY: <agent-key> or X-ADMIN-KEY: <admin-key>
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

# Admin client
admin = AgentGuardClient(
    base_url="http://localhost:8000",
    admin_key="your-admin-key"
)

# Create agent
agent = admin.create_agent(
    name="my-agent",
    owner_team="engineering",
    environment="prod"
)
print(f"Agent ID: {agent['agent_id']}")
print(f"API Key: {agent['api_key']}")  # Save this!

# Set policy
admin.set_policy(
    agent_id=agent['agent_id'],
    allow=[
        {"action": "read:file", "resource": "*"}
    ],
    deny=[
        {"action": "delete:*", "resource": "*"}
    ]
)

# Agent client
client = AgentGuardClient(
    base_url="http://localhost:8000",
    agent_key=agent['api_key']
)

# Check permission
result = client.enforce(
    action="read:file",
    resource="invoice.pdf"
)
if result['allowed']:
    # Perform action
    client.log_action(
        action="read:file",
        resource="invoice.pdf",
        allowed=True,
        result="success"
    )
```

---

## Development

### Setup Local Environment

```bash
# Install backend dependencies
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Install SDK for development
cd ../sdk
pip install -e .

# Install UI dependencies
cd ../ui
npm install
```

### Run Tests

```bash
# Backend tests
make test

# Or directly
cd backend
pytest -v
```

### Database Migrations

```bash
# Create new migration
make migration MSG="add_new_field"

# Apply migrations
make migrate

# Rollback
make rollback
```

### Code Quality

```bash
# Format code
make format

# Lint
make lint
```

---

## Configuration

### Environment Variables

Backend (`.env` or docker-compose):
```bash
# Database
DATABASE_URL=postgresql://agentguard:password@localhost:5432/agentguard

# Auth
ADMIN_API_KEY=your-secret-admin-key-change-me

# Server
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO

# CORS (for UI dev)
CORS_ORIGINS=http://localhost:3000
```

UI (`.env.local`):
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Database Schema

### agents
- `id` (PK)
- `agent_id` (unique, indexed, e.g., "agt_abc123")
- `name`
- `owner_team`
- `environment` (dev/stage/prod)
- `is_active`
- `created_at`
- `updated_at`

### agent_keys
- `id` (PK)
- `agent_id` (FK → agents)
- `key_hash` (SHA256 hash)
- `key_prefix` (first 8 chars for identification)
- `is_active`
- `created_at`

### policies
- `id` (PK)
- `agent_id` (FK → agents, unique)
- `allow_rules` (JSONB)
- `deny_rules` (JSONB)
- `created_at`
- `updated_at`

### audit_logs
- `id` (PK)
- `log_id` (UUID, unique, indexed)
- `agent_id` (indexed)
- `timestamp` (indexed)
- `action` (indexed)
- `resource`
- `context` (JSONB)
- `allowed` (boolean, indexed)
- `result` (success/error)
- `metadata` (JSONB)
- `request_id` (UUID)

---

## MVP Threat Model Notes

**What This MVP Protects Against:**
- Unauthorized agent actions (via policy enforcement)
- Visibility gaps (comprehensive audit logs)
- API key theft detection (via audit patterns)

**What This MVP Does NOT Protect Against (Future Work):**
- API key brute force (no rate limiting yet)
- Database tampering (no cryptographic log verification)
- Replay attacks (no timestamp validation)
- Advanced RBAC (single admin role only)

**Production Hardening Required:**
- Use secrets manager for ADMIN_API_KEY
- Enable TLS/HTTPS
- Add rate limiting
- Implement log signature verification
- Add backup and retention policies
- Enable database encryption at rest

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
├── backend/          # FastAPI backend
│   ├── app/
│   │   ├── api/      # API routes
│   │   ├── models/   # SQLAlchemy models
│   │   ├── schemas/  # Pydantic schemas
│   │   └── utils/    # Auth, logging utilities
│   ├── alembic/      # Database migrations
│   └── tests/        # Pytest tests
├── sdk/              # Python SDK
│   ├── agentguard/
│   └── examples/
└── ui/               # Next.js dashboard
    └── src/
```

---

## Roadmap (Post-MVP)

- [ ] JWT authentication
- [ ] Rate limiting
- [ ] Webhook notifications
- [ ] Policy templates
- [ ] Advanced RBAC (teams, roles)
- [ ] Log retention policies
- [ ] Analytics dashboard
- [ ] Go/JS SDKs
- [ ] Terraform provider

---

## Contributing

1. Fork the repo
2. Create feature branch (`git checkout -b feature/amazing`)
3. Run tests (`make test`)
4. Format code (`make format`)
5. Commit (`git commit -m 'Add amazing feature'`)
6. Push (`git push origin feature/amazing`)
7. Open Pull Request

---

## License

MIT License - see LICENSE file

---

## Support

- Issues: https://github.com/yourorg/agentguard/issues
- Docs: https://docs.agentguard.dev (TODO)
- Email: support@agentguard.dev

---

**Built for enterprises who need AI agent governance. Simple. Secure. Scalable.**
