"""
Simple Backtest using Working API Endpoint
Calls the API, retrieves diagnostics and trades, saves to files
"""

import os
import json
import requests
import gzip
from datetime import datetime


def get_local_backtest_files(
    strategy_id: str,
    backtest_date: str,
    output_dir: str = "simple_live_output"
):
    """
    Read backtest results directly from API server's local storage
    Files are stored in: backtest_results/{strategy_id}/{date}/
    """
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Determine base directory (API server stores files relative to its working directory)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    backtest_results_dir = os.path.join(base_dir, "backtest_results", strategy_id, backtest_date)
    
    print(f"\n{'='*80}")
    print(f"📂 Reading Backtest Files from Local Storage")
    print(f"{'='*80}")
    print(f"Strategy: {strategy_id}")
    print(f"Date: {backtest_date}")
    print(f"Storage Dir: {backtest_results_dir}")
    print(f"Output Dir: {output_dir}")
    print(f"{'='*80}\n")
    
    # Check if directory exists
    if not os.path.exists(backtest_results_dir):
        print(f"❌ Backtest results directory not found: {backtest_results_dir}")
        print(f"   Make sure the backtest has been run via the API first.")
        return None
    
    # Read diagnostics file
    diagnostics_file_gz = os.path.join(backtest_results_dir, "diagnostics_export.json.gz")
    if os.path.exists(diagnostics_file_gz):
        print(f"📖 Reading diagnostics from: {diagnostics_file_gz}")
        with gzip.open(diagnostics_file_gz, 'rt', encoding='utf-8') as f:
            diagnostics_data = json.load(f)
        print(f"✅ Loaded diagnostics")
        
        # Count events
        events_count = len(diagnostics_data.get('events_history', {}))
        print(f"   Events: {events_count}")
        
        # Save uncompressed version to output
        diagnostics_output = os.path.join(output_dir, "diagnostics_export.json")
        with open(diagnostics_output, 'w') as f:
            json.dump(diagnostics_data, f, indent=2, default=str)
        print(f"📝 Saved: {diagnostics_output}")
    else:
        print(f"⚠️  Diagnostics file not found: {diagnostics_file_gz}")
        diagnostics_data = None
    
    # Read trades file
    trades_file_gz = os.path.join(backtest_results_dir, "trades_daily.json.gz")
    if os.path.exists(trades_file_gz):
        print(f"\n📖 Reading trades from: {trades_file_gz}")
        with gzip.open(trades_file_gz, 'rt', encoding='utf-8') as f:
            trades_data = json.load(f)
        print(f"✅ Loaded trades")
        
        # Count trades
        trades_count = len(trades_data.get('trades', []))
        total_pnl = trades_data.get('summary', {}).get('total_pnl', 'N/A')
        print(f"   Trades: {trades_count}")
        print(f"   Total P&L: {total_pnl}")
        
        # Save uncompressed version to output
        trades_output = os.path.join(output_dir, "trades_daily.json")
        with open(trades_output, 'w') as f:
            json.dump(trades_data, f, indent=2, default=str)
        print(f"📝 Saved: {trades_output}")
    else:
        print(f"⚠️  Trades file not found: {trades_file_gz}")
        trades_data = None
    
    print(f"\n{'='*80}")
    print(f"✅ Files Retrieved from Local Storage")
    print(f"{'='*80}\n")
    
    return {
        'diagnostics': diagnostics_data,
        'trades': trades_data
    }


def run_backtest_via_api(
    api_url: str,
    strategy_id: str,
    user_id: str,
    backtest_date: str,
    output_dir: str = "simple_live_output"
):
    """
    Run backtest via API and save results to files
    """
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\n{'='*80}")
    print(f"🚀 Running Backtest via API")
    print(f"{'='*80}")
    print(f"API: {api_url}")
    print(f"Strategy: {strategy_id}")
    print(f"User: {user_id}")
    print(f"Date: {backtest_date}")
    print(f"Output: {output_dir}")
    print(f"{'='*80}\n")
    
    # Prepare request payload
    # API expects start_date and end_date (same date for single day backtest)
    payload = {
        "strategy_id": strategy_id,
        "user_id": user_id,
        "start_date": backtest_date,
        "end_date": backtest_date
    }
    
    print(f"📤 Sending backtest request...")
    print(f"   Payload: {json.dumps(payload, indent=2)}")
    
    try:
        # Call API
        response = requests.post(
            api_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=600  # 10 minutes timeout
        )
        
        print(f"\n✅ API Response: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ Error: {response.text}")
            return None
        
        # Parse response
        result = response.json()
        print(f"📊 Response keys: {list(result.keys())}")
        
        # Save raw response
        raw_response_file = os.path.join(output_dir, "api_response.json")
        with open(raw_response_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        print(f"📝 Saved raw response: {raw_response_file}")
        
        # Check if this is async API with stream_url
        if 'stream_url' in result and 'diagnostics' not in result:
            print(f"\n📡 Backtest started, fetching results from stream...")
            backtest_id = result.get('backtest_id')
            stream_url = result.get('stream_url')
            
            # Get base URL from api_url
            base_url = api_url.rsplit('/api/', 1)[0]
            full_stream_url = f"{base_url}{stream_url}"
            
            print(f"   Stream URL: {full_stream_url}")
            
            # Try to get results from a results endpoint first
            results_url = f"{base_url}/api/v1/backtest/{backtest_id}/results"
            print(f"   Trying results URL: {results_url}")
            
            try:
                results_response = requests.get(
                    results_url,
                    headers={"Accept": "application/json"},
                    timeout=600
                )
                
                if results_response.status_code == 200:
                    result = results_response.json()
                    print(f"✅ Retrieved results from results endpoint")
                    print(f"📊 Result keys: {list(result.keys())}")
                    
                    # Save results
                    results_file = os.path.join(output_dir, "results_response.json")
                    with open(results_file, 'w') as f:
                        json.dump(result, f, indent=2, default=str)
                    print(f"📝 Saved results: {results_file}")
                else:
                    print(f"⚠️  Results endpoint returned {results_response.status_code}")
                    print(f"   Response: {results_response.text[:200]}")
                    
                    # Fall back to consuming SSE stream
                    print(f"\n📡 Consuming SSE stream...")
                    print(f"   Stream URL: {full_stream_url}")
                    print(f"   Please wait, backtest is running...")
                    
                    # Stream endpoint returns SSE, consume it
                    stream_response = requests.get(
                        full_stream_url,
                        headers={"Accept": "text/event-stream"},
                        stream=True,
                        timeout=600
                    )
                    
                    if stream_response.status_code == 200:
                        print(f"✅ Connected to stream")
                        
                        # Parse SSE stream and collect events
                        diagnostics_data = None
                        trades_data = None
                        event_count = 0
                        all_events = []
                        last_event = None
                        
                        for line in stream_response.iter_lines(decode_unicode=True):
                            if not line:
                                continue
                            
                            # SSE format: "event: event_name" followed by "data: json_data"
                            if line.startswith('data: '):
                                event_data = line[6:]  # Remove 'data: ' prefix
                                try:
                                    event = json.loads(event_data)
                                    event_count += 1
                                    all_events.append(event)
                                    last_event = event
                                    
                                    # Debug: show first few events
                                    if event_count <= 5:
                                        print(f"   Event {event_count}: {list(event.keys())}")
                                        if 'has_detail_data' in event:
                                            print(f"      has_detail_data: {event['has_detail_data']}")
                                        if 'summary' in event:
                                            print(f"      summary keys: {list(event['summary'].keys()) if isinstance(event['summary'], dict) else type(event['summary'])}")
                                    
                                    # Progress updates
                                    if 'progress' in event:
                                        progress = event.get('progress', 0)
                                        if event_count % 50 == 0:  # Print every 50 events
                                            print(f"   Progress: {progress}%")
                                    
                                    # Check for diagnostics (might be in different fields)
                                    if 'diagnostics' in event:
                                        diagnostics_data = event['diagnostics']
                                        print(f"   ✅ Received diagnostics")
                                    elif 'events_history' in event:
                                        diagnostics_data = {'events_history': event['events_history']}
                                        print(f"   ✅ Received events_history")
                                    elif 'detail_data' in event:
                                        # Detail data might contain diagnostics
                                        detail = event['detail_data']
                                        if isinstance(detail, dict):
                                            if 'diagnostics' in detail:
                                                diagnostics_data = detail['diagnostics']
                                                print(f"   ✅ Received diagnostics from detail_data")
                                            if 'trades' in detail:
                                                trades_data = detail['trades']
                                                print(f"   ✅ Received trades from detail_data")
                                    
                                    # Check for trades (might be in different fields)
                                    if 'trades' in event:
                                        trades_data = event['trades']
                                        print(f"   ✅ Received trades")
                                    elif 'closed_positions' in event:
                                        trades_data = event['closed_positions']
                                        print(f"   ✅ Received closed_positions")
                                    
                                    # Check overall_summary (might have file paths)
                                    if 'overall_summary' in event:
                                        print(f"   📊 Received overall_summary")
                                        summary = event['overall_summary']
                                        if isinstance(summary, dict):
                                            print(f"      Keys: {list(summary.keys())}")
                                    
                                    # Check for completion
                                    if event.get('status') == 'completed' or event.get('event') == 'complete':
                                        print(f"   ✅ Backtest completed")
                                        break
                                        
                                except json.JSONDecodeError as e:
                                    # Some lines might not be JSON (like comments or keep-alive)
                                    if event_count <= 3:
                                        print(f"   Non-JSON line: {line[:100]}")
                                    continue
                        
                        print(f"\n   Total events received: {event_count}")
                        
                        # Save all events for inspection
                        all_events_file = os.path.join(output_dir, "all_stream_events.json")
                        with open(all_events_file, 'w') as f:
                            json.dump(all_events, f, indent=2, default=str)
                        print(f"   📝 Saved all events: {all_events_file}")
                        
                        # Check if any event has has_detail_data flag
                        has_detail_data = any(e.get('has_detail_data', False) for e in all_events)
                        if has_detail_data:
                            print(f"\n   🔍 Detail data available, trying to fetch...")
                            
                            # Try detail endpoint
                            detail_url = f"{base_url}/api/v1/backtest/{backtest_id}/detail"
                            print(f"      Detail URL: {detail_url}")
                            
                            try:
                                detail_response = requests.get(
                                    detail_url,
                                    headers={"Accept": "application/json"},
                                    timeout=60
                                )
                                
                                if detail_response.status_code == 200:
                                    detail_data = detail_response.json()
                                    print(f"      ✅ Retrieved detail data")
                                    print(f"      Keys: {list(detail_data.keys())}")
                                    
                                    # Extract diagnostics and trades from detail
                                    if 'diagnostics' in detail_data:
                                        diagnostics_data = detail_data['diagnostics']
                                        print(f"      ✅ Found diagnostics in detail")
                                    if 'trades' in detail_data:
                                        trades_data = detail_data['trades']
                                        print(f"      ✅ Found trades in detail")
                                    
                                    # Save detail response
                                    detail_file = os.path.join(output_dir, "detail_response.json")
                                    with open(detail_file, 'w') as f:
                                        json.dump(detail_data, f, indent=2, default=str)
                                    print(f"      📝 Saved detail: {detail_file}")
                                else:
                                    print(f"      ⚠️ Detail endpoint returned {detail_response.status_code}")
                                    
                                    # Try with date-specific detail endpoint
                                    detail_date_url = f"{base_url}/api/v1/backtest/{backtest_id}/detail/2024-10-29"
                                    print(f"      Trying date-specific: {detail_date_url}")
                                    
                                    detail_date_response = requests.get(
                                        detail_date_url,
                                        headers={"Accept": "application/json"},
                                        timeout=60
                                    )
                                    
                                    if detail_date_response.status_code == 200:
                                        detail_data = detail_date_response.json()
                                        print(f"      ✅ Retrieved date-specific detail data")
                                        print(f"      Keys: {list(detail_data.keys())}")
                                        
                                        # Extract diagnostics and trades
                                        if 'diagnostics' in detail_data:
                                            diagnostics_data = detail_data['diagnostics']
                                            print(f"      ✅ Found diagnostics")
                                        if 'trades' in detail_data:
                                            trades_data = detail_data['trades']
                                            print(f"      ✅ Found trades")
                                    else:
                                        print(f"      ⚠️ Date-specific detail returned {detail_date_response.status_code}")
                                        
                            except Exception as e:
                                print(f"      ❌ Error fetching detail: {e}")
                        
                        # Build result from collected data
                        result = {}
                        if diagnostics_data:
                            result['diagnostics'] = diagnostics_data
                        if trades_data:
                            result['trades'] = trades_data
                        
                        # If no direct data but we have summary, return that
                        if not result and last_event:
                            if 'overall_summary' in last_event:
                                result['summary'] = last_event['overall_summary']
                            if 'summary' in last_event:
                                result['daily_summary'] = last_event['summary']
                        
                        if not result:
                            print(f"❌ No data collected from {event_count} events")
                            print(f"   💡 Check {all_events_file} for event details")
                            return None
                    else:
                        print(f"❌ Stream error: {stream_response.status_code}")
                        return None
                    
            except Exception as e:
                print(f"❌ Error: {e}")
                import traceback
                traceback.print_exc()
                return None
        
        # Now read the actual detail files from local storage
        print(f"\n📂 Reading detail files from local storage...\n")
        local_results = get_local_backtest_files(
            strategy_id=strategy_id,
            backtest_date=backtest_date,
            output_dir=output_dir
        )
        
        if local_results:
            # Merge API summary with local detailed data
            result.update(local_results)
        
        # Extract and save diagnostics
        if 'diagnostics' in result:
            diagnostics_file = os.path.join(output_dir, "diagnostics_export.json")
            with open(diagnostics_file, 'w') as f:
                json.dump(result['diagnostics'], f, indent=2, default=str)
            print(f"📝 Saved diagnostics: {diagnostics_file}")
            
            # Count events
            events_history = result['diagnostics'].get('events_history', {})
            print(f"   Node events: {len(events_history)}")
        else:
            print(f"⚠️  No diagnostics in response")
        
        # Extract and save trades
        if 'trades' in result:
            trades_file = os.path.join(output_dir, "trades_daily.json")
            with open(trades_file, 'w') as f:
                json.dump(result['trades'], f, indent=2, default=str)
            print(f"📝 Saved trades: {trades_file}")
            
            # Count trades
            if isinstance(result['trades'], dict):
                trades_list = result['trades'].get('trades', [])
            else:
                trades_list = result['trades']
            print(f"   Trades: {len(trades_list)}")
        else:
            print(f"⚠️  No trades in response")
        
        # Extract and save summary/metrics if available
        if 'summary' in result:
            summary_file = os.path.join(output_dir, "summary.json")
            with open(summary_file, 'w') as f:
                json.dump(result['summary'], f, indent=2, default=str)
            print(f"📝 Saved summary: {summary_file}")
        
        print(f"\n{'='*80}")
        print(f"✅ Backtest Triggered via API")
        print(f"{'='*80}\n")
        
        return result
        
    except requests.exceptions.Timeout:
        print(f"❌ Request timeout after 10 minutes")
        return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    # Configuration
    API_URL = "https://986030d95033.ngrok-free.app/api/v1/backtest/start"
    STRATEGY_ID = "5708424d-5962-4629-978c-05b3a174e104"
    USER_ID = "user_2yfjTGEKjL7XkklQyBaMP6SN2Lc"
    BACKTEST_DATE = "2024-10-29"
    
    # Run backtest
    result = run_backtest_via_api(
        api_url=API_URL,
        strategy_id=STRATEGY_ID,
        user_id=USER_ID,
        backtest_date=BACKTEST_DATE
    )
    
    if result:
        print(f"✅ All data saved to: simple_live_output")
    else:
        print(f"❌ Backtest failed")
