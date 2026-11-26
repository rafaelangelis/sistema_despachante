#!/usr/bin/env bash
# Gera a imagem do Frappe ja com o app dom_despachante embutido.
# Uso: ./build-imagem.sh <caminho-do-frappe_docker> <tag>
#
# Desde 2026 o frappe_docker recebe o apps.json como *build secret*
# (--secret id=apps_json). O antigo --build-arg APPS_JSON_BASE64 e ignorado
# em silencio: a imagem sai so com o frappe, sem o app.
# O padrao da imagem tambem passou a ser Python 3.14 / Debian trixie (Frappe v16);
# o Frappe v15 exige Python 3.10-3.12, por isso fixamos 3.11 + bookworm.
#
# CACHE_BUST: o conteudo do secret NAO entra na chave de cache do Docker. Sem isto um
# rebuild reaproveita o clone antigo do app e a imagem "nova" sai com o codigo velho
# (aconteceu no teste). Com ele, o bench init roda de novo a cada build (~5-10 min).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRAPPE_DOCKER_DIR="${1:-$HOME/frappe_docker}"
TAG="${2:-dom-erp:1.0.0}"
APPS_JSON="${APPS_JSON:-$SCRIPT_DIR/../apps.json}"
APPS_JSON="$(cd "$(dirname "$APPS_JSON")" && pwd)/$(basename "$APPS_JSON")"

cd "$FRAPPE_DOCKER_DIR"

docker build \
  --build-arg=FRAPPE_PATH=https://github.com/frappe/frappe \
  --build-arg=FRAPPE_BRANCH=version-15 \
  --build-arg=PYTHON_VERSION=3.11.9 \
  --build-arg=DEBIAN_BASE=bookworm \
  --secret=id=apps_json,src="$APPS_JSON" \
  --build-arg=CACHE_BUST="$(date +%s)" \
  --tag="$TAG" \
  --file=images/custom/Containerfile .

# o entrypoint da imagem imprime texto antes do comando; use --entrypoint para conferir
echo "Apps na imagem:"
docker run --rm --entrypoint ls "$TAG" /home/frappe/frappe-bench/apps

echo "Imagem gerada: $TAG"
echo "Agora ajuste CUSTOM_IMAGE/CUSTOM_TAG no .env do frappe_docker e rode: docker compose up -d"
