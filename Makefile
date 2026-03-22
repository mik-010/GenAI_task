.PHONY: help setup generate db-up db-down ingest dashboard api test all

help:
	@echo "Claude Code Analytics Platform"
	@echo "  make setup      - Install Python dependencies"
	@echo "  make generate   - Generate synthetic telemetry data"
	@echo "  make db-up      - Start PostgreSQL via Docker"
	@echo "  make db-down    - Stop PostgreSQL"
	@echo "  make ingest     - Ingest data into PostgreSQL"
	@echo "  make dashboard  - Launch Dash dashboard"
	@echo "  make api        - Launch FastAPI service"
	@echo "  make test       - Run test suite"
	@echo "  make all        - Full pipeline: generate -> db-up -> ingest -> dashboard"

setup:
	pip install -r requirements.txt

generate:
	python3 generate_fake_data.py --num-users 100 --num-sessions 5000 --days 60

db-up:
	docker compose up -d
	@echo "Waiting for PostgreSQL..."
	@sleep 3

db-down:
	docker compose down

ingest:
	python3 -m app.ingestion.run --input-dir output

dashboard:
	python3 -m app.dashboard.app

api:
	uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload

test:
	python3 -m pytest tests/ -v

all: generate db-up ingest dashboard
