#!/bin/bash
# Start FastAPI from project root to ensure proper Python imports
cd "$(dirname "$0")/.." && uv run uvicorn app.api.main:app --host 0.0.0.0 --port 8080 --reload
