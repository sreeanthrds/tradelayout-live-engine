#!/usr/bin/env python3
"""
Show Tick Events at Square-Off Time

Demonstrates what tick_update events look like before, during, and after
the last square-off at 15:25:00.
"""

import json
from datetime import datetime

# Load actual trade data
with open('real_strategy_output/trades_daily.json') as f:
    trades_data = json.load(f)

# Last trade (square-off)
last_trade = trades_data['trades'][-1]

print("="*80)
print("📊 TICK EVENTS AT LAST SQUARE-OFF")
print("="*80)
print(f"Trade: {last_trade['symbol']}")
print(f"Entry: {last_trade['entry_price']} @ {last_trade['entry_time']}")
print(f"Exit: {last_trade['exit_price']} @ {last_trade['exit_time']}")
print(f"P&L: {last_trade['pnl']}")
print("="*80)
print()

# Simulate tick events before, during, and after square-off
tick_events = [
    {
        "time": "15:24:58",
        "description": "2 seconds before square-off",
        "event": {
            "timestamp": "2024-10-28T15:24:58+05:30",
            "current_time": "2024-10-28 15:24:58+05:30",
            "progress": {
                "ticks_processed": 21960,
                "total_ticks": 21962,
                "progress_percentage": 99.99
            },
            "active_nodes": ["entry-2", "entry-3", "square-off-1"],
            "pending_nodes": [],
            "completed_nodes_this_tick": [],
            "open_positions": [
                {
                    "position_id": "entry-2-pos1",
                    "symbol": "NIFTY:2024-11-07:OPT:24400:PE",
                    "side": "sell",
                    "quantity": 1,
                    "entry_price": 199.40,
                    "current_price": 220.80,  # Live price moving
                    "unrealized_pnl": -21.40,
                    "entry_time": "2024-10-28T12:52:16+05:30",
                    "duration_minutes": 152.70
                }
            ],
            "pnl_summary": {
                "realized_pnl": "-15.00",  # From previous 10 trades
                "unrealized_pnl": "-21.40",  # Open position P&L
                "total_pnl": "-36.40",
                "closed_trades": 10,
                "open_trades": 1,
                "winning_trades": 2,
                "losing_trades": 8,
                "win_rate": "20.00"
            },
            "ltp_store": {
                "NIFTY": 24412.50,
                "NIFTY:2024-11-07:OPT:24400:PE": 220.80,
                "NIFTY:2024-11-07:OPT:24250:CE": 268.30,
                "NIFTY:2024-11-07:OPT:24450:CE": 262.20
            },
            "candle_data": {
                "NIFTY": {
                    "timestamp": "2024-10-28T15:24:00+05:30",
                    "open": 24410.00,
                    "high": 24415.00,
                    "low": 24405.00,
                    "close": 24412.50,
                    "volume": 1234567
                }
            }
        }
    },
    {
        "time": "15:25:00",
        "description": "AT square-off - Position still open, exit order placed",
        "event": {
            "timestamp": "2024-10-28T15:25:00+05:30",
            "current_time": "2024-10-28 15:25:00+05:30",
            "progress": {
                "ticks_processed": 21962,
                "total_ticks": 21962,
                "progress_percentage": 100.00
            },
            "active_nodes": ["square-off-1"],
            "pending_nodes": [],
            "completed_nodes_this_tick": ["square-off-1"],  # Just executed
            "open_positions": [
                {
                    "position_id": "entry-2-pos1",
                    "symbol": "NIFTY:2024-11-07:OPT:24400:PE",
                    "side": "sell",
                    "quantity": 1,
                    "entry_price": 199.40,
                    "current_price": 221.25,  # Final exit price
                    "unrealized_pnl": -21.85,
                    "entry_time": "2024-10-28T12:52:16+05:30",
                    "duration_minutes": 152.73
                }
            ],
            "pnl_summary": {
                "realized_pnl": "-15.00",
                "unrealized_pnl": "-21.85",  # Updated with final price
                "total_pnl": "-36.85",
                "closed_trades": 10,
                "open_trades": 1,  # Still showing as open
                "winning_trades": 2,
                "losing_trades": 8,
                "win_rate": "20.00"
            },
            "ltp_store": {
                "NIFTY": 24413.00,
                "NIFTY:2024-11-07:OPT:24400:PE": 221.25,
                "NIFTY:2024-11-07:OPT:24250:CE": 268.40,
                "NIFTY:2024-11-07:OPT:24450:CE": 262.30
            },
            "candle_data": {
                "NIFTY": {
                    "timestamp": "2024-10-28T15:25:00+05:30",
                    "open": 24412.50,
                    "high": 24415.00,
                    "low": 24410.00,
                    "close": 24413.00,
                    "volume": 1234890
                }
            }
        }
    },
    {
        "time": "15:25:01",
        "description": "AFTER square-off - Position closed (in backtesting, fills immediately)",
        "event": {
            "timestamp": "2024-10-28T15:25:01+05:30",
            "current_time": "2024-10-28 15:25:01+05:30",
            "progress": {
                "ticks_processed": 21962,
                "total_ticks": 21962,
                "progress_percentage": 100.00
            },
            "active_nodes": [],
            "pending_nodes": [],
            "completed_nodes_this_tick": [],
            "open_positions": [],  # Position now closed!
            "pnl_summary": {
                "realized_pnl": "-36.85",  # Now includes this trade
                "unrealized_pnl": "0.00",  # No open positions
                "total_pnl": "-36.85",
                "closed_trades": 11,  # Updated
                "open_trades": 0,
                "winning_trades": 2,
                "losing_trades": 9,  # Updated
                "win_rate": "18.18"
            },
            "ltp_store": {
                "NIFTY": 24413.00,
                "NIFTY:2024-11-07:OPT:24400:PE": 221.25,
                "NIFTY:2024-11-07:OPT:24250:CE": 268.40,
                "NIFTY:2024-11-07:OPT:24450:CE": 262.30
            },
            "candle_data": {
                "NIFTY": {
                    "timestamp": "2024-10-28T15:25:00+05:30",
                    "open": 24412.50,
                    "high": 24415.00,
                    "low": 24410.00,
                    "close": 24413.00,
                    "volume": 1234890
                }
            }
        }
    }
]

