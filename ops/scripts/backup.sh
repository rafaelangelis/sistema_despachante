#!/usr/bin/env bash
# Backup do site Frappe: banco + arquivos publicos/privados + site_config (encryption_key).
# Cada execucao gera UMA pasta datada em $DESTINO e apaga as com mais de $RETENCAO_DIAS dias.
#
# Uso:   SITE=despacho.dom.local ./backup.sh
# Cron:  0 2 * * * SITE=despacho.dom.local COMPOSE_DIR=/home/USUARIO/frappe_docker /home/USUARIO/sistema_despachante/ops/scripts/backup.sh >> /var/log/dom-backup.log 2>&1
#
# Restaurar: ops/scripts/restore.sh <pasta-do-backup> <site>
set -euo pipefail

SITE="${SITE:-despacho.dom.local}"
COMPOSE_DIR="${COMPOSE_DIR:-$HOME/frappe_docker}"
PROJETO="${PROJETO:-dom}"
DESTINO="${DESTINO:-/var/backups/dom-despachante}"
RETENCAO_DIAS="${RETENCAO_DIAS:-30}"
DOCKER="${DOCKER:-docker}"

cd "$COMPOSE_DIR"
# --project-name e obrigatorio: sem ele o compose procura o projeto "frappe_docker" e nao acha o backend.
# O COMPOSE_FILE do .env (RUNBOOK, Etapa D) traz os overrides.
dc() { $DOCKER compose --project-name "$PROJETO" "$@"; }

CARIMBO="$(date +%Y%m%d-%H%M%S)"
TMP="/tmp/dom-backup-$CARIMBO"
PASTA="$DESTINO/$SITE/$CARIMBO"

mkdir -p "$PASTA"
dc exec -T backend bench --site "$SITE" backup --with-files --backup-path "$TMP" >/dev/null
# tar em stream (e nao "compose cp"): os arquivos nascem com o dono de quem roda o script
dc exec -T backend tar -C "$TMP" -cf - . | tar -C "$PASTA" -xf -
dc exec -T backend rm -rf "$TMP"

# o *-site_config_backup.json do bench ja contem a encryption_key; guardamos tambem a parte, por clareza
dc exec -T backend sh -c "cd sites/$SITE && python3 -c 'import json;print(json.load(open(\"site_config.json\"))[\"encryption_key\"])'" \
	> "$PASTA/encryption_key.txt"
chmod -R go-rwx "$PASTA"

ls "$PASTA" | grep -q 'database.sql.gz$' || { echo "ERRO: backup sem banco em $PASTA" >&2; exit 1; }

find "$DESTINO/$SITE" -mindepth 1 -maxdepth 1 -type d -mtime +"$RETENCAO_DIAS" -exec rm -rf {} +
echo "Backup concluido: $PASTA ($(du -sh "$PASTA" | cut -f1))"
