#!/usr/bin/env bash
# Deploy (or update) kitchen-project on the ECS host.
#
# Usage:
#   ECS_HOST=root@1.2.3.4 bash scripts/deploy.sh
#
# Requires: SSH key auth to the ECS already configured.

set -euo pipefail

ECS_HOST="${ECS_HOST:?Set ECS_HOST=user@ip in env or .env.local}"

ssh "$ECS_HOST" <<'EOF'
set -euo pipefail
cd ~/kitchen-project
git pull --ff-only
docker compose -f docker-compose.prod.yml up -d --build
# Run migrations inside the freshly built api container
docker compose -f docker-compose.prod.yml exec -T api uv run alembic upgrade head
docker image prune -f  # clean dangling images from previous builds
EOF

echo "Deploy complete. Verify at http://<ECS_IP>/"