# Display tick events
for i, tick_event in enumerate(tick_events, 1):
    print(f"\n{'='*80}")
    print(f"TICK EVENT #{i}: {tick_event['time']}")
    print(f"{'='*80}")
    print(f"📝 {tick_event['description']}")
    print()
    
    event = tick_event['event']
    
    # Progress
    print(f"⏱️  Progress: {event['progress']['ticks_processed']}/{event['progress']['total_ticks']} ({event['progress']['progress_percentage']:.2f}%)")
    
    # Nodes
    print(f"🎯 Active Nodes: {', '.join(event['active_nodes']) if event['active_nodes'] else 'None'}")
    print(f"✅ Completed This Tick: {', '.join(event['completed_nodes_this_tick']) if event['completed_nodes_this_tick'] else 'None'}")
    
    # Positions
    print(f"\n📍 Open Positions: {len(event['open_positions'])}")
    if event['open_positions']:
        for pos in event['open_positions']:
            print(f"   • {pos['symbol'].split(':')[-1]}: {pos['quantity']} @ {pos['entry_price']} → {pos['current_price']} (P&L: {pos['unrealized_pnl']:.2f})")
    else:
        print("   (All positions closed)")
    
    # P&L Summary
    pnl = event['pnl_summary']
    print(f"\n💰 P&L Summary:")
    print(f"   Realized: ₹{pnl['realized_pnl']}")
    print(f"   Unrealized: ₹{pnl['unrealized_pnl']}")
    print(f"   Total: ₹{pnl['total_pnl']}")
    print(f"   Trades: {pnl['closed_trades']} closed, {pnl['open_trades']} open")
    print(f"   Win/Loss: {pnl['winning_trades']}/{pnl['losing_trades']} ({pnl['win_rate']}%)")
    
    # LTP Store (sample)
    print(f"\n📊 LTP Store (sample):")
    for symbol, price in list(event['ltp_store'].items())[:3]:
        symbol_short = symbol.split(':')[-1] if ':' in symbol else symbol
        print(f"   {symbol_short}: {price:.2f}")
    
    # Candle Data
    print(f"\n🕯️  Current Candle (NIFTY):")
    candle = event['candle_data']['NIFTY']
    print(f"   OHLC: {candle['open']:.2f} / {candle['high']:.2f} / {candle['low']:.2f} / {candle['close']:.2f}")
    
    # JSON representation (what UI receives)
    print(f"\n📦 JSON Event (as UI receives via SSE):")
    print("```json")
    print(json.dumps({
        "event": "tick_update",
        "data": {
            "session_id": "sim-5708424d",
            "tick_state": event
        }
    }, indent=2, default=str)[:500] + "...")
    print("```")

print("\n" + "="*80)
print("✅ COMPLETE FLOW DEMONSTRATED")
print("="*80)
print()
print("📌 Key Observations:")
print("   1. Before square-off: Position open with unrealized P&L")
print("   2. At square-off: Exit order placed, position still shows as open")
print("   3. After square-off: Position closed, P&L moved to realized")
print("   4. LTP store continuously updated with live prices")
print("   5. Candle data reflects market movement")
print("   6. Progress shows 100% completion at end")
print()
print("🎯 UI updates dashboard in real-time with each tick_update event")
print("="*80)
