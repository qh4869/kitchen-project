#!/usr/bin/env bash
# Daily DB backup. Run via crontab on the ECS:
#   0 3 * * * /home/<user>/kitchen-project/scripts/backup-db.sh

set -euo pipefail

BACKUP_DIR=/mnt/data/backups
mkdir -p "$BACKUP_DIR"

cd ~/kitchen-project
source .env

docker compose -f docker-compose.prod.yml exec -T postgres \
  pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" \
  | gzip > "$BACKUP_DIR/kitchen-$(date +%F).sql.gz"

# Keep last 7 days
find "$BACKUP_DIR" -name "kitchen-*.sql.gz" -mtime +7 -delete
