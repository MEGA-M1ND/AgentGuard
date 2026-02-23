# AgentGuard Local Development Startup Script
# Starts backend and UI without Docker

param(
    [switch]$SkipUI,
    [switch]$SetupOnly
)

Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "   AgentGuard Local Setup" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Check Python
Write-Host "[1/5] Checking Python..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Python not found. Please install Python 3.11+" -ForegroundColor Red
    exit 1
}
Write-Host "  ✓ $pythonVersion" -ForegroundColor Green

# Check if in correct directory
if (-not (Test-Path "backend")) {
    Write-Host "ERROR: Please run this script from the agentguard directory" -ForegroundColor Red
    exit 1
}

# Install backend dependencies
Write-Host ""
Write-Host "[2/5] Installing backend dependencies..." -ForegroundColor Yellow
Push-Location backend
$installed = Test-Path "venv"
if (-not $installed) {
    Write-Host "  Creating virtual environment..." -ForegroundColor Cyan
    python -m venv venv
    .\venv\Scripts\Activate.ps1
    pip install -r requirements.txt
} else {
    Write-Host "  Virtual environment exists, activating..." -ForegroundColor Cyan
    .\venv\Scripts\Activate.ps1
}
Write-Host "  ✓ Dependencies installed" -ForegroundColor Green

# Setup database
Write-Host ""
Write-Host "[3/5] Setting up database..." -ForegroundColor Yellow
$env:DATABASE_URL = "sqlite:///./agentguard.db"
$env:ADMIN_API_KEY = "admin-secret-key-change-in-production"
$env:CORS_ORIGINS = "http://localhost:3000"

if (-not (Test-Path "agentguard.db")) {
    Write-Host "  Running migrations..." -ForegroundColor Cyan
    alembic upgrade head
    Write-Host "  ✓ Database created" -ForegroundColor Green
} else {
    Write-Host "  ✓ Database exists" -ForegroundColor Green
}

Pop-Location

# Install SDK
Write-Host ""
Write-Host "[4/5] Installing SDK..." -ForegroundColor Yellow
Push-Location sdk
pip install -e . | Out-Null
Write-Host "  ✓ SDK installed" -ForegroundColor Green
Pop-Location

if ($SetupOnly) {
    Write-Host ""
    Write-Host "Setup complete! To start services:" -ForegroundColor Green
    Write-Host "  cd backend"
    Write-Host "  .\venv\Scripts\Activate.ps1"
    Write-Host "  uvicorn app.main:app --reload"
    exit 0
}

# Start backend
Write-Host ""
Write-Host "[5/5] Starting services..." -ForegroundColor Yellow
Write-Host ""

Write-Host "Starting backend server..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$PWD\backend'; " +
    ".\venv\Scripts\Activate.ps1; " +
    "`$env:DATABASE_URL='sqlite:///./agentguard.db'; " +
    "`$env:ADMIN_API_KEY='admin-secret-key-change-in-production'; " +
    "`$env:CORS_ORIGINS='http://localhost:3000'; " +
    "Write-Host 'Backend starting on http://localhost:8000' -ForegroundColor Green; " +
    "uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
)

# Wait for backend to start
Write-Host "Waiting for backend to start..." -ForegroundColor Cyan
Start-Sleep -Seconds 5

# Test backend
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 5
    Write-Host "  ✓ Backend is running at http://localhost:8000" -ForegroundColor Green
} catch {
    Write-Host "  ⚠ Backend may still be starting..." -ForegroundColor Yellow
}

# Start UI if not skipped
if (-not $SkipUI) {
    Write-Host ""
    Write-Host "Starting UI..." -ForegroundColor Cyan

    # Check if Node is installed
    $nodeVersion = node --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ⚠ Node.js not found. Skipping UI." -ForegroundColor Yellow
        Write-Host "    Install from: https://nodejs.org/" -ForegroundColor Yellow
    } else {
        Write-Host "  Node.js version: $nodeVersion" -ForegroundColor Cyan

        # Check if node_modules exists
        if (-not (Test-Path "ui\node_modules")) {
            Write-Host "  Installing UI dependencies (this may take a minute)..." -ForegroundColor Cyan
            Push-Location ui
            npm install | Out-Null
            Pop-Location
        }

        Start-Process powershell -ArgumentList @(
            "-NoExit",
            "-Command",
            "cd '$PWD\ui'; " +
            "`$env:NEXT_PUBLIC_API_URL='http://localhost:8000'; " +
            "Write-Host 'UI starting on http://localhost:3000' -ForegroundColor Green; " +
            "npm run dev"
        )
        Write-Host "  ✓ UI is starting at http://localhost:3000" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "   Services Started!" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Backend API:       http://localhost:8000" -ForegroundColor Cyan
Write-Host "API Docs:          http://localhost:8000/docs" -ForegroundColor Cyan
if (-not $SkipUI) {
    Write-Host "UI Dashboard:      http://localhost:3000" -ForegroundColor Cyan
}
Write-Host ""
Write-Host "Try the demo:" -ForegroundColor Yellow
Write-Host "  cd sdk" -ForegroundColor Gray
Write-Host "  python examples\quickstart.py" -ForegroundColor Gray
Write-Host ""
Write-Host "To stop: Close the PowerShell windows or press Ctrl+C" -ForegroundColor Yellow
Write-Host ""
