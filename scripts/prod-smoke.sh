#!/usr/bin/env bash
set -euo pipefail

WEB_URL="${WEB_URL:-https://almanac.solar}"
API_URL="${API_URL:-https://api.almanac.solar}"

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

echo "Checking web shell: ${WEB_URL}"
curl -fsS "${WEB_URL}" -o "${tmpdir}/web.html"
grep -q "Almanac" "${tmpdir}/web.html"

echo "Checking API health: ${API_URL}/health"
curl -fsS "${API_URL}/health" -o "${tmpdir}/health.json"
grep -q '"status":"healthy"' "${tmpdir}/health.json"
grep -q '"database":{"status":"ok"' "${tmpdir}/health.json"

echo "Checking finite-feed completion response"
curl -fsS "${API_URL}/api/v1/feed?read_count=20" -o "${tmpdir}/completion.json"
grep -q '"message":"The Garden is Watered."' "${tmpdir}/completion.json"

# The completion path above returns early without touching the database, so
# it stayed green through the 2026-07-16 feed outage. Exercise the real
# DB-backed feed path too.
echo "Checking feed serves the DB-backed path"
curl -fsS "${API_URL}/api/v1/feed?limit=1" -o "${tmpdir}/feed.json"
grep -q '"cards"' "${tmpdir}/feed.json"

echo "Checking schema is at alembic head"
curl -fsS "${API_URL}/health" -o "${tmpdir}/health2.json"
python3 -c "import json,sys; d=json.load(open('${tmpdir}/health2.json')); sys.exit(0 if d['checks'].get('migrations',{}).get('status')=='ok' else 1)" || {
  echo "ERROR: schema is not at alembic head (see /health checks.migrations)" >&2
  exit 1
}

echo "Checking production bundle API base"
curl -fsS "${WEB_URL}/main.dart.js" -o "${tmpdir}/main.dart.js"
grep -q "https://api.almanac.solar/api/v1" "${tmpdir}/main.dart.js"
if grep -q "http://localhost:8000/api/v1" "${tmpdir}/main.dart.js"; then
  echo "ERROR: production bundle contains leaked local API base" >&2
  exit 1
fi

echo "Checking API docs are hidden"
docs_status="$(curl -sS -o /dev/null -w "%{http_code}" "${API_URL}/docs")"
openapi_status="$(curl -sS -o /dev/null -w "%{http_code}" "${API_URL}/openapi.json")"
if [[ "${docs_status}" == "200" || "${openapi_status}" == "200" ]]; then
  echo "ERROR: production API docs are public (/docs=${docs_status}, /openapi.json=${openapi_status})" >&2
  exit 1
fi

echo "Checking liveness endpoint"
curl -fsS "${API_URL}/livez" -o "${tmpdir}/livez.json"
grep -q '"status":"alive"' "${tmpdir}/livez.json"

echo "Checking write endpoints reject unauthenticated callers (audit D1)"
ingest_status="$(curl -sS -o /dev/null -w "%{http_code}" -X POST "${API_URL}/api/v1/ingest/owid")"
track_status="$(curl -sS -o /dev/null -w "%{http_code}" -X POST -H 'Content-Type: application/json' \
  -d '{"user_id":"smoke","card_id":"smoke","action":"view"}' "${API_URL}/api/v1/interactions/track")"
if [[ "${ingest_status}" != "401" || "${track_status}" != "401" ]]; then
  echo "ERROR: write endpoints are open (ingest=${ingest_status}, track=${track_status}; expected 401)" >&2
  exit 1
fi

echo "Production smoke checks passed"
