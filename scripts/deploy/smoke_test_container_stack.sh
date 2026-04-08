#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

wait_for_http_endpoint() {
  local url="$1"
  local attempts="${2:-60}"
  local delay_seconds="${3:-2}"

  for ((attempt = 1; attempt <= attempts; attempt += 1)); do
    if curl --fail --silent --show-error "${url}" >/dev/null; then
      echo "Healthy: ${url}"
      return 0
    fi

    sleep "${delay_seconds}"
  done

  echo "Error: timed out waiting for ${url}" >&2
  return 1
}

wait_for_redis() {
  local attempts="${1:-30}"
  local delay_seconds="${2:-2}"

  for ((attempt = 1; attempt <= attempts; attempt += 1)); do
    if docker compose exec -T redis redis-cli ping 2>/dev/null | grep -q "PONG"; then
      echo "Healthy: redis://localhost:6379"
      return 0
    fi

    sleep "${delay_seconds}"
  done

  echo "Error: timed out waiting for Redis health." >&2
  return 1
}

main() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "Error: required command 'docker' is not available." >&2
    exit 1
  fi

  if ! docker compose version >/dev/null 2>&1; then
    echo "Error: 'docker compose' is not available. Install Docker Desktop or Docker Engine with Compose support." >&2
    exit 1
  fi

  if ! command -v curl >/dev/null 2>&1; then
    echo "Error: required command 'curl' is not available." >&2
    exit 1
  fi

  cd "${PROJECT_ROOT}"

  for endpoint in \
    "http://localhost:3000/" \
    "http://localhost:8080/api/health" \
    "http://localhost:8000/health" \
    "http://localhost:8001/health"; do
    wait_for_http_endpoint "${endpoint}"
  done

  wait_for_redis
  docker compose ps
}

main "$@"
