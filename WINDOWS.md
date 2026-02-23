# AgentGuard - Windows Setup Guide

This guide is specifically for Windows users running AgentGuard.

## Prerequisites

1. **Docker Desktop for Windows**
   - Download from: https://www.docker.com/products/docker-desktop
   - Make sure it's running before proceeding
   - Docker Desktop includes Docker Compose V2

2. **Python 3.11+**
   - Download from: https://www.python.org/downloads/
   - Make sure to check "Add Python to PATH" during installation

3. **Git for Windows** (optional, for cloning)
   - Download from: https://git-scm.com/download/win

## Quick Start (Windows)

### Option 1: Using PowerShell Script (Recommended)

```powershell
# 1. Open PowerShell in the agentguard directory
cd "d:\VSCode projects\AgentGuard"

# 2. Start all services
.\agentguard.ps1 up

# 3. Run database migrations (wait a few seconds for services to start)
.\agentguard.ps1 migrate

# 4. Install SDK
.\agentguard.ps1 install-sdk

# 5. Run demo
.\agentguard.ps1 demo

# 6. View help
.\agentguard.ps1 help
```

### Option 2: Using Batch File (CMD)

```cmd
# 1. Open Command Prompt in the agentguard directory
cd "d:\VSCode projects\AgentGuard"

# 2. Start all services
agentguard.bat up

# 3. Run database migrations
agentguard.bat migrate

# 4. Install SDK
agentguard.bat install-sdk

# 5. Run demo
agentguard.bat demo
```

### Option 3: Using Docker Compose Directly

```powershell
# Start services
docker compose up -d

# Run migrations
docker compose exec backend alembic upgrade head

# Install SDK
cd sdk
pip install -e .

# Run demo
python examples\quickstart.py

# View logs
docker compose logs -f

# Stop services
docker compose down
```

### Option 4: Using Make (if you have it installed)

If you have `make` installed (via WSL, Git Bash, or Chocolatey):

```bash
make up
make migrate
make install-sdk
make demo
```

## Troubleshooting

### Issue: "docker-compose is not recognized"

**Solution:** You're using Docker Desktop with Compose V2. Use `docker compose` (with space) instead of `docker-compose` (with hyphen).

Or use the provided scripts:
- PowerShell: `.\agentguard.ps1 up`
- CMD: `agentguard.bat up`

### Issue: "Cannot be loaded because running scripts is disabled"

If you get this error when running PowerShell scripts:

```powershell
# Run this in PowerShell as Administrator
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then try again.

### Issue: "pip is not recognized"

**Solution:** Make sure Python is installed and added to PATH.

```powershell
# Check if Python is installed
python --version

# If not, download and install from python.org
# Make sure to check "Add Python to PATH" during installation
```

### Issue: Docker containers won't start

**Solution:** Make sure Docker Desktop is running.

1. Open Docker Desktop application
2. Wait for it to fully start (icon should be green)
3. Try again: `.\agentguard.ps1 up`

### Issue: Port already in use (8000 or 3000)

**Solution:** Stop the service using that port or change the port in `docker-compose.yml`.

```powershell
# Check what's using port 8000
netstat -ano | findstr :8000

# Kill the process (replace <PID> with the actual process ID)
taskkill /PID <PID> /F
```

## Available Commands

### PowerShell Script (`.\agentguard.ps1`)

| Command | Description |
|---------|-------------|
| `up` | Start all services |
| `down` | Stop all services |
| `logs` | View logs from all services |
| `ps` | Show running services |
| `migrate` | Run database migrations |
| `rollback` | Rollback last migration |
| `test` | Run backend tests |
| `clean` | Stop and remove all containers, volumes |
| `build` | Rebuild all containers |
| `restart` | Restart all services |
| `install-sdk` | Install SDK locally |
| `demo` | Run quickstart demo |
| `help` | Show help message |

### Batch Script (`agentguard.bat`)

Same commands as PowerShell script, but run as:
```cmd
agentguard.bat <command>
```

## Accessing Services

Once services are running:

- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **UI Dashboard**: http://localhost:3000
- **PostgreSQL**: `localhost:5432`

## Development Workflow

### 1. Start Development Environment

```powershell
.\agentguard.ps1 up
.\agentguard.ps1 migrate
```

### 2. View Logs

```powershell
.\agentguard.ps1 logs
```

Press `Ctrl+C` to exit.

### 3. Run Tests

```powershell
.\agentguard.ps1 test
```

### 4. Stop Services

```powershell
.\agentguard.ps1 down
```

## Using Python Virtual Environment (Optional)

For SDK development:

```powershell
# Create virtual environment
python -m venv venv

# Activate it
.\venv\Scripts\Activate.ps1

# Install SDK in development mode
cd sdk
pip install -e .

# Run demo
python examples\quickstart.py
```

## IDE Setup

### VS Code

Install recommended extensions:
- Python
- Docker
- PostgreSQL

Open the workspace:
```powershell
code .
```

### PyCharm

1. Open the `agentguard` directory
2. Configure Python interpreter to use Python 3.11+
3. Mark `backend/app` as sources root

## Next Steps

1. Read the main [README.md](README.md) for detailed documentation
2. Try the quickstart demo: `.\agentguard.ps1 demo`
3. View logs in the UI: http://localhost:3000
4. Explore the API docs: http://localhost:8000/docs
5. Integrate with your AI agents using the SDK

## Getting Help

If you encounter issues:

1. Check Docker Desktop is running
2. Verify ports 8000, 3000, and 5432 are available
3. Check logs: `.\agentguard.ps1 logs`
4. Try rebuilding: `.\agentguard.ps1 clean` then `.\agentguard.ps1 up`
5. Report issues: https://github.com/yourorg/agentguard/issues

---

**Note**: All paths in this guide use Windows-style backslashes (`\`). The scripts handle this automatically.
