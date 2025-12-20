#!/bin/bash
# Restart Backtest API Server
# Usage: ./restart_backtest_api.sh

cd /Users/sreenathreddy/Downloads/UniTrader-project/backtesting_project/tradelayout-engine

echo "Stopping any existing backtest API server..."
pkill -f backtest_file_api_server.py 2>/dev/null || true
sleep 1

echo "Starting backtest API server..."
nohup python backtest_file_api_server.py > backtest_api.log 2>&1 &

sleep 2

# Check if server started
if ps aux | grep -v grep | grep backtest_file_api_server.py > /dev/null; then
    PID=$(ps aux | grep -v grep | grep backtest_file_api_server.py | awk '{print $2}')
    echo "✅ Backtest API server started successfully!"
    echo "   PID: $PID"
    echo "   Logs: backtest_api.log"
    echo ""
    echo "To view logs: tail -f backtest_api.log"
    echo "To stop server: pkill -f backtest_file_api_server.py"
else
    echo "❌ Failed to start server. Check backtest_api.log for errors."
    exit 1
fi
