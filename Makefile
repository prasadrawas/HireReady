.PHONY: help install build serve dev start test scan clean

help:
	@echo "HireReady Commands:"
	@echo "  make start     - Build frontend & launch unified Web Dashboard (http://localhost:8000)"
	@echo "  make dev       - Run FastAPI backend (:8000) & Vite dev server (:5173) concurrently"
	@echo "  make serve     - Run FastAPI backend only (:8000)"
	@echo "  make build     - Build production React frontend bundle"
	@echo "  make scan      - Run CLI ATS job scanner"
	@echo "  make test      - Run pytest test suite"
	@echo "  make install   - Install Python & Node dependencies"
	@echo "  make clean     - Clear Python caches, scan data, and built assets"

# Production: build frontend, then serve everything from FastAPI on :8000
start: build serve

# Development: run backend + frontend dev servers concurrently
dev:
	@echo "Starting FastAPI (:8000) and Vite (:5173) concurrently..."
	@bash -c "trap 'kill 0' SIGINT EXIT; \
		./venv/bin/uvicorn src.api.app:app --reload --port 8000 & \
		(cd frontend && npm run dev) & \
		wait"

# Backend only
serve:
	@echo "Starting HireReady API on http://localhost:8000"
	./venv/bin/uvicorn src.api.app:app --host 0.0.0.0 --port 8000

# Build frontend for production
build:
	@echo "Building React frontend..."
	cd frontend && npm run build

# Install all dependencies
install:
	@test -d venv || python3 -m venv venv
	./venv/bin/pip install -r requirements.txt
	./venv/bin/playwright install chromium
	cd frontend && npm install

# Run ATS scanner via CLI
scan:
	./venv/bin/python main.py scan

# Run test suite
test:
	./venv/bin/python -m pytest tests/ -v

# Clean caches and generated data
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache frontend/dist
	@echo "Cleaned. Run 'make build' to rebuild frontend."
