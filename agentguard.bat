@echo off
REM AgentGuard Batch Script for Windows CMD
REM Usage: agentguard.bat <command>

if "%1"=="" goto help
if "%1"=="help" goto help
if "%1"=="up" goto up
if "%1"=="down" goto down
if "%1"=="logs" goto logs
if "%1"=="ps" goto ps
if "%1"=="migrate" goto migrate
if "%1"=="rollback" goto rollback
if "%1"=="test" goto test
if "%1"=="clean" goto clean
if "%1"=="build" goto build
if "%1"=="restart" goto restart
if "%1"=="install-sdk" goto install-sdk
if "%1"=="demo" goto demo
goto unknown

:help
echo.
echo AgentGuard - Commands
echo ====================
echo.
echo Usage: agentguard.bat ^<command^>
echo.
echo Available commands:
echo   up          - Start all services
echo   down        - Stop all services
echo   logs        - View logs from all services
echo   ps          - Show running services
echo   migrate     - Run database migrations
echo   rollback    - Rollback last migration
echo   test        - Run backend tests
echo   clean       - Stop and remove all containers, volumes
echo   build       - Rebuild all containers
echo   restart     - Restart all services
echo   install-sdk - Install SDK locally
echo   demo        - Run quickstart demo
echo   help        - Show this help message
echo.
goto end

:up
echo Starting all services...
docker compose up -d
echo.
echo Services started!
echo   Backend API: http://localhost:8000
echo   UI Dashboard: http://localhost:3000
echo   API Docs: http://localhost:8000/docs
goto end

:down
echo Stopping all services...
docker compose down
goto end

:logs
echo Viewing logs (Ctrl+C to exit)...
docker compose logs -f
goto end

:ps
echo Running services:
docker compose ps
goto end

:migrate
echo Running database migrations...
docker compose exec backend alembic upgrade head
goto end

:rollback
echo Rolling back last migration...
docker compose exec backend alembic downgrade -1
goto end

:test
echo Running tests...
docker compose exec backend pytest -v
goto end

:clean
echo Cleaning up containers and volumes...
docker compose down -v
echo Cleaned up!
goto end

:build
echo Rebuilding containers...
docker compose build
goto end

:restart
echo Restarting services...
docker compose restart
goto end

:install-sdk
echo Installing SDK locally...
cd sdk
pip install -e .
cd ..
echo SDK installed!
goto end

:demo
echo Running quickstart demo...
cd sdk
python examples\quickstart.py
cd ..
goto end

:unknown
echo Unknown command: %1
echo.
echo Run 'agentguard.bat help' for available commands
goto end

:end
