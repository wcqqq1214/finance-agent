#!/bin/bash
# Test script to verify all services are working

echo "Testing Finance Agent Services..."
echo ""

# Test MCP Market Data
echo "1. Testing MCP Market Data (http://localhost:8000)..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "   ✓ MCP Market Data is running"
else
    echo "   ✗ MCP Market Data is not responding"
fi

# Test MCP News Search
echo "2. Testing MCP News Search (http://localhost:8001)..."
if curl -s http://localhost:8001/health > /dev/null 2>&1; then
    echo "   ✓ MCP News Search is running"
else
    echo "   ✗ MCP News Search is not responding"
fi

# Test FastAPI
echo "3. Testing FastAPI (http://localhost:8080)..."
if curl -s http://localhost:8080/api/health > /dev/null 2>&1; then
    echo "   ✓ FastAPI is running"
    echo "   Response: $(curl -s http://localhost:8080/api/health | jq -r .status)"
else
    echo "   ✗ FastAPI is not responding"
fi

# Test Frontend
echo "4. Testing Frontend (http://localhost:3000)..."
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo "   ✓ Frontend is running"
else
    echo "   ✗ Frontend is not responding"
fi

echo ""
echo "Test complete!"
