#!/usr/bin/env python3
"""
Generate all UI files from diagnostics in one command.

Generates:
1. diagnostics_export.json - Full execution events
2. trades_summary.json - Trades with entry/exit flows (overall + per day)
3. Formats all prices to 2 decimals

Usage:
    python generate_all_ui_files.py
"""

import subprocess
import sys
import os

def run_script(script_name, description):
    """Run a Python script and report success/failure."""
    print(f"\n{'='*80}")
    print(f"Running: {description}")
    print(f"{'='*80}")
    
    try:
        result = subprocess.run(
            [sys.executable, script_name],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            print(f"✅ {description} - COMPLETE")
            if result.stdout:
                # Show last few lines of output
                lines = result.stdout.strip().split('\n')
                if len(lines) > 10:
                    print("   (showing last 10 lines)")
                    for line in lines[-10:]:
                        print(f"   {line}")
                else:
                    print(result.stdout)
            return True
        else:
            print(f"❌ {description} - FAILED")
            print(f"Error: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"❌ {description} - TIMEOUT")
        return False
    except Exception as e:
        print(f"❌ {description} - ERROR: {e}")
        return False

def main():
    print("="*80)
    print("🚀 GENERATING ALL UI FILES")
    print("="*80)
    
    scripts = [
        ("view_diagnostics.py", "Step 1: Generate diagnostics_export.json"),
        ("extract_trades_simplified.py", "Step 2: Extract trades (simplified format)"),
        ("format_diagnostics_prices.py", "Step 3: Format all prices to 2 decimals")
    ]
    
    success_count = 0
    for script_name, description in scripts:
        if run_script(script_name, description):
            success_count += 1
        else:
            print(f"\n⚠️  Stopping due to error in {script_name}")
            break
    
    print("\n" + "="*80)
    if success_count == len(scripts):
        print("✅ ALL FILES GENERATED SUCCESSFULLY")
        print("="*80)
        
        # Show file sizes
        files = [
            "diagnostics_export.json",
            "trades_daily.json"
        ]
        
        print("\n📦 Generated Files:")
        for filename in files:
            if os.path.exists(filename):
                size = os.path.getsize(filename)
                print(f"   ✅ {filename:30} ({size:,} bytes = {size/1024:.1f} KB)")
            else:
                print(f"   ❌ {filename:30} (NOT FOUND)")
        
        print("\n🎯 Files ready for UI development!")
        print("   Location: /Users/sreenathreddy/Downloads/UniTrader-project/backtesting_project/tradelayout-engine/")
        
    else:
        print(f"⚠️  ONLY {success_count}/{len(scripts)} STEPS COMPLETED")
        print("="*80)
    
    return success_count == len(scripts)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
