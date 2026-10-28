.PHONY: help install build serve dev start test scan clean

help:
	@echo "HireReady Commands:"
	@echo "  make start   - Build frontend & launch unified Web Dashboard (http://localhost:8000)"
	@echo "  make dev     - Run Python FastAPI backend (:8000) & React Vite (:5173) concurrently"
	@echo "  make build   - Build production React frontend bundle"
	@echo "  make scan    - Run CLI ATS job scanner"
	@echo "  make test    - Run pytest test suite"
	@echo "  make install - Install Python requirements & Node dependencies"

start: build
	@echo "Starting unified HireReady application..."
	./venv/bin/python main.py serve --port 8000

dev:
	@echo "Starting Python FastAPI (:8000) and React Vite (:5173) concurrently..."
	@bash -c "trap 'kill 0' SIGINT EXIT; ./venv/bin/python main.py serve --reload & (cd frontend && npm run dev) & wait"

build:
	@echo "Building React frontend..."
	cd frontend && npm run build

install:
	./venv/bin/pip install -r requirements.txt
	cd frontend && npm install

scan:
	./venv/bin/python main.py scan

test:
	./venv/bin/pytest
