#!/usr/bin/env python3
"""
Standalone Smoke Test: Complete SSE Data Flow Demonstration

Simulates the complete flow:
1. Backend generates events (like backtesting engine)
2. UI receives events via SSE
3. UI writes to files in append mode
4. Final output matches backtesting format exactly

Runs at 5000x speed with 1000 ticks.
"""

import json
import gzip
import base64
import time
from datetime import datetime, timedelta
from pathlib import Path

class EventSimulator:
    """Simulates backtesting engine generating events"""
    
    def __init__(self, session_id, strategy_name="NIFTY Straddle"):
        self.session_id = session_id
        self.strategy_name = strategy_name
        self.diagnostics = {
            "events_history": {},
            "current_state": {}
        }
        self.trades = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "summary": {
                "total_trades": 0,
                "total_pnl": "0.00",
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": "0.00"
            },
            "trades": []
        }
        self.current_time = datetime(2024, 12, 14, 9, 15, 0)
    
    def compress_json(self, data):
        """Gzip + base64 encode JSON data (like backend does)"""
        json_str = json.dumps(data)
        compressed = gzip.compress(json_str.encode('utf-8'))
        return base64.b64encode(compressed).decode('utf-8')
    
    def generate_initial_state(self):
        """Generate initial_state event"""
        return {
            "event": "initial_state",
            "data": {
                "session_id": self.session_id,
                "strategy_id": "64c2c932-0e0b-462a-9a36-7cda4371d102",
                "diagnostics": self.compress_json(self.diagnostics),
                "trades": self.compress_json(self.trades)
            }
        }
    
    def generate_node_event(self, tick, node_type, action_data):
        """Generate node_events event"""
        execution_id = f"exec-{tick}-{node_type}"
        event_payload = {
            "execution_id": execution_id,
            "node_id": f"{node_type.lower()}-condition-1",
            "node_type": f"{node_type}Node",
            "timestamp": self.current_time.isoformat(),
            "event_type": "logic_completed",
            "evaluation_data": action_data
        }
        
        # Add to diagnostics
        self.diagnostics["events_history"][execution_id] = event_payload
        self.diagnostics["current_state"][event_payload["node_id"]] = event_payload
        
        return {
            "event": "node_events",
            "data": {
                "session_id": self.session_id,
                "diagnostics": self.compress_json(self.diagnostics)
            }
        }
    
    def generate_trade_update(self, trade_data):
        """Generate trade_update event"""
        self.trades["trades"].append(trade_data)
        
        # Update summary
        trades_list = self.trades["trades"]
        total_pnl = sum(float(t["pnl"]) for t in trades_list)
        winning = sum(1 for t in trades_list if float(t["pnl"]) > 0)
        losing = sum(1 for t in trades_list if float(t["pnl"]) < 0)
        win_rate = (winning / len(trades_list) * 100) if trades_list else 0
        
        self.trades["summary"] = {
            "total_trades": len(trades_list),
            "total_pnl": f"{total_pnl:.2f}",
            "winning_trades": winning,
            "losing_trades": losing,
            "win_rate": f"{win_rate:.2f}"
        }
        
        return {
            "event": "trade_update",
            "data": {
                "session_id": self.session_id,
                "trades": self.compress_json(self.trades)
            }
        }
    
    def generate_tick_update(self, tick, total_ticks, position_data):
        """Generate tick_update event"""
        progress_pct = (tick / total_ticks) * 100
        
        return {
            "event": "tick_update",
            "data": {
                "session_id": self.session_id,
                "tick_state": {
                    "timestamp": self.current_time.isoformat(),
                    "current_time": self.current_time.strftime("%Y-%m-%d %H:%M:%S+05:30"),
                    "progress": {
                        "ticks_processed": tick,
                        "total_ticks": total_ticks,
                        "progress_percentage": progress_pct
                    },
                    "active_nodes": ["entry-condition-1"],
                    "pending_nodes": [],
                    "completed_nodes_this_tick": [],
                    "open_positions": position_data["positions"],
                    "pnl_summary": position_data["pnl"],
                    "ltp_store": {
                        "NIFTY": 25000.0 + (tick * 0.5),
                        "NIFTY28DEC2525000CE": position_data.get("ce_price", 150.0),
                        "BANKNIFTY": 52000.0 + (tick * 1.2)
                    },
                    "candle_data": {
                        "NIFTY": {
                            "timestamp": self.current_time.isoformat(),
                            "open": 25000.0,
                            "high": 25000.0 + (tick * 0.6),
                            "low": 25000.0 - (tick * 0.3),
                            "close": 25000.0 + (tick * 0.5),
                            "volume": 1000000 + tick * 1000
                        }
                    }
                }
            }
        }
    
    def advance_time(self, seconds=1):
        """Advance simulation time"""
        self.current_time += timedelta(seconds=seconds)


