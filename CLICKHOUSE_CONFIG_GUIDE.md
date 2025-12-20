# ClickHouse Configuration Guide

## Overview

All ClickHouse connection settings are now centralized in one location: `src/config/clickhouse_config.py`

## Quick Start

### 1. Environment Variables (Recommended)

Create a `.env` file in the project root:

```bash
# Local ClickHouse (default)
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=9000
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=
CLICKHOUSE_DATABASE=tradelayout
CLICKHOUSE_SECURE=false
```

### 2. Direct Config File

Or modify defaults in `src/config/clickhouse_config.py`:

```python
class ClickHouseConfig:
    HOST = os.getenv('CLICKHOUSE_HOST', 'localhost')
    PORT = int(os.getenv('CLICKHOUSE_PORT', '9000'))
    USER = os.getenv('CLICKHOUSE_USER', 'default')
    PASSWORD = os.getenv('CLICKHOUSE_PASSWORD', '')
    SECURE = os.getenv('CLICKHOUSE_SECURE', 'false').lower() == 'true'
    DATABASE = os.getenv('CLICKHOUSE_DATABASE', 'tradelayout')
```

## Usage in Code

### For clickhouse_connect library (most common)

```python
from src.config.clickhouse_config import ClickHouseConfig
import clickhouse_connect

client = clickhouse_connect.get_client(**ClickHouseConfig.get_clickhouse_connect_config())
```

### For clickhouse-driver library

```python
from src.config.clickhouse_config import ClickHouseConfig
from clickhouse_driver import Client

client = Client(**ClickHouseConfig.get_connection_config())
```

## Files Updated

### Core Configuration
- ✅ `src/config/clickhouse_config.py` - Main config file

### Production Files (Using Config)
- ✅ `expiry_calculator.py` - Now uses `ClickHouseConfig`
- ✅ `backtest_strike_loader.py` - Now uses `ClickHouseConfig`
- ✅ All files importing from `src.config.clickhouse_config` automatically use it

### Test/Example Files (Not Updated - For Reference Only)
- ⚠️ `tests/test_*.py` - Test files (use hardcoded values, not run in production)
- ⚠️ `example_strategy.py` - Example only (not production code)
- ⚠️ `_archived_legacy_backtest/` - Archived files (not used)
- ⚠️ `run_complete_system.sh` - Helper script (modify if needed)

## Switching Between Environments

### Local ClickHouse (Default)

```bash
export CLICKHOUSE_HOST=localhost
export CLICKHOUSE_PORT=9000
export CLICKHOUSE_DATABASE=tradelayout
export CLICKHOUSE_SECURE=false
```

### Cloud ClickHouse (If Needed)

```bash
export CLICKHOUSE_HOST=your-host.clickhouse.cloud
export CLICKHOUSE_PORT=9440
export CLICKHOUSE_USER=default
export CLICKHOUSE_PASSWORD=your-password
export CLICKHOUSE_DATABASE=default
export CLICKHOUSE_SECURE=true
```

## Connection Validation

Test your config with:

```bash
python -c "from src.config.clickhouse_config import ClickHouseConfig; print(ClickHouseConfig.get_clickhouse_connect_config())"
```

Or use the CLI:

```bash
clickhouse client \
  --host $(python -c "from src.config.clickhouse_config import ClickHouseConfig; print(ClickHouseConfig.HOST)") \
  --port $(python -c "from src.config.clickhouse_config import ClickHouseConfig; print(ClickHouseConfig.PORT)") \
  --user $(python -c "from src.config.clickhouse_config import ClickHouseConfig; print(ClickHouseConfig.USER)") \
  --database $(python -c "from src.config.clickhouse_config import ClickHouseConfig; print(ClickHouseConfig.DATABASE)") \
  --query "SELECT 1"
```

## Current Setup Status

✅ **Local ClickHouse Running:** localhost:9000  
✅ **Database:** tradelayout  
✅ **Data Loaded:** ~44 GB (2.5B+ rows)  
✅ **Tables:** nse_ticks_options, raw_ticks_all, nse_ticks_stocks, etc.

## Backup Information

**S3 Backup Location:** `s3://tradelayout-backup/clickhouse-backups/20251206_110204/`  
**Backup Size:** 43.23 GB  
**Backup Scripts:**
- `scripts/backup_clickhouse_to_s3.sh` - Backup to S3
- `scripts/restore_clickhouse_from_s3.sh` - Restore from S3

## Security Notes

1. **Never commit `.env` files** - They contain credentials
2. **Use environment variables** in production
3. **Empty password** is fine for local development
4. **Enable TLS (`SECURE=true`)** for cloud/production

## Troubleshooting

### Connection Failed

```python
# Check current config
from src.config.clickhouse_config import ClickHouseConfig
print(f"Host: {ClickHouseConfig.HOST}")
print(f"Port: {ClickHouseConfig.PORT}")
print(f"Database: {ClickHouseConfig.DATABASE}")
```

### Wrong Database

```bash
# Set correct database
export CLICKHOUSE_DATABASE=tradelayout
```

### Port Issues

- Native protocol: Port 9000 (default)
- HTTP protocol: Port 8123
- HTTPS protocol: Port 8443
- Secure native: Port 9440

## Migration Complete ✅

- ✅ Local ClickHouse installed and running
- ✅ Data migrated from cloud (43 GB)
- ✅ Config centralized in one place
- ✅ All production code uses `ClickHouseConfig`
- ✅ Environment variables supported
- ✅ Cloud credentials removed from codebase
