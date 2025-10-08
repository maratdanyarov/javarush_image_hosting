#!/usr/bin/env bash
set -Eeuo pipefail

CONTAINER_NAME="${PG_CONTAINER_NAME:-postgres_container}"
DB_NAME="${PG_DB:-images_db}"
DB_USER="${PG_USER:-postgres}"

BACKUP_FILE="${1:-}"
if [[ -z "${BACKUP_FILE}" || ! -f "${BACKUP_FILE}" ]]; then
  echo "Использование: $0 backups/backup_YYYY-MM-DD_HHMMSS.sql" >&2
  exit 2
fi

if docker exec -i "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}" < "${BACKUP_FILE}"; then
  echo "✅ Восстановление завершено: ${BACKUP_FILE}"
else
  echo "❌ Ошибка: не удалось восстановить БД." >&2
  exit 1
fi