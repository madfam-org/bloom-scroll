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

echo "Production smoke checks passed"
