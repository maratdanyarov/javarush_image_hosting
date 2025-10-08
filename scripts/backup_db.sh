#!/usr/bin/env bash
set -Eeuo pipefail

CONTAINER_NAME="${PG_CONTAINER_NAME:-postgres_container}"
DB_NAME="${PG_DB:-images_db}"
DB_USER="${PG_USER:-postgres}"
BACKUP_DIR="${BACKUP_DIR:-backups}"

mkdir -p "${BACKUP_DIR}"
ts=$(date +'%F_%H%M%S')
outfile="${BACKUP_DIR}/backup_${ts}.sql"

if docker exec -t "${CONTAINER_NAME}" pg_dump -U "${DB_USER}" "${DB_NAME}" > "${outfile}"; then
  echo "✅ Бэкап создан: ${outfile}"
else
  echo "❌ Ошибка: не удалось создать бэкап." >&2
  exit 1
fi