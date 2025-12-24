#!/usr/bin/env python3
import argparse
import gzip
import io
import json
import sys
import tempfile
import zipfile

import requests


def _as_float(x):
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip()
    if not s:
        return None
    try:
        return float(s)
    except Exception:
        try:
            return float(s.replace(",", ""))
        except Exception:
            return None


def _normalize_summary_from_sync(resp_json: dict) -> dict:
    data = (resp_json or {}).get("data") or {}
    s = data.get("overall_summary") or {}
    return {
        "total_trades": int(s.get("total_positions") or 0),
        "total_pnl": _as_float(s.get("total_pnl")) or 0.0,
        "winning_trades": int(s.get("total_winning_trades") or 0),
        "losing_trades": int(s.get("total_losing_trades") or 0),
        "breakeven_trades": int(s.get("total_breakeven_trades") or 0),
        "win_rate": _as_float(s.get("overall_win_rate")) or 0.0,
    }


def _normalize_trades_from_sync(resp_json: dict) -> list[dict]:
    data = (resp_json or {}).get("data") or {}
    daily_results = data.get("daily_results") or []
    trades = []
    for day in daily_results:
        for pos in day.get("positions") or []:
            position_id = pos.get("position_id") or pos.get("trade_id")
            re_entry_num = pos.get("re_entry_num", 0)
            key = f"{position_id}:{re_entry_num}"
            trades.append(
                {
                    "key": key,
                    "position_id": position_id,
                    "re_entry_num": int(re_entry_num or 0),
                    "symbol": pos.get("symbol"),
                    "side": pos.get("side"),
                    "pnl": _as_float(pos.get("pnl")) or 0.0,
                    "entry_time": pos.get("entry_time"),
                    "exit_time": pos.get("exit_time"),
                }
            )
    return trades


def _run_sync(base_url: str, payload: dict, timeout_s: int) -> tuple[dict, list[dict]]:
    r = requests.post(f"{base_url}/api/v1/backtest", json=payload, timeout=timeout_s)
    r.raise_for_status()
    j = r.json()
    return _normalize_summary_from_sync(j), _normalize_trades_from_sync(j)


def _run_ndjson(base_url: str, payload: dict, timeout_s: int) -> tuple[dict, list[dict]]:
    r = requests.post(f"{base_url}/api/v1/backtest/stream", json=payload, stream=True, timeout=timeout_s)
    r.raise_for_status()

    complete = None
    trades = []

    for raw_line in r.iter_lines(decode_unicode=True):
        if not raw_line:
            continue
        line = raw_line.strip()
        if not line:
            continue
        obj = json.loads(line)
        t = obj.get("type")
        if t == "transaction":
            pos = obj.get("data") or {}
            position_id = pos.get("position_id") or pos.get("trade_id")
            re_entry_num = pos.get("re_entry_num", 0)
            key = f"{position_id}:{re_entry_num}"
            trades.append(
                {
                    "key": key,
                    "position_id": position_id,
                    "re_entry_num": int(re_entry_num or 0),
                    "symbol": pos.get("symbol"),
                    "side": pos.get("side"),
                    "pnl": _as_float(pos.get("pnl")) or 0.0,
                    "entry_time": pos.get("entry_time"),
                    "exit_time": pos.get("exit_time"),
                }
            )
        elif t == "complete":
            complete = obj

    if not complete:
        raise RuntimeError("NDJSON stream did not produce a complete event")

    s = complete.get("overall_summary") or {}
    summary = {
        "total_trades": int(s.get("total_positions") or 0),
        "total_pnl": _as_float(s.get("total_pnl")) or 0.0,
        "winning_trades": int(s.get("total_winning_trades") or 0),
        "losing_trades": int(s.get("total_losing_trades") or 0),
        "breakeven_trades": int(s.get("total_breakeven_trades") or 0),
        "win_rate": _as_float(s.get("overall_win_rate")) or 0.0,
    }

    return summary, trades


