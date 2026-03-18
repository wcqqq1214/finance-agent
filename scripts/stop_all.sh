#!/bin/bash
# Stop all Finance Agent services

echo "Stopping Finance Agent services..."

# Stop frontend (Next.js on port 3000)
if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "Stopping frontend (port 3000)..."
    kill $(lsof -t -i:3000) 2>/dev/null || true
fi

# Stop FastAPI (port 8080)
if lsof -Pi :8080 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "Stopping FastAPI (port 8080)..."
    kill $(lsof -t -i:8080) 2>/dev/null || true
fi

# Stop MCP servers
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$SCRIPT_DIR/stop_mcp_servers.sh" ]; then
    bash "$SCRIPT_DIR/stop_mcp_servers.sh"
else
    # Fallback: stop by port
    if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "Stopping MCP Market Data (port 8000)..."
        kill $(lsof -t -i:8000) 2>/dev/null || true
    fi
    if lsof -Pi :8001 -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "Stopping MCP News Search (port 8001)..."
        kill $(lsof -t -i:8001) 2>/dev/null || true
    fi
fi

echo "All services stopped."
