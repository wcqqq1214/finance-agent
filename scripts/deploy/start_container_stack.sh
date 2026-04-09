#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ENV_FILE="${PROJECT_ROOT}/.env"

require_command() {
  local command_name="$1"
  if ! command -v "${command_name}" >/dev/null 2>&1; then
    echo "Error: required command '${command_name}' is not available." >&2
    exit 1
  fi
}

require_compose() {
  if ! docker compose version >/dev/null 2>&1; then
    echo "Error: 'docker compose' is not available. Install Docker Desktop or Docker Engine with Compose support." >&2
    exit 1
  fi
}

main() {
  if [[ ! -f "${ENV_FILE}" ]]; then
    echo "Error: .env is missing. Copy .env.example to .env and add the required keys before starting the container stack." >&2
    exit 1
  fi

  require_command docker
  require_compose

  cd "${PROJECT_ROOT}"
  docker compose up -d --build
}

main "$@"