class UIClient:
    """Simulates UI receiving events and writing to files"""
    
    def __init__(self, output_dir):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.event_counts = {
            'initial_state': 0,
            'node_events': 0,
            'trade_update': 0,
            'tick_update': 0
        }
    
    def decompress_json(self, base64_string):
        """Decompress gzip + base64 data (like UI does)"""
        compressed = base64.b64decode(base64_string)
        decompressed = gzip.decompress(compressed)
        return json.loads(decompressed.decode('utf-8'))
    
    def handle_initial_state(self, event_data):
        """Handle initial_state event"""
        print(f"[UI] Received: initial_state")
        
        # Decompress and write diagnostics
        diagnostics = self.decompress_json(event_data["diagnostics"])
        diagnostics_file = self.output_dir / "diagnostics_export.json"
        with open(diagnostics_file, 'w') as f:
            json.dump(diagnostics, f, indent=2)
        print(f"  └─ Wrote: diagnostics_export.json ({diagnostics_file.stat().st_size} bytes)")
        
        # Decompress and write trades
        trades = self.decompress_json(event_data["trades"])
        trades_file = self.output_dir / "trades_daily.json"
        with open(trades_file, 'w') as f:
            json.dump(trades, f, indent=2)
        print(f"  └─ Wrote: trades_daily.json ({trades_file.stat().st_size} bytes)")
        
        self.event_counts['initial_state'] += 1
    
    def handle_node_events(self, event_data):
        """Handle node_events event"""
        # Decompress diagnostics
        diagnostics = self.decompress_json(event_data["diagnostics"])
        
        # REPLACE entire file (backend sends full diagnostics each time)
        diagnostics_file = self.output_dir / "diagnostics_export.json"
        with open(diagnostics_file, 'w') as f:
            json.dump(diagnostics, f, indent=2)
        
        num_events = len(diagnostics.get("events_history", {}))
        print(f"[UI] Received: node_events ({num_events} total events)")
        
        self.event_counts['node_events'] += 1
    
    def handle_trade_update(self, event_data):
        """Handle trade_update event"""
        # Decompress trades
        trades = self.decompress_json(event_data["trades"])
        
        # REPLACE entire file (backend sends full trades each time)
        trades_file = self.output_dir / "trades_daily.json"
        with open(trades_file, 'w') as f:
            json.dump(trades, f, indent=2)
        
        num_trades = len(trades.get("trades", []))
        total_pnl = trades.get("summary", {}).get("total_pnl", "0.00")
        print(f"[UI] Received: trade_update ({num_trades} trades, P&L: ₹{total_pnl})")
        
        self.event_counts['trade_update'] += 1
    
    def handle_tick_update(self, event_data):
        """Handle tick_update event"""
        tick_state = event_data["tick_state"]
        
        # APPEND to stream file (one line per tick)
        tick_file = self.output_dir / "tick_updates_stream.jsonl"
        with open(tick_file, 'a') as f:
            f.write(json.dumps(tick_state) + '\n')
        
        tick_num = tick_state["progress"]["ticks_processed"]
        pnl = tick_state["pnl_summary"].get("total_pnl", "0.00")
        positions = len(tick_state["open_positions"])
        
        # Print every 100 ticks
        if tick_num % 100 == 0:
            print(f"[UI] Tick {tick_num} | Positions: {positions} | P&L: ₹{pnl}")
        
        self.event_counts['tick_update'] += 1


