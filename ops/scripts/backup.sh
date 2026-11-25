#!/usr/bin/env bash
# Backup diario do site Frappe (banco + arquivos) com retencao de 30 dias.
# Sugestao de cron (rodar 2h da manha):
#   0 2 * * * /opt/dom-despachante/scripts/backup.sh >> /var/log/dom-backup.log 2>&1
set -euo pipefail

SITE="${SITE:-despacho.dom.local}"
COMPOSE_DIR="${COMPOSE_DIR:-$HOME/frappe_docker}"
DESTINO="${DESTINO:-/var/backups/dom-despachante}"

mkdir -p "$DESTINO"
cd "$COMPOSE_DIR"

docker compose exec -T backend bench --site "$SITE" backup --with-files
docker compose exec -T backend sh -c 'tar -czf - /home/frappe/frappe-bench/sites/*/private/backups' \
  > "$DESTINO/backup-$(date +%Y%m%d-%H%M).tar.gz"

find "$DESTINO" -name 'backup-*.tar.gz' -mtime +30 -delete
echo "Backup concluido em $DESTINO"