#!/usr/bin/env bash
# deploy.sh — Sincroniza el código de develop a producción en /opt/flow_transcriber
# Uso: bash deploy/deploy.sh
set -euo pipefail

DEV_DIR="/home/lf/git/flow_transcriber"
PROD_DIR="/opt/flow_transcriber"
SERVICE="flow-transcriber-prod"
VENV="$PROD_DIR/.venv"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Flow Transcriber — Deploy develop → producción"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1. Crear directorio si no existe
sudo mkdir -p "$PROD_DIR"
sudo chown www-data:www-data "$PROD_DIR"

# 2. Sincronizar ficheros (excluye .git, venv, caché, datos de trabajo)
echo "▶ Sincronizando ficheros…"
sudo rsync -av --delete \
    --exclude='.git/' \
    --exclude='.venv/' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    --exclude='.env' \
    --exclude='out/' \
    --exclude='.work/' \
    "$DEV_DIR/" "$PROD_DIR/"

# 3. Crear/actualizar venv de prod
echo "▶ Configurando entorno virtual de producción…"
if [[ ! -d "$VENV" ]]; then
    sudo python3 -m venv "$VENV"
fi
sudo "$VENV/bin/pip" install --upgrade pip -q
sudo "$VENV/bin/pip" install -r "$PROD_DIR/requirements.txt" -q

# 4. Asegurar que existe un .env en prod (no se sobreescribe)
if [[ ! -f "$PROD_DIR/.env" ]]; then
    echo "▶ Copiando .env.example como .env (editar antes de continuar)"
    sudo cp "$PROD_DIR/.env.example" "$PROD_DIR/.env"
    echo "  ⚠ Edita $PROD_DIR/.env con los valores de producción."
fi

# 5. Reiniciar servicio
echo "▶ Reiniciando servicio $SERVICE…"
sudo systemctl restart "$SERVICE"
sudo systemctl status "$SERVICE" --no-pager -l

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ Deploy completado → https://transcriber.luisforni.com"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
