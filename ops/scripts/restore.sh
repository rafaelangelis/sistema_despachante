#!/usr/bin/env bash
# Restaura um backup feito por backup.sh num site (novo ou existente).
#
# Uso: DB_ROOT_PASSWORD=... ./restore.sh <pasta-do-backup> <site>
#   - se o site nao existir, ele e criado;
#   - se existir, o banco e os arquivos dele sao SUBSTITUIDOS pelos do backup.
# Depois do restore a encryption_key do backup e aplicada (senhas salvas, como a chave da
# Evolution, voltam a ser legiveis) e o bench migrate e executado.
set -euo pipefail

PASTA="${1:?informe a pasta do backup}"
SITE="${2:?informe o site de destino}"
COMPOSE_DIR="${COMPOSE_DIR:-$HOME/frappe_docker}"
PROJETO="${PROJETO:-dom}"
DOCKER="${DOCKER:-docker}"
: "${DB_ROOT_PASSWORD:?defina DB_ROOT_PASSWORD (o DB_PASSWORD do .env do frappe_docker)}"

PASTA="$(cd "$PASTA" && pwd)"
DB="$(ls "$PASTA"/*-database.sql.gz | head -1)"
PUB="$(ls "$PASTA"/*-files.tar 2>/dev/null | grep -v private | head -1 || true)"
PRIV="$(ls "$PASTA"/*-private-files.tar 2>/dev/null | head -1 || true)"
CHAVE="$(cat "$PASTA/encryption_key.txt")"

cd "$COMPOSE_DIR"
dc() { $DOCKER compose --project-name "$PROJETO" "$@"; }
B() { dc exec -T backend bench "$@"; }

TMP="/tmp/dom-restore-$$"
dc exec -T backend mkdir -p "$TMP"
dc cp "$PASTA/." "backend:$TMP/"

if ! dc exec -T backend test -d "sites/$SITE"; then
	echo "Criando o site $SITE..."
	B new-site "$SITE" --mariadb-user-host-login-scope='%' --admin-password "$(openssl rand -hex 12)" \
		--db-root-username root --db-root-password "$DB_ROOT_PASSWORD" >/dev/null
fi

ARGS=()
[ -n "$PUB" ] && ARGS+=(--with-public-files "$TMP/$(basename "$PUB")")
[ -n "$PRIV" ] && ARGS+=(--with-private-files "$TMP/$(basename "$PRIV")")

echo "Restaurando $(basename "$DB") em $SITE..."
B --site "$SITE" --force restore "$TMP/$(basename "$DB")" "${ARGS[@]}" \
	--db-root-username root --db-root-password "$DB_ROOT_PASSWORD"
B --site "$SITE" set-config encryption_key "$CHAVE"
B --site "$SITE" migrate >/dev/null
dc exec -T backend rm -rf "$TMP"
echo "Restore concluido em $SITE. A senha do Administrator e a do backup."
