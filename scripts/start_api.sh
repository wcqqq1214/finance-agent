#!/bin/bash
# Start FastAPI from project root to ensure proper Python imports

# Source proxy configuration if it exists
PROXY_SCRIPT="$(dirname "$0")/setup_proxy.sh"
if [ -f "$PROXY_SCRIPT" ]; then
    source "$PROXY_SCRIPT"
fi

cd "$(dirname "$0")/.." && uv run uvicorn app.api.main:app --host 0.0.0.0 --port 8080 --reload
