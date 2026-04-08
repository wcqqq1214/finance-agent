#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

if ! command -v docker >/dev/null 2>&1; then
  echo "Error: required command 'docker' is not available." >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "Error: 'docker compose' is not available. Install Docker Desktop or Docker Engine with Compose support." >&2
  exit 1
fi

cd "${PROJECT_ROOT}"
docker compose down --remove-orphans
