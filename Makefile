.PHONY: dev dev-backend dev-frontend install install-backend install-frontend \
        deploy-prod install-service-dev install-service-prod install-nginx \
        logs-dev logs-prod status \
        docker-build docker-up docker-down docker-logs docker-pull-model

PYTHON   := python3
DEV_DIR  := /home/lf/git/flow_transcriber

# ── Desarrollo local ──────────────────────────────────────────────────────────
dev-backend:
	cd backend && uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

dev-frontend:
	cd frontend && npm run dev

# Ejecuta backend y frontend en paralelo (requiere que ambos estén instalados)
dev:
	@echo "▶️  Iniciando backend (puerto 8000) y frontend (puerto 3000)…"
	$(MAKE) dev-backend & $(MAKE) dev-frontend

# ── Dependencias ──────────────────────────────────────────────────────────────
install-backend:
	cd backend && $(PYTHON) -m pip install -r requirements.txt

install-frontend:
	cd frontend && npm install

install: install-backend install-frontend

# ── Deploy prod (bare-metal) ──────────────────────────────────────────────────
deploy-prod:
	bash deploy/deploy.sh

install-service-dev:
	sudo cp deploy/flow-transcriber-dev.service /etc/systemd/system/
	sudo systemctl daemon-reload
	sudo systemctl enable flow-transcriber-dev
	sudo systemctl start flow-transcriber-dev
	@echo "✅ Servicio dev instalado"

install-service-prod:
	sudo cp deploy/flow-transcriber-prod.service /etc/systemd/system/
	sudo systemctl daemon-reload
	sudo systemctl enable flow-transcriber-prod
	sudo systemctl start flow-transcriber-prod
	@echo "✅ Servicio prod instalado"

install-nginx:
	sudo cp deploy/nginx-subdomain.conf /etc/nginx/sites-available/flow-transcriber
	sudo ln -sf /etc/nginx/sites-available/flow-transcriber /etc/nginx/sites-enabled/
	sudo nginx -t
	sudo systemctl reload nginx
	@echo "✅ nginx configurado."

# ── Logs y estado ─────────────────────────────────────────────────────────────
logs-dev:
	journalctl -u flow-transcriber-dev -f

logs-prod:
	journalctl -u flow-transcriber-prod -f

status:
	@echo "── Dev ──────────────────────────────────────"
	@systemctl is-active flow-transcriber-dev 2>/dev/null || echo "inactivo"
	@echo "── Prod ─────────────────────────────────────"
	@systemctl is-active flow-transcriber-prod 2>/dev/null || echo "inactivo"

# ── Docker ────────────────────────────────────────────────────────────────────
docker-build:
	docker compose build

## Levanta todos los servicios.
## Si Ollama ya corre en el host se conecta a él; si no, levanta el contenedor.
docker-up:
	@if curl -sf http://localhost:11434/ > /dev/null 2>&1; then \
		echo "✅ Ollama ya está corriendo en el host"; \
		OLLAMA_HOST=http://host.docker.internal:11434 docker compose up -d backend frontend; \
	else \
		echo "🐳 Ollama no detectado — iniciando contenedor Ollama..."; \
		docker compose --profile with-ollama up -d; \
	fi

docker-down:
	docker compose --profile with-ollama down

docker-logs:
	docker compose logs -f

## Descarga un modelo en Ollama (contenedor o host).
## Uso: make docker-pull-model MODEL=llama3
docker-pull-model:
	$(eval MODEL ?= llama3)
	@if docker ps --format '{{.Names}}' | grep -q flow-transcriber-ollama; then \
		echo "📥 Descargando $(MODEL) en el contenedor Ollama..."; \
		docker compose exec ollama ollama pull $(MODEL); \
	else \
		echo "📥 Descargando $(MODEL) en Ollama del host..."; \
		ollama pull $(MODEL); \
	fi
