.PHONY: dev docker-up docker-down migrate test lint install clean

# ── Local Development ─────────────────────────────────────────────────────────

install:
	@echo "Installing backend dependencies..."
	cd backend && pip install -e ".[dev]"
	@echo "Installing frontend dependencies..."
	cd frontend && npm install

dev: install
	@echo "Starting backend and frontend in parallel..."
	Start-Process powershell -ArgumentList "cd backend; uvicorn app.main:app --reload --port 8000"
	Start-Process powershell -ArgumentList "cd frontend; npm run start"

dev-backend:
	cd backend && uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm start

dev-celery:
	cd backend && celery -A app.workers.celery_app worker --loglevel=info

# ── Database ──────────────────────────────────────────────────────────────────

migrate:
	cd backend && alembic upgrade head

migrate-create:
	@read -p "Migration name: " name; cd backend && alembic revision --autogenerate -m "$$name"

migrate-down:
	cd backend && alembic downgrade -1

# ── Docker ────────────────────────────────────────────────────────────────────

docker-up:
	docker-compose up -d
	@echo "Services started:"
	@echo "  Frontend:  http://localhost:4200"
	@echo "  Backend:   http://localhost:8000"
	@echo "  API Docs:  http://localhost:8000/docs"
	@echo "  ChromaDB:  http://localhost:8001"

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-build:
	docker-compose build --no-cache

docker-restart:
	docker-compose restart backend

# ── Testing & Quality ─────────────────────────────────────────────────────────

test:
	cd backend && pytest tests/ -v --cov=app --cov-report=html

test-frontend:
	cd frontend && ng test --watch=false

lint:
	cd backend && ruff check app/ && ruff format app/ --check

lint-fix:
	cd backend && ruff check app/ --fix && ruff format app/

type-check:
	cd backend && mypy app/

# ── Cleanup ───────────────────────────────────────────────────────────────────

clean:
	find . -name "__pycache__" -type d -exec rm -rf {} +
	find . -name "*.pyc" -delete
	find . -name ".ruff_cache" -type d -exec rm -rf {} +
	rm -rf backend/.pytest_cache backend/htmlcov
