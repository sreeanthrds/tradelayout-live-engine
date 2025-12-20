#!/usr/bin/env python3
"""
Event Simulator for Smoke Test

Simulates a live backtesting engine feeding events to sse_manager
at high speed (5000x) to demonstrate UI data flow.

This generates realistic node_events, trade_updates, and tick_updates.
"""

import asyncio
import json
import sys
import time
from datetime import datetime, timedelta
from live_simulation_sse import sse_manager

async def simulate_events(session_id, num_ticks=1000, speed_multiplier=5000):
    """Simulate backtest events for a session"""
    
    session = sse_manager.get_session(session_id)
    if not session:
        print(f"[ERROR] Session {session_id} not found")
        return
    
    print(f"[SIMULATOR] Starting simulation for {session_id}")
    print(f"[SIMULATOR] Ticks: {num_ticks}, Speed: {speed_multiplier}x")
    
    # Starting time
    current_time = datetime(2024, 12, 14, 9, 15, 0)
    
    # Simulate tick-by-tick execution
    for tick in range(num_ticks):
        # Update tick state
        session.tick_state.update({
            "timestamp": current_time.isoformat(),
            "current_time": current_time.strftime("%Y-%m-%d %H:%M:%S+05:30"),
            "progress": {
                "ticks_processed": tick + 1,
                "total_ticks": num_ticks,
                "progress_percentage": ((tick + 1) / num_ticks) * 100
            },
            "active_nodes": ["entry-condition-1"],
            "pending_nodes": [],
            "completed_nodes_this_tick": [],
            "open_positions": [],
            "pnl_summary": {
                "realized_pnl": "0.00",
                "unrealized_pnl": "0.00",
                "total_pnl": "0.00",
                "closed_trades": 0,
                "open_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": "0.00"
            },
            "ltp_store": {
                "NIFTY": 25000.0 + (tick * 0.5),
                "BANKNIFTY": 52000.0 + (tick * 1.2)
            },
            "candle_data": {
                "NIFTY": {
                    "timestamp": current_time.isoformat(),
                    "open": 25000.0,
                    "high": 25000.0 + (tick * 0.6),
                    "low": 25000.0 - (tick * 0.3),
                    "close": 25000.0 + (tick * 0.5),
                    "volume": 1000000 + tick * 1000
                }
            }
        })
        
        # Simulate entry at tick 100
        if tick == 100:
            execution_id = f"exec-{tick}-entry"
            event_payload = {
                "execution_id": execution_id,
                "node_id": "entry-condition-1",
                "node_type": "EntryNode",
                "timestamp": current_time.isoformat(),
                "event_type": "logic_completed",
                "evaluation_data": {
                    "action": "entry_placed",
                    "symbol": "NIFTY28DEC2525000CE",
                    "quantity": 50,
                    "price": 150.00
                }
            }
            session.add_node_event(execution_id, event_payload)
            
            # Update positions
            session.tick_state["open_positions"] = [{
                "position_id": "pos-001",
                "symbol": "NIFTY28DEC2525000CE",
                "exchange": "NFO",
                "quantity": 50,
                "entry_price": 150.00,
                "current_price": 150.00,
                "unrealized_pnl": 0.00,
                "entry_time": current_time.isoformat()
            }]
            session.tick_state["pnl_summary"]["open_trades"] = 1
            
            print(f"[SIMULATOR] Tick {tick}: Entry placed - NIFTY CE @150")
        
        # Update position P&L if open
        if tick > 100 and tick < 500:
            current_price = 150.00 + ((tick - 100) * 0.1)
            unrealized_pnl = (current_price - 150.00) * 50
            
            session.tick_state["open_positions"][0].update({
                "current_price": current_price,
                "unrealized_pnl": unrealized_pnl
            })
            session.tick_state["pnl_summary"]["unrealized_pnl"] = f"{unrealized_pnl:.2f}"
            session.tick_state["pnl_summary"]["total_pnl"] = f"{unrealized_pnl:.2f}"
        
        # Simulate exit at tick 500
        if tick == 500:
            execution_id = f"exec-{tick}-exit"
            exit_price = 190.00
            pnl = (exit_price - 150.00) * 50
            
            event_payload = {
                "execution_id": execution_id,
                "node_id": "exit-condition-1",
                "node_type": "ExitNode",
                "timestamp": current_time.isoformat(),
                "event_type": "logic_completed",
                "evaluation_data": {
                    "action": "exit_placed",
                    "symbol": "NIFTY28DEC2525000CE",
                    "quantity": 50,
                    "price": exit_price
                }
            }
            session.add_node_event(execution_id, event_payload)
            
            # Add trade
            trade = {
                "trade_id": "trade-001",
                "symbol": "NIFTY28DEC2525000CE",
                "entry_time": datetime(2024, 12, 14, 9, 15, 0).isoformat(),
                "exit_time": current_time.isoformat(),
                "entry_price": 150.00,
                "exit_price": exit_price,
                "quantity": 50,
                "pnl": f"{pnl:.2f}",
                "pnl_percentage": f"{((exit_price - 150.00) / 150.00 * 100):.2f}"
            }
            session.add_trade(trade)
            
            # Clear positions
            session.tick_state["open_positions"] = []
            session.tick_state["pnl_summary"] = {
                "realized_pnl": f"{pnl:.2f}",
                "unrealized_pnl": "0.00",
                "total_pnl": f"{pnl:.2f}",
                "closed_trades": 1,
                "open_trades": 0,
                "winning_trades": 1,
                "losing_trades": 0,
                "win_rate": "100.00"
            }
            
            print(f"[SIMULATOR] Tick {tick}: Exit placed - P&L: ₹{pnl:.2f}")
        
        # Queue tick_update event
        await session.event_queue.put({
            "type": "tick_update",
            "data": session.tick_state.copy()
        })
        
        # Advance time
        current_time += timedelta(seconds=1)
        
        # Speed control (5000x means 5000 ticks per second = 0.0002s per tick)
        await asyncio.sleep(1.0 / speed_multiplier)
        
        # Print progress every 100 ticks
        if (tick + 1) % 100 == 0:
            print(f"[SIMULATOR] Processed {tick + 1}/{num_ticks} ticks")
    
    print(f"[SIMULATOR] Simulation complete - {num_ticks} ticks processed")

async def main():
    if len(sys.argv) < 2:
        print("Usage: python simulate_live_events.py <session_id> [num_ticks] [speed_multiplier]")
        sys.exit(1)
    
    session_id = sys.argv[1]
    num_ticks = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
    speed_multiplier = float(sys.argv[3]) if len(sys.argv) > 3 else 5000.0
    
    start_time = time.time()
    
    await simulate_events(session_id, num_ticks, speed_multiplier)
    
    elapsed = time.time() - start_time
    ticks_per_sec = num_ticks / elapsed if elapsed > 0 else 0
    
    print(f"\n[STATS] Total time: {elapsed:.2f}s")
    print(f"[STATS] Speed: {ticks_per_sec:.1f} ticks/sec ({speed_multiplier}x target)")

if __name__ == "__main__":
    asyncio.run(main())
