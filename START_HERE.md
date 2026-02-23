# 🚀 AgentGuard - Quick Start

Choose your setup method:

## Option 1: Local Development (No Docker) ⭐ RECOMMENDED

**Best for:** Quick start, Windows users, development

```powershell
.\start-local.ps1
```

That's it! This will:
- ✅ Install all dependencies
- ✅ Setup SQLite database
- ✅ Start backend at http://localhost:8000
- ✅ Start UI at http://localhost:3000
- ✅ Install SDK

**Prerequisites:**
- Python 3.11+
- Node.js 18+ (optional, for UI)

See [LOCAL_SETUP.md](LOCAL_SETUP.md) for details.

---

## Option 2: Docker Compose

**Best for:** Production-like environment, team collaboration

```powershell
docker compose up -d
docker compose exec backend alembic upgrade head
```

**Prerequisites:**
- Docker Desktop

See [README.md](README.md) for details.

---

## What's Next?

### 1. Verify Services

Backend: http://localhost:8000
API Docs: http://localhost:8000/docs
UI Dashboard: http://localhost:3000

### 2. Run the Demo

```powershell
cd sdk
pip install -e .
python examples\quickstart.py
```

### 3. View Logs

Open http://localhost:3000 to see audit logs in the UI!

### 4. Integrate with Your AI Agents

```python
from agentguard import AgentGuardClient

client = AgentGuardClient(
    base_url="http://localhost:8000",
    agent_key="your-agent-key"
)

# Check permissions (supports natural language!)
result = client.enforce(action="read file", resource="data.txt")
if result['allowed']:
    # Do the thing
    client.log_action(action="read file", allowed=True, result="success")
```

---

## Troubleshooting

### Local Setup Issues

**"Python not found"**
→ Install Python 3.11+ from https://www.python.org/downloads/

**"Backend won't start"**
```powershell
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app
```

**"Port already in use"**
→ Change PORT in `.env` file or stop the conflicting service

### Docker Issues

**"docker compose not found"**
→ Install Docker Desktop from https://www.docker.com/products/docker-desktop

**"Containers won't start"**
→ Make sure Docker Desktop is running

---

## Documentation

- 📖 [README.md](README.md) - Full documentation
- 💻 [LOCAL_SETUP.md](LOCAL_SETUP.md) - Local setup guide
- 🪟 [WINDOWS.md](WINDOWS.md) - Windows-specific guide
- 🐍 [sdk/README.md](sdk/README.md) - Python SDK docs

---

## Support

- Issues: https://github.com/yourorg/agentguard/issues
- Docs: See README.md files

---

**Happy building! 🎉**
