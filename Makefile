backup:
	@./scripts/backup_db.sh

restore:
	@./scripts/restore_db.sh $(FILE)

list-backups:
	@ls -lh backups/*.sql 2>/dev/null || echo "Нет файлов бэкапов"