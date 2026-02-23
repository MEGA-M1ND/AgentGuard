# Detect docker compose command (V2 uses 'docker compose', V1 uses 'docker-compose')
DOCKER_COMPOSE := $(shell docker compose version > /dev/null 2>&1 && echo "docker compose" || echo "docker-compose")

.PHONY: up down logs ps migrate rollback migration test format lint clean help

help: ## Show this help message
	@echo "AgentGuard - Makefile Commands"
	@echo ""
	@echo "Available commands:"
	@echo "  up          - Start all services"
	@echo "  down        - Stop all services"
	@echo "  logs        - View logs from all services"
	@echo "  ps          - Show running services"
	@echo "  migrate     - Run database migrations"
	@echo "  rollback    - Rollback last migration"
	@echo "  test        - Run backend tests"
	@echo "  format      - Format code with black and ruff"
	@echo "  lint        - Lint code with ruff"
	@echo "  clean       - Stop and remove all containers, volumes"
	@echo "  build       - Rebuild all containers"
	@echo "  restart     - Restart all services"
	@echo "  demo        - Run quickstart demo"

up: ## Start all services
	$(DOCKER_COMPOSE) up -d
	@echo "Services started. Backend: http://localhost:8000, UI: http://localhost:3000"

down: ## Stop all services
	$(DOCKER_COMPOSE) down

logs: ## View logs from all services
	$(DOCKER_COMPOSE) logs -f

ps: ## Show running services
	$(DOCKER_COMPOSE) ps

migrate: ## Run database migrations
	$(DOCKER_COMPOSE) exec backend alembic upgrade head

rollback: ## Rollback last migration
	$(DOCKER_COMPOSE) exec backend alembic downgrade -1

migration: ## Create new migration (use: make migration MSG="description")
	@if [ -z "$(MSG)" ]; then \
		echo "Error: MSG is required. Usage: make migration MSG='your message'"; \
		exit 1; \
	fi
	$(DOCKER_COMPOSE) exec backend alembic revision --autogenerate -m "$(MSG)"

test: ## Run backend tests
	$(DOCKER_COMPOSE) exec backend pytest -v

test-local: ## Run tests locally (outside Docker)
	cd backend && pytest -v

format: ## Format code with black and ruff
	cd backend && black app/ tests/ && ruff check --fix app/ tests/

lint: ## Lint code with ruff
	cd backend && ruff check app/ tests/

clean: ## Stop and remove all containers, volumes
	$(DOCKER_COMPOSE) down -v
	@echo "Cleaned up containers and volumes"

build: ## Rebuild all containers
	$(DOCKER_COMPOSE) build

restart: ## Restart all services
	$(DOCKER_COMPOSE) restart

shell-backend: ## Open shell in backend container
	$(DOCKER_COMPOSE) exec backend /bin/bash

shell-db: ## Open PostgreSQL shell
	$(DOCKER_COMPOSE) exec postgres psql -U agentguard -d agentguard

install-sdk: ## Install SDK locally for development
	cd sdk && pip install -e .

demo: ## Run quickstart demo (requires SDK installed)
	cd sdk && python examples/quickstart.py
