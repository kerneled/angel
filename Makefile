.PHONY: api frontend up down logs build clean

# --- Development (local) ---
api:
	cd api && uvicorn main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd frontend && npm run dev

# --- Docker ---
up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f

build:
	docker compose build

# --- Utilities ---
clean:
	docker compose down -v
	rm -rf data/sessions.db

health:
	curl -s http://localhost:8000/api/health | python3 -m json.tool
