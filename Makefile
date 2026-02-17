.PHONY: help docker-build docker-up docker-down docker-logs docker-shell docker-migrate docker-createsuperuser docker-test docker-clean

# Color output
BLUE=\033[0;34m
GREEN=\033[0;32m
YELLOW=\033[0;33m
RED=\033[0;31m
NC=\033[0m # No Color

help:
	@echo "$(BLUE)User Management System - Available Commands$(NC)"
	@echo ""
	@echo "$(GREEN)Docker Commands:$(NC)"
	@echo "  make docker-build       - Build Docker images"
	@echo "  make docker-up          - Start containers in background"
	@echo "  make docker-down        - Stop and remove containers"
	@echo "  make docker-logs        - View application logs (follow)"
	@echo "  make docker-shell       - Open shell in app container"
	@echo ""
	@echo "$(GREEN)Database Commands:$(NC)"
	@echo "  make migrate            - Run database migrations"
	@echo "  make migrations         - Create new migrations"
	@echo "  make superuser          - Create admin user"
	@echo ""
	@echo "$(GREEN)Testing Commands:$(NC)"
	@echo "  make test               - Run test suite"
	@echo "  make test-verbose       - Run tests with verbose output"
	@echo "  make coverage           - Run tests with coverage report"
	@echo ""
	@echo "$(GREEN)Development Commands:$(NC)"
	@echo "  make run                - Start development server"
	@echo "  make clean              - Clean up Docker resources"
	@echo "  make ps                 - List running containers"
	@echo ""

# ============================================================================
# Docker Commands
# ============================================================================

docker-build:
	@echo "$(BLUE)Building Docker images...$(NC)"
	docker-compose build

docker-up:
	@echo "$(BLUE)Starting containers...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)✅ Containers started!$(NC)"
	@echo "   App: http://localhost:8000"
	@echo "   Admin: http://localhost:8000/admin"

docker-down:
	@echo "$(BLUE)Stopping containers...$(NC)"
	docker-compose down
	@echo "$(GREEN)✅ Containers stopped!$(NC)"

docker-logs:
	@echo "$(BLUE)Streaming application logs...$(NC)"
	docker-compose logs -f app

docker-shell:
	@echo "$(BLUE)Opening shell in app container...$(NC)"
	docker-compose exec app bash

ps:
	@echo "$(BLUE)Running containers:$(NC)"
	docker-compose ps

# ============================================================================
# Database Commands
# ============================================================================

migrate:
	@echo "$(BLUE)Running migrations...$(NC)"
	docker-compose exec app python manage.py migrate
	@echo "$(GREEN)✅ Migrations completed!$(NC)"

migrations:
	@echo "$(BLUE)Creating migrations...$(NC)"
	docker-compose exec app python manage.py makemigrations
	@echo "$(GREEN)✅ Migrations created!$(NC)"

superuser:
	@echo "$(BLUE)Creating superuser...$(NC)"
	docker-compose exec app python manage.py createsuperuser

# ============================================================================
# Testing Commands
# ============================================================================

test:
	@echo "$(BLUE)Running test suite...$(NC)"
	docker-compose exec app python manage.py test accounts.test_user_management

test-verbose:
	@echo "$(BLUE)Running tests with verbose output...$(NC)"
	docker-compose exec app python manage.py test accounts.test_user_management -v 2

pytest:
	@echo "$(BLUE)Running pytest suite...$(NC)"
	docker-compose exec app pytest

pytest-verbose:
	@echo "$(BLUE)Running pytest with verbose output...$(NC)"
	docker-compose exec app pytest -v

pytest-cov:
	@echo "$(BLUE)Running pytest with coverage...$(NC)"
	docker-compose exec app pytest --cov=accounts --cov-report=html --cov-report=term
	@echo "$(GREEN)✅ Coverage report generated in htmlcov/index.html$(NC)"

pytest-markers:
	@echo "$(BLUE)Running specific test markers...$(NC)"
	@echo "Usage: make pytest-markers MARKER=auth"
	docker-compose exec app pytest -m $(MARKER)

coverage:
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	docker-compose exec app pip install coverage > /dev/null 2>&1
	docker-compose exec app coverage run --source='accounts' manage.py test accounts.test_user_management
	docker-compose exec app coverage report -m
	@echo "$(GREEN)✅ Coverage report generated!$(NC)"

# ============================================================================
# Development Commands
# ============================================================================

run:
	@echo "$(BLUE)Starting development server...$(NC)"
	docker-compose exec app python manage.py runserver 0.0.0.0:8000

shell:
	@echo "$(BLUE)Opening Django shell...$(NC)"
	docker-compose exec app python manage.py shell

static:
	@echo "$(BLUE)Collecting static files...$(NC)"
	docker-compose exec app python manage.py collectstatic --noinput
	@echo "$(GREEN)✅ Static files collected!$(NC)"

# ============================================================================
# Cleanup Commands
# ============================================================================

clean:
	@echo "$(YELLOW)Removing Docker resources...$(NC)"
	docker-compose down -v
	docker system prune -f
	@echo "$(GREEN)✅ Cleanup completed!$(NC)"

clean-containers:
	@echo "$(YELLOW)Removing containers...$(NC)"
	docker-compose down
	@echo "$(GREEN)✅ Containers removed!$(NC)"

clean-images:
	@echo "$(YELLOW)Removing images...$(NC)"
	docker-compose down --rmi all
	@echo "$(GREEN)✅ Images removed!$(NC)"

clean-volumes:
	@echo "$(YELLOW)Removing volumes...$(NC)"
	docker-compose down -v
	@echo "$(GREEN)✅ Volumes removed!$(NC)"

# ============================================================================
# Setup Commands
# ============================================================================

setup: docker-build docker-up migrate superuser
	@echo "$(GREEN)✅ Setup completed!$(NC)"
	@echo "   App: http://localhost:8000"
	@echo "   Admin: http://localhost:8000/admin"

restart:
	@echo "$(BLUE)Restarting containers...$(NC)"
	docker-compose restart
	@echo "$(GREEN)✅ Containers restarted!$(NC)"

# ============================================================================
# Utility Commands
# ============================================================================

requirements:
	@echo "$(BLUE)Installing requirements...$(NC)"
	docker-compose exec app pip install -r requirements.txt
	@echo "$(GREEN)✅ Requirements installed!$(NC)"

lint:
	@echo "$(BLUE)Running linter...$(NC)"
	docker-compose exec app pip install flake8 > /dev/null 2>&1
	docker-compose exec app flake8 accounts/
	@echo "$(GREEN)✅ Linting completed!$(NC)"

format:
	@echo "$(BLUE)Formatting code...$(NC)"
	docker-compose exec app pip install black > /dev/null 2>&1
	docker-compose exec app black accounts/
	@echo "$(GREEN)✅ Code formatted!$(NC)"

.DEFAULT_GOAL := help
