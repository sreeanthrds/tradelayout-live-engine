#!/bin/bash

# Run Live Simulation Test
# This script starts the API server and runs the test client

echo "=================================="
echo "🚀 Live Simulation Test Runner"
echo "=================================="

# Check if server is already running
if curl -s http://localhost:8000/api/v1/backtest/status > /dev/null 2>&1; then
    echo "✅ API server is already running"
else
    echo "🔄 Starting API server..."
    python backtest_api_server.py &
    SERVER_PID=$!
    echo "   Server PID: $SERVER_PID"
    
    # Wait for server to be ready
    echo "   Waiting for server to start..."
    for i in {1..10}; do
        if curl -s http://localhost:8000/api/v1/backtest/status > /dev/null 2>&1; then
            echo "   ✅ Server is ready!"
            break
        fi
        sleep 1
    done
fi

echo ""
echo "=================================="
echo "🧪 Running Test Client"
echo "=================================="
echo ""

# Run test client
python test_live_simulation.py

echo ""
echo "=================================="
echo "✅ Test Complete"
echo "=================================="
