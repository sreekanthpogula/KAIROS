.PHONY: install dev backend frontend test seed ingest evaluate demo docker-up docker-down

VENV := backend/.venv
PY := $(VENV)/Scripts/python.exe

install:
	python -m venv $(VENV)
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -r backend/requirements.txt
	cd frontend && npm install

backend:
	cd backend && ../$(PY) -m uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

dev:
	@echo "Run 'make backend' and 'make frontend' in two separate terminals."

test:
	cd backend && ../$(PY) -m pytest -v

seed:
	$(PY) scripts/seed_demo_data.py

ingest:
	$(PY) scripts/run_demo_ingestion.py

evaluate:
	$(PY) scripts/evaluate.py

demo: install seed ingest evaluate
	@echo ""
	@echo "Demo data ready. Now run 'make backend' and 'make frontend' in two terminals,"
	@echo "then open http://localhost:5173"

docker-up:
	docker compose up --build

docker-down:
	docker compose down
