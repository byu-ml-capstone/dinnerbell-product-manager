#!/usr/bin/env bash
# Local:  ./smoke-test.sh            builds and starts the stack, registers a throwaway user, creates a project.
# Remote: ./smoke-test.sh <url>      read-only checks; set SMOKE_USERNAME and SMOKE_PASSWORD to also check login.
#         It never creates data on a deployed instance (TEST-7).
set -euo pipefail
cd "$(dirname "$0")"

# Pick up APP_PORT etc. from .env, the same file docker compose reads.
if [ -f .env ]; then
    set -a
    . ./.env
    set +a
fi

if [ $# -eq 0 ]; then
    MODE=local
    BASE_URL="http://localhost:${APP_PORT:-8080}"
else
    MODE=remote
    BASE_URL="${1%/}"
fi

JAR="$(mktemp)"
trap 'rm -f "$JAR"' EXIT

if [ "$MODE" = "local" ]; then
    export SERVICE_FQDN_FRONTEND="$BASE_URL"
    echo "=== local mode: building + starting frontend, backend, db ==="
    docker compose down --remove-orphans >/dev/null 2>&1 || true
    docker compose up -d --build
else
    echo "=== remote mode: smoke-testing $BASE_URL ==="
fi

echo -n "waiting for /health "
for _ in $(seq 1 90); do
    if curl -sSf "$BASE_URL/health" >/dev/null 2>&1; then
        echo " ready"
        break
    fi
    echo -n "."
    sleep 1
done

echo
echo "=== GET / ==="
curl -fsS "$BASE_URL/" >/dev/null
echo "frontend ok"

echo "=== GET /health ==="
curl -fsS "$BASE_URL/health"
echo

echo "=== GET /api/projects without a session must be 401 ==="
status=$(curl -s -o /dev/null -w '%{http_code}' "$BASE_URL/api/projects")
[ "$status" = "401" ] || { echo "expected 401, got $status"; exit 1; }
echo "login required ok"

if [ "$MODE" = "local" ]; then
    USERNAME="smoke-$(date +%s)"
    echo "=== POST /api/auth/register ($USERNAME) ==="
    curl -fsS -c "$JAR" -X POST "$BASE_URL/api/auth/register" \
        -H 'Content-Type: application/json' \
        -d "{\"username\":\"$USERNAME\",\"name\":\"Smoke Test\",\"password\":\"smoke-test-password\"}" >/dev/null
    echo "registered"

    PROJECT_NAME="smoke-test-project-$(date +%s)"
    echo "=== POST /api/projects (frontend -> backend -> db write) ==="
    curl -fsS -b "$JAR" -X POST "$BASE_URL/api/projects" \
        -H 'Content-Type: application/json' \
        -d "{\"name\":\"$PROJECT_NAME\",\"description\":\"Created by smoke-test.sh\",\"team_member_ids\":[]}" >/dev/null
    echo "created $PROJECT_NAME"

    echo "=== GET /api/projects (db read-back) ==="
    curl -fsS -b "$JAR" "$BASE_URL/api/projects" | grep "$PROJECT_NAME" >/dev/null
    echo "read-back ok"
elif [ -n "${SMOKE_USERNAME:-}" ] && [ -n "${SMOKE_PASSWORD:-}" ]; then
    echo "=== POST /api/auth/login ($SMOKE_USERNAME) ==="
    curl -fsS -c "$JAR" -X POST "$BASE_URL/api/auth/login" \
        -H 'Content-Type: application/json' \
        -d "{\"username\":\"$SMOKE_USERNAME\",\"password\":\"$SMOKE_PASSWORD\"}" >/dev/null
    curl -fsS -b "$JAR" "$BASE_URL/api/projects" >/dev/null
    echo "login and project list ok"
else
    echo "SMOKE_USERNAME / SMOKE_PASSWORD not set: skipping the login check"
fi

echo
if [ "$MODE" = "local" ]; then
    echo "Local smoke test passed. The stack is still running at $BASE_URL."
    echo "Stop it with: docker compose down"
else
    echo "Remote smoke test passed: $BASE_URL"
fi
