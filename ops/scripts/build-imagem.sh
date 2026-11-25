#!/usr/bin/env bash
# Gera a imagem do Frappe ja com o app dom_despachante embutido.
# Uso: ./build-imagem.sh <caminho-do-frappe_docker> <tag>
set -euo pipefail

FRAPPE_DOCKER_DIR="${1:-$HOME/frappe_docker}"
TAG="${2:-dom-erp:1.0.0}"
APPS_JSON="${APPS_JSON:-$HOME/dom-despachante/apps.json}"

cd "$FRAPPE_DOCKER_DIR"

export APPS_JSON_BASE64
APPS_JSON_BASE64=$(base64 -w 0 "$APPS_JSON")

docker build \
  --build-arg=FRAPPE_PATH=https://github.com/frappe/frappe \
  --build-arg=FRAPPE_BRANCH=version-15 \
  --build-arg=APPS_JSON_BASE64="$APPS_JSON_BASE64" \
  --tag="$TAG" \
  --file=images/custom/Containerfile .

echo "Imagem gerada: $TAG"
echo "Agora ajuste CUSTOM_IMAGE/CUSTOM_TAG no .env do frappe_docker e rode: docker compose up -d"