def _parse_sse_events(resp: requests.Response):
    event_type = None
    data_lines = []

    for raw in resp.iter_lines(decode_unicode=True):
        if raw is None:
            continue
        line = raw.strip("\r")
        if not line:
            if data_lines:
                data = "\n".join(data_lines)
                yield event_type, data
            event_type = None
            data_lines = []
            continue

        if line.startswith(":"):
            continue

        if line.startswith("event:"):
            event_type = line.split(":", 1)[1].strip()
            continue

        if line.startswith("data:"):
            data_lines.append(line.split(":", 1)[1].lstrip())
            continue


def _read_json_from_gz_bytes(gz_bytes: bytes) -> dict:
    with gzip.open(io.BytesIO(gz_bytes), "rt", encoding="utf-8") as f:
        return json.load(f)


def _run_sse(base_url: str, strategy_id: str, start_date: str, end_date: str, strategy_scale: float, timeout_s: int) -> tuple[dict, list[dict]]:
    start_payload = {
        "strategy_id": strategy_id,
        "start_date": start_date,
        "end_date": end_date,
        "strategy_scale": strategy_scale,
    }

    r = requests.post(f"{base_url}/api/v1/backtest/start", json=start_payload, timeout=timeout_s)
    r.raise_for_status()
    start_obj = r.json()
    backtest_id = start_obj.get("backtest_id")
    if not backtest_id:
        raise RuntimeError(f"Missing backtest_id in response: {start_obj}")

    stream = requests.get(f"{base_url}/api/v1/backtest/{backtest_id}/stream", stream=True, timeout=timeout_s)
    stream.raise_for_status()

    completed = None
    for ev, data in _parse_sse_events(stream):
        if ev == "backtest_completed":
            completed = json.loads(data)
            break

    if not completed:
        raise RuntimeError("SSE did not emit backtest_completed")

    download_date = start_date
    z = requests.get(f"{base_url}/api/v1/backtest/{backtest_id}/day/{download_date}", timeout=timeout_s)
    z.raise_for_status()

    with tempfile.TemporaryDirectory() as td:
        zp = zipfile.ZipFile(io.BytesIO(z.content))
        zp.extractall(td)

        with open(f"{td}/trades_daily.json.gz", "rb") as f:
            trades_daily = _read_json_from_gz_bytes(f.read())

        summary_obj = (trades_daily or {}).get("summary") or {}
        summary = {
            "total_trades": int(summary_obj.get("total_trades") or 0),
            "total_pnl": _as_float(summary_obj.get("total_pnl")) or 0.0,
            "winning_trades": int(summary_obj.get("winning_trades") or 0),
            "losing_trades": int(summary_obj.get("losing_trades") or 0),
            "breakeven_trades": 0,
            "win_rate": _as_float(summary_obj.get("win_rate")) or 0.0,
        }

        trades = []
        for t in (trades_daily or {}).get("trades") or []:
            position_id = t.get("position_id") or t.get("trade_id")
            re_entry_num = t.get("re_entry_num", 0)
            key = f"{position_id}:{re_entry_num}"
            trades.append(
                {
                    "key": key,
                    "position_id": position_id,
                    "re_entry_num": int(re_entry_num or 0),
                    "symbol": t.get("symbol"),
                    "side": t.get("side"),
                    "pnl": _as_float(t.get("pnl")) or 0.0,
                    "entry_time": t.get("entry_time"),
                    "exit_time": t.get("exit_time"),
                }
            )

    return summary, trades


def _index_trades(trades: list[dict]) -> dict:
    return {t["key"]: t for t in trades}


def _print_summary(name: str, s: dict):
    keys = ["total_trades", "total_pnl", "winning_trades", "losing_trades", "breakeven_trades", "win_rate"]
    row = " | ".join([name] + [str(s.get(k)) for k in keys])
    print(row)


def _diff_summaries(a_name: str, a: dict, b_name: str, b: dict):
    diffs = []
    for k in set(a.keys()).union(b.keys()):
        if a.get(k) != b.get(k):
            diffs.append((k, a.get(k), b.get(k)))
    if diffs:
        print(f"\nSUMMARY DIFF: {a_name} vs {b_name}")
        for k, av, bv in sorted(diffs, key=lambda x: x[0]):
            print(f"  {k}: {av} != {bv}")


def _diff_trades(a_name: str, a_trades: list[dict], b_name: str, b_trades: list[dict]):
    a_idx = _index_trades(a_trades)
    b_idx = _index_trades(b_trades)
    a_keys = set(a_idx.keys())
    b_keys = set(b_idx.keys())

    missing_in_b = sorted(a_keys - b_keys)
    missing_in_a = sorted(b_keys - a_keys)

    if missing_in_b or missing_in_a:
        print(f"\nTRADE KEY DIFF: {a_name} vs {b_name}")
        if missing_in_b:
            print(f"  present in {a_name} only: {missing_in_b[:20]}" + (" ..." if len(missing_in_b) > 20 else ""))
        if missing_in_a:
            print(f"  present in {b_name} only: {missing_in_a[:20]}" + (" ..." if len(missing_in_a) > 20 else ""))

    pnl_diffs = []
    for k in sorted(a_keys & b_keys):
        ap = a_idx[k].get("pnl")
        bp = b_idx[k].get("pnl")
        if round(ap or 0.0, 4) != round(bp or 0.0, 4):
            pnl_diffs.append((k, ap, bp))

    if pnl_diffs:
        print(f"\nTRADE PNL DIFF: {a_name} vs {b_name} (showing up to 20)")
        for k, ap, bp in pnl_diffs[:20]:
            print(f"  {k}: {ap} != {bp}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--strategy-id", required=True)
    ap.add_argument("--start-date", required=True)
    ap.add_argument("--end-date", default=None)
    ap.add_argument("--strategy-scale", type=float, default=1.0)
    ap.add_argument("--include-diagnostics", action="store_true")
    ap.add_argument("--timeout", type=int, default=300)
    args = ap.parse_args()

    end_date = args.end_date or args.start_date

    payload = {
        "strategy_id": args.strategy_id,
        "start_date": args.start_date,
        "end_date": end_date,
        "mode": "backtesting",
        "include_diagnostics": bool(args.include_diagnostics),
        "strategy_scale": args.strategy_scale,
    }

    print("Running modes...")

    sync_summary, sync_trades = _run_sync(args.base_url, payload, args.timeout)
    nd_summary, nd_trades = _run_ndjson(args.base_url, payload, args.timeout)

    if args.start_date != end_date:
        print("SSE mode comparison currently supports single-day only. Use a single date.")
        sys.exit(2)

    sse_summary, sse_trades = _run_sse(
        args.base_url,
        args.strategy_id,
        args.start_date,
        end_date,
        args.strategy_scale,
        args.timeout,
    )

    print("\nMODE | total_trades | total_pnl | winning_trades | losing_trades | breakeven_trades | win_rate")
    _print_summary("SYNC", sync_summary)
    _print_summary("NDJSON", nd_summary)
    _print_summary("SSE", sse_summary)

    _diff_summaries("SYNC", sync_summary, "NDJSON", nd_summary)
    _diff_summaries("SYNC", sync_summary, "SSE", sse_summary)
    _diff_summaries("NDJSON", nd_summary, "SSE", sse_summary)

    _diff_trades("SYNC", sync_trades, "NDJSON", nd_trades)
    _diff_trades("SYNC", sync_trades, "SSE", sse_trades)
    _diff_trades("NDJSON", nd_trades, "SSE", sse_trades)

    print("\nTrade counts:")
    print(f"  SYNC: {len(sync_trades)}")
    print(f"  NDJSON: {len(nd_trades)}")
    print(f"  SSE: {len(sse_trades)}")


if __name__ == "__main__":
    main()
