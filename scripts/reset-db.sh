#!/usr/bin/env bash
# Factory reset: wipe ALL data (DB tables + uploaded images) and recreate
# empty schema via migrations.
#
# ⚠️  DESTRUCTIVE — data loss. Confirmation required.
#
# Usage on ECS: bash scripts/reset-db.sh
# (Run from anywhere; script locates project root via BASH_SOURCE.)

set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

echo "⚠️  This will:"
echo "   - Drop the postgres volume (all DB rows gone)"
echo "   - Drop the uploads volume (all receipt photos gone)"
echo "   - Rebuild containers + re-run migrations"
echo "   (Image builds are cached; only data is wiped)"
echo

read -rp "Type 'reset' to proceed (anything else aborts): " ans
[ "$ans" = "reset" ] || { echo "Aborted."; exit 1; }

echo "→ Stopping containers + removing volumes..."
docker compose -f docker-compose.prod.yml down -v

echo "→ Starting fresh containers..."
docker compose -f docker-compose.prod.yml up -d

echo "→ Waiting for postgres healthy..."
for i in {1..30}; do
    if docker compose -f docker-compose.prod.yml exec -T postgres \
         pg_isready -U kitchen -d kitchen >/dev/null 2>&1; then
        echo "  postgres ready"
        break
    fi
    sleep 1
done

echo "→ Running migrations (creates empty schema)..."
docker compose -f docker-compose.prod.yml exec -T api uv run alembic upgrade head

echo
echo "✓ Factory reset complete. DB is empty, schema is at head."
echo "  Verify at http://<ECS_PUBLIC_IP>/ — should show 0 records everywhere."
