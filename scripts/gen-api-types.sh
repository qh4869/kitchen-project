#!/usr/bin/env bash
set -euo pipefail

API_URL="${API_URL:-http://localhost:3000}"
OUT="packages/api-types/src/index.ts"
TMP="$(mktemp -t openapi.XXXXXX.json)"

trap 'rm -f "$TMP"' EXIT

echo "Fetching OpenAPI spec from $API_URL/openapi.json ..."
curl -fsS "$API_URL/openapi.json" -o "$TMP"

echo "Generating TypeScript types..."
npx openapi-typescript "$TMP" -o "$OUT"

echo "Wrote $OUT"