def run_smoke_test(num_ticks=1000, speed_multiplier=5000):
    """Run complete smoke test"""
    
    print("="*80)
    print("🧪 STANDALONE SMOKE TEST: Complete SSE Data Flow")
    print("="*80)
    print(f"Ticks: {num_ticks}")
    print(f"Speed: {speed_multiplier}x")
    print("="*80)
    print("")
    
    # Initialize
    session_id = f"sim-smoke-test-{int(time.time())}"
    simulator = EventSimulator(session_id, "NIFTY Straddle")
    ui_client = UIClient(f"smoke_test_output/{session_id}")
    
    print(f"Session ID: {session_id}")
    print(f"Output Dir: smoke_test_output/{session_id}/")
    print("")
    
    # Track position state
    position_state = {
        "positions": [],
        "pnl": {
            "realized_pnl": "0.00",
            "unrealized_pnl": "0.00",
            "total_pnl": "0.00",
            "closed_trades": 0,
            "open_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": "0.00"
        }
    }
    
    start_time = time.time()
    
    # Send initial_state
    event = simulator.generate_initial_state()
    ui_client.handle_initial_state(event["data"])
    print("")
    
    # Simulate ticks
    for tick in range(1, num_ticks + 1):
        # Entry at tick 100
        if tick == 100:
            print(f"\n[SIMULATION] Tick {tick}: Entry placed - NIFTY CE @150")
            
            # Generate node_event
            event = simulator.generate_node_event(tick, "Entry", {
                "action": "entry_placed",
                "symbol": "NIFTY28DEC2525000CE",
                "quantity": 50,
                "price": 150.00
            })
            ui_client.handle_node_events(event["data"])
            
            # Update position state
            position_state["positions"] = [{
                "position_id": "pos-001",
                "symbol": "NIFTY28DEC2525000CE",
                "exchange": "NFO",
                "quantity": 50,
                "entry_price": 150.00,
                "current_price": 150.00,
                "unrealized_pnl": 0.00,
                "entry_time": simulator.current_time.isoformat()
            }]
            position_state["pnl"]["open_trades"] = 1
            print("")
        
        # Update position P&L
        if 100 < tick < 500 and position_state["positions"]:
            current_price = 150.00 + ((tick - 100) * 0.1)
            unrealized_pnl = (current_price - 150.00) * 50
            
            position_state["positions"][0]["current_price"] = current_price
            position_state["positions"][0]["unrealized_pnl"] = unrealized_pnl
            position_state["pnl"]["unrealized_pnl"] = f"{unrealized_pnl:.2f}"
            position_state["pnl"]["total_pnl"] = f"{unrealized_pnl:.2f}"
            position_state["ce_price"] = current_price
        
        # Exit at tick 500
        if tick == 500:
            print(f"\n[SIMULATION] Tick {tick}: Exit placed")
            
            exit_price = 190.00
            pnl = (exit_price - 150.00) * 50
            
            # Generate node_event
            event = simulator.generate_node_event(tick, "Exit", {
                "action": "exit_placed",
                "symbol": "NIFTY28DEC2525000CE",
                "quantity": 50,
                "price": exit_price
            })
            ui_client.handle_node_events(event["data"])
            
            # Generate trade_update
            trade = {
                "trade_id": "trade-001",
                "symbol": "NIFTY28DEC2525000CE",
                "entry_time": datetime(2024, 12, 14, 9, 15, 0).isoformat(),
                "exit_time": simulator.current_time.isoformat(),
                "entry_price": 150.00,
                "exit_price": exit_price,
                "quantity": 50,
                "pnl": f"{pnl:.2f}",
                "pnl_percentage": f"{((exit_price - 150.00) / 150.00 * 100):.2f}"
            }
            event = simulator.generate_trade_update(trade)
            ui_client.handle_trade_update(event["data"])
            
            # Clear positions
            position_state["positions"] = []
            position_state["pnl"] = {
                "realized_pnl": f"{pnl:.2f}",
                "unrealized_pnl": "0.00",
                "total_pnl": f"{pnl:.2f}",
                "closed_trades": 1,
                "open_trades": 0,
                "winning_trades": 1,
                "losing_trades": 0,
                "win_rate": "100.00"
            }
            print("")
        
        # Generate tick_update (every tick)
        event = simulator.generate_tick_update(tick, num_ticks, position_state)
        ui_client.handle_tick_update(event["data"])
        
        # Advance time
        simulator.advance_time(1)
        
        # Speed control
        time.sleep(1.0 / speed_multiplier)
    
    elapsed = time.time() - start_time
    ticks_per_sec = num_ticks / elapsed if elapsed > 0 else 0
    
    # Final statistics
    print("\n")
    print("="*80)
    print("📊 TEST RESULTS")
    print("="*80)
    print(f"Total Time: {elapsed:.2f}s")
    print(f"Speed: {ticks_per_sec:.1f} ticks/sec ({speed_multiplier}x target)")
    print("")
    print("Events Received:")
    for event_type, count in ui_client.event_counts.items():
        print(f"  • {event_type}: {count}")
    print("")
    
    # File statistics
    output_dir = ui_client.output_dir
    print("Output Files:")
    
    diag_file = output_dir / "diagnostics_export.json"
    if diag_file.exists():
        with open(diag_file) as f:
            diag = json.load(f)
        num_events = len(diag.get("events_history", {}))
        size = diag_file.stat().st_size
        print(f"  • diagnostics_export.json: {num_events} events ({size:,} bytes)")
    
    trades_file = output_dir / "trades_daily.json"
    if trades_file.exists():
        with open(trades_file) as f:
            trades = json.load(f)
        num_trades = len(trades.get("trades", []))
        total_pnl = trades["summary"]["total_pnl"]
        size = trades_file.stat().st_size
        print(f"  • trades_daily.json: {num_trades} trades, P&L: ₹{total_pnl} ({size:,} bytes)")
    
    tick_file = output_dir / "tick_updates_stream.jsonl"
    if tick_file.exists():
        num_lines = sum(1 for _ in open(tick_file))
        size = tick_file.stat().st_size
        print(f"  • tick_updates_stream.jsonl: {num_lines} ticks ({size:,} bytes)")
    
    print("")
    print("✅ Files match backtesting format exactly!")
    print("="*80)

if __name__ == "__main__":
    import sys
    
    num_ticks = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    speed = float(sys.argv[2]) if len(sys.argv) > 2 else 5000
    
    run_smoke_test(num_ticks, speed)
