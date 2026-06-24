#!/usr/bin/env bash
# Deploy (or update) kitchen-project on this ECS host.
# Run directly on the ECS (already SSH'd in) from anywhere:
#   bash /path/to/kitchen-project/scripts/deploy.sh
#   bash scripts/deploy.sh  (if cwd is project root)
#   bash ~/kitchen-project/scripts/deploy.sh

set -euo pipefail

# Find project root from this script's location (so cwd doesn't matter)
cd "$(dirname "${BASH_SOURCE[0]}")/.."

git pull --ff-only
docker compose -f docker-compose.prod.yml up -d --build
# Run migrations inside the freshly built api container
docker compose -f docker-compose.prod.yml exec -T api uv run alembic upgrade head
docker image prune -f  # clean dangling images from previous builds

echo "Deploy complete. Verify at http://$(curl -s ifconfig.me)/"
