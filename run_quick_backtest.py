"""Quick backtest runner for strategy 5708424d-5962-4629-978c-05b3a174e104"""
import os
import sys
from datetime import datetime

# Set environment variables
os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'

# ClickHouse local configuration
os.environ['CLICKHOUSE_HOST'] = 'localhost'
os.environ['CLICKHOUSE_PORT'] = '8123'
os.environ['CLICKHOUSE_USER'] = 'default'
os.environ['CLICKHOUSE_PASSWORD'] = ''
os.environ['CLICKHOUSE_DATABASE'] = 'tradelayout'
os.environ['CLICKHOUSE_SECURE'] = 'false'

from show_dashboard_data import run_dashboard_backtest, dashboard_data

# Configuration
STRATEGY_ID = "5708424d-5962-4629-978c-05b3a174e104"
BACKTEST_DATE = "2024-10-29"

print("=" * 100)
print("🚀 RUNNING BACKTEST")
print("=" * 100)
print(f"Strategy ID: {STRATEGY_ID}")
print(f"Date: {BACKTEST_DATE}")
print()

try:
    # Run backtest
    result = run_dashboard_backtest(STRATEGY_ID, BACKTEST_DATE)
    
    print("\n" + "=" * 100)
    print("📊 BACKTEST RESULTS")
    print("=" * 100)
    
    # Get summary data
    summary = dashboard_data.get('summary', {})
    positions = dashboard_data.get('positions', [])
    
    print(f"\n✅ Total Positions: {len(positions)}")
    print(f"✅ Total P&L: ₹{summary.get('total_pnl', 0):,.2f}")
    print(f"✅ Win Rate: {summary.get('win_rate', 0):.1f}%")
    
    # Show position details
    if positions:
        print(f"\n" + "=" * 100)
        print(f"📌 POSITION DETAILS ({len(positions)} positions)")
        print("=" * 100)
        
        # Group by entry node
        entry_nodes = {}
        for pos in positions:
            entry_node = pos.get('entry_node', 'Unknown')
            if entry_node not in entry_nodes:
                entry_nodes[entry_node] = []
            entry_nodes[entry_node].append(pos)
        
        for entry_node, node_positions in entry_nodes.items():
            print(f"\n{entry_node}: {len(node_positions)} positions")
            for idx, pos in enumerate(node_positions, 1):
                entry_time = pos.get('entry_time', 'N/A')
                exit_time = pos.get('exit_time', 'N/A')
                pnl = pos.get('pnl', 0)
                symbol = pos.get('symbol', 'N/A')
                side = pos.get('side', 'N/A')
                entry_price = pos.get('entry_price', 0)
                exit_price = pos.get('exit_price', 0)
                
                # Manual P&L calculation
                if side.upper() == 'BUY':
                    manual_pnl = exit_price - entry_price
                elif side.upper() == 'SELL':
                    manual_pnl = entry_price - exit_price
                else:
                    manual_pnl = 0
                
                print(f"  {idx}. {symbol}")
                print(f"      Side: {side} | Entry: ₹{entry_price:.2f} | Exit: ₹{exit_price:.2f}")
                print(f"      Time: {entry_time} → {exit_time}")
                print(f"      P&L (system): ₹{pnl:.2f} | P&L (manual): ₹{manual_pnl:.2f}")
    
    print("\n" + "=" * 100)
    print("✅ BACKTEST COMPLETE")
    print("=" * 100)
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
