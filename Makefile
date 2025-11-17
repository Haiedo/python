.PHONY: help build up down restart logs shell seed test clean

help:
	@echo "Expense Splitter - Docker Commands"
	@echo ""
	@echo "Development:"
	@echo "  make build     - Build Docker images"
	@echo "  make up        - Start development environment"
	@echo "  make down      - Stop all containers"
	@echo "  make restart   - Restart containers"
	@echo "  make logs      - View logs"
	@echo "  make shell     - Access container shell"
	@echo ""
	@echo "Database:"
	@echo "  make seed      - Run seed data"
	@echo ""
	@echo "Testing:"
	@echo "  make test      - Run tests in running container"
	@echo "  make test-cov  - Run tests with coverage in isolated container"
	@echo ""
	@echo "Production:"
	@echo "  make up-prod   - Start production environment"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean     - Remove containers and volumes"

build:
	docker-compose build

up:
	docker-compose up -d
	@echo "Application is running at http://localhost:5000"

up-prod:
	docker-compose --profile production up -d web-prod db
	@echo "Production application is running at http://localhost:5000"

down:
	docker-compose down

restart:
	docker-compose restart

logs:
	docker-compose logs -f web

shell:
	docker-compose exec web bash

seed:
	docker-compose exec web python seed_data.py

test:
	docker-compose exec web pytest

test-cov:
	docker-compose -f docker-compose.test.yml run --rm test

clean:
	docker-compose down -v
	@echo "All containers and volumes removed"
