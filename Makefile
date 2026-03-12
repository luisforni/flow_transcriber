.PHONY: dev install deploy-prod \
        install-service-dev install-service-prod \
        install-nginx logs-dev logs-prod status

PYTHON   := python3
DEV_DIR  := /home/lf/git/flow_transcriber
PROD_DIR := /opt/flow_transcriber

# ── Desarrollo ────────────────────────────────────────────────────────────────
dev:
	streamlit run app.py \
	  --server.port 8502 \
	  --server.address 127.0.0.1 \
	  --server.headless true

# ── Dependencias ──────────────────────────────────────────────────────────────
install:
	$(PYTHON) -m pip install -r requirements.txt

# ── Deploy dev → prod ─────────────────────────────────────────────────────────
deploy-prod:
	bash deploy/deploy.sh

# ── Servicios systemd ─────────────────────────────────────────────────────────
install-service-dev:
	sudo cp deploy/flow-transcriber-dev.service /etc/systemd/system/
	sudo systemctl daemon-reload
	sudo systemctl enable flow-transcriber-dev
	sudo systemctl start flow-transcriber-dev
	@echo "✅ Servicio dev instalado y activo en el puerto 8502"

install-service-prod:
	sudo cp deploy/flow-transcriber-prod.service /etc/systemd/system/
	sudo systemctl daemon-reload
	sudo systemctl enable flow-transcriber-prod
	sudo systemctl start flow-transcriber-prod
	@echo "✅ Servicio prod instalado y activo en el puerto 8501"

# ── nginx ─────────────────────────────────────────────────────────────────────
install-nginx:
	sudo cp deploy/nginx-subdomain.conf /etc/nginx/sites-available/flow-transcriber
	sudo ln -sf /etc/nginx/sites-available/flow-transcriber /etc/nginx/sites-enabled/
	sudo nginx -t
	sudo systemctl reload nginx
	@echo "✅ nginx configurado. Para SSL: sudo certbot --nginx -d transcriber.luisforni.com"

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
