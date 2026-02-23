# AgentGuard - Local Setup (No Docker)

This guide helps you run AgentGuard entirely on your local machine without Docker.

## Prerequisites

- Python 3.11+ (https://www.python.org/downloads/)
- Node.js 18+ (https://nodejs.org/)

That's it!

## Quick Start

### 1. Install Backend Dependencies

```powershell
cd backend
pip install -r requirements.txt
```

### 2. Setup Database (SQLite)

```powershell
# Still in backend directory
# Set environment to use SQLite
$env:DATABASE_URL = "sqlite:///./agentguard.db"
$env:ADMIN_API_KEY = "admin-secret-key-change-in-production"

# Run migrations
alembic upgrade head
```

### 3. Start Backend

```powershell
# Still in backend directory
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend is now running at http://localhost:8000

### 4. Install and Test SDK (New Terminal)

```powershell
cd sdk
pip install -e .

# Set environment variables
$env:AGENTGUARD_URL = "http://localhost:8000"
$env:ADMIN_API_KEY = "admin-secret-key-change-in-production"

# Run demo
python examples\quickstart.py
```

### 5. Start UI (New Terminal - Optional)

```powershell
cd ui
npm install
npm run dev
```

UI is now running at http://localhost:3000

## Complete Startup Script

Save this as `start-local.ps1`:

```powershell
# Start backend in background
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd backend; `$env:DATABASE_URL='sqlite:///./agentguard.db'; `$env:ADMIN_API_KEY='admin-secret-key-change-in-production'; uvicorn app.main:app --reload --port 8000"

# Wait a moment
Start-Sleep -Seconds 3

# Start UI in background
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd ui; npm run dev"

Write-Host "Services starting..."
Write-Host "Backend: http://localhost:8000"
Write-Host "UI: http://localhost:3000"
```

## Environment Variables

Create a `.env` file in the `backend` directory:

```env
DATABASE_URL=sqlite:///./agentguard.db
ADMIN_API_KEY=admin-secret-key-change-in-production
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000
```

Then start backend with:

```powershell
cd backend
uvicorn app.main:app --reload
```

## Troubleshooting

### Backend won't start

Check Python version:
```powershell
python --version  # Should be 3.11+
```

Install dependencies:
```powershell
cd backend
pip install -r requirements.txt
```

### UI won't start

Check Node version:
```powershell
node --version  # Should be 18+
```

Install dependencies:
```powershell
cd ui
npm install
```

### Database errors

Reset database:
```powershell
cd backend
Remove-Item agentguard.db -ErrorAction SilentlyContinue
alembic upgrade head
```

## Development Workflow

### Terminal 1 - Backend
```powershell
cd backend
$env:DATABASE_URL = "sqlite:///./agentguard.db"
$env:ADMIN_API_KEY = "admin-secret-key"
uvicorn app.main:app --reload
```

### Terminal 2 - UI (optional)
```powershell
cd ui
npm run dev
```

### Terminal 3 - Testing
```powershell
cd sdk
pip install -e .
python examples\quickstart.py
```

## Running Tests

```powershell
cd backend
pytest -v
```

## Using PostgreSQL Instead of SQLite

If you want to use PostgreSQL later:

1. Install PostgreSQL locally
2. Create database:
   ```sql
   CREATE DATABASE agentguard;
   ```
3. Update DATABASE_URL:
   ```
   DATABASE_URL=postgresql://postgres:password@localhost:5432/agentguard
   ```
4. Run migrations:
   ```powershell
   alembic upgrade head
   ```

## Stopping Services

Press `Ctrl+C` in each terminal window to stop the services.

Or if you used the startup script, close the PowerShell windows.
