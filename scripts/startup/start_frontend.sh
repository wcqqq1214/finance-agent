#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
FRONTEND_DIR="$SCRIPT_DIR/../frontend"
cd "$FRONTEND_DIR" && npm run dev
