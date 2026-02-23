# AgentGuard PowerShell Script for Windows
# Usage: .\agentguard.ps1 <command>

param(
    [Parameter(Position=0)]
    [string]$Command = "help",

    [Parameter(Position=1)]
    [string]$Arg
)

function Show-Help {
    Write-Host ""
    Write-Host "AgentGuard - PowerShell Commands" -ForegroundColor Cyan
    Write-Host "================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage: .\agentguard.ps1 <command>" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Available commands:" -ForegroundColor Green
    Write-Host "  up          - Start all services"
    Write-Host "  down        - Stop all services"
    Write-Host "  logs        - View logs from all services"
    Write-Host "  ps          - Show running services"
    Write-Host "  migrate     - Run database migrations"
    Write-Host "  rollback    - Rollback last migration"
    Write-Host "  test        - Run backend tests"
    Write-Host "  clean       - Stop and remove all containers, volumes"
    Write-Host "  build       - Rebuild all containers"
    Write-Host "  restart     - Restart all services"
    Write-Host "  install-sdk - Install SDK locally for development"
    Write-Host "  demo        - Run quickstart demo"
    Write-Host "  help        - Show this help message"
    Write-Host ""
}

function Invoke-DockerCompose {
    param([string[]]$Arguments)

    # Try docker compose (V2) first, fallback to docker-compose (V1)
    $composeCmd = Get-Command "docker" -ErrorAction SilentlyContinue
    if ($composeCmd) {
        $testCompose = docker compose version 2>&1
        if ($LASTEXITCODE -eq 0) {
            docker compose @Arguments
        } else {
            docker-compose @Arguments
        }
    } else {
        Write-Host "Error: Docker is not installed or not in PATH" -ForegroundColor Red
        exit 1
    }
}

switch ($Command.ToLower()) {
    "up" {
        Write-Host "Starting all services..." -ForegroundColor Green
        Invoke-DockerCompose "up", "-d"
        Write-Host ""
        Write-Host "Services started!" -ForegroundColor Green
        Write-Host "  Backend API: http://localhost:8000" -ForegroundColor Cyan
        Write-Host "  UI Dashboard: http://localhost:3000" -ForegroundColor Cyan
        Write-Host "  API Docs: http://localhost:8000/docs" -ForegroundColor Cyan
    }

    "down" {
        Write-Host "Stopping all services..." -ForegroundColor Yellow
        Invoke-DockerCompose "down"
    }

    "logs" {
        Write-Host "Viewing logs (Ctrl+C to exit)..." -ForegroundColor Cyan
        Invoke-DockerCompose "logs", "-f"
    }

    "ps" {
        Write-Host "Running services:" -ForegroundColor Cyan
        Invoke-DockerCompose "ps"
    }

    "migrate" {
        Write-Host "Running database migrations..." -ForegroundColor Green
        Invoke-DockerCompose "exec", "backend", "alembic", "upgrade", "head"
    }

    "rollback" {
        Write-Host "Rolling back last migration..." -ForegroundColor Yellow
        Invoke-DockerCompose "exec", "backend", "alembic", "downgrade", "-1"
    }

    "test" {
        Write-Host "Running tests..." -ForegroundColor Green
        Invoke-DockerCompose "exec", "backend", "pytest", "-v"
    }

    "clean" {
        Write-Host "Cleaning up containers and volumes..." -ForegroundColor Yellow
        Invoke-DockerCompose "down", "-v"
        Write-Host "Cleaned up!" -ForegroundColor Green
    }

    "build" {
        Write-Host "Rebuilding containers..." -ForegroundColor Cyan
        Invoke-DockerCompose "build"
    }

    "restart" {
        Write-Host "Restarting services..." -ForegroundColor Cyan
        Invoke-DockerCompose "restart"
    }

    "install-sdk" {
        Write-Host "Installing SDK locally..." -ForegroundColor Green
        Push-Location sdk
        pip install -e .
        Pop-Location
        Write-Host "SDK installed!" -ForegroundColor Green
    }

    "demo" {
        Write-Host "Running quickstart demo..." -ForegroundColor Green
        Push-Location sdk
        python examples/quickstart.py
        Pop-Location
    }

    "help" {
        Show-Help
    }

    default {
        Write-Host "Unknown command: $Command" -ForegroundColor Red
        Write-Host ""
        Show-Help
        exit 1
    }
}
