#!/usr/bin/env python3
"""Generate COMPLETE_BACKTEST_RESULTS.json from a fresh backtest.

This script:
- Uses the existing run_dashboard_backtest() entrypoint
- Reads positions (dashboard_data['positions']) and diagnostics
- Writes/overwrites COMPLETE_BACKTEST_RESULTS.json on every run

No changes to core logic or diagnostics.
"""

import os
import sys
import json
from datetime import date

# Ensure local imports work when run as a script
sys.path.insert(0, os.path.dirname(__file__))

from show_dashboard_data import run_dashboard_backtest  # type: ignore

DEFAULT_STRATEGY_ID = "5708424d-5962-4629-978c-05b3a174e104"
DEFAULT_BACKTEST_DATE = "2024-10-29"  # ISO string


def _parse_date(s: str) -> date:
    return date.fromisoformat(s)


def generate_complete_results(strategy_id: str, backtest_date_str: str) -> str:
    """Run backtest and write COMPLETE_BACKTEST_RESULTS.json.

    Returns the output file path.
    """
    backtest_date = _parse_date(backtest_date_str)

    result = run_dashboard_backtest(strategy_id, backtest_date)

    positions = result.get("positions", [])
    diag = result.get("diagnostics", {}) or {}

    closed = [p for p in positions if p.get("status") == "CLOSED"]

    total_pnl = sum(p.get("pnl", 0.0) or 0.0 for p in closed)
    winning = [p for p in closed if (p.get("pnl") or 0.0) > 0]
    losing = [p for p in closed if (p.get("pnl") or 0.0) < 0]

    win_rate = (len(winning) / len(closed) * 100.0) if closed else 0.0

    # Build compact positions array for UI
    ui_positions = []
    for idx, p in enumerate(positions, start=1):
        ui_positions.append(
            {
                "position_number": idx,
                "position_id": p.get("position_id"),
                "symbol": p.get("symbol"),
                "side": p.get("side"),
                "quantity": p.get("quantity"),
                "entry_price": p.get("entry_price"),
                "exit_price": p.get("exit_price"),
                "entry_time": p.get("entry_timestamp") or p.get("entry_time"),
                "exit_time": p.get("exit_timestamp") or p.get("exit_time"),
                "duration_minutes": p.get("duration_minutes"),
                "pnl": p.get("pnl"),
                "pnl_percent": p.get("pnl_percentage"),
                # These can be filled from diagnostics later if needed
                "re_entry_num": None,
            }
        )

    output = {
        "metadata": {
            "strategy_id": strategy_id,
            "backtest_date": backtest_date_str,
        },
        "summary": {
            "total_positions": len(positions),
            "total_pnl": round(total_pnl, 2),
            "win_rate_percent": round(win_rate, 1),
            "winning_trades": len(winning),
            "losing_trades": len(losing),
            "nodes_with_events": len(diag.get("events_history", {})),
            "active_nodes_remaining": len(diag.get("current_state", {})),
        },
        "positions": ui_positions,
    }

    out_path = os.path.join(os.path.dirname(__file__), "COMPLETE_BACKTEST_RESULTS.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)

    return out_path


if __name__ == "__main__":
    strategy_id = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_STRATEGY_ID
    backtest_date = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_BACKTEST_DATE

    out = generate_complete_results(strategy_id, backtest_date)
    print(f"✅ COMPLETE_BACKTEST_RESULTS.json written to: {out}")
