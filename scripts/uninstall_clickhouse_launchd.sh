#!/bin/bash
set -euo pipefail

PLIST_NAME="com.tradelayout.clickhouse.plist"
LABEL="com.tradelayout.clickhouse"
DEST_PLIST="$HOME/Library/LaunchAgents/$PLIST_NAME"

launchctl bootout "gui/$UID" "$DEST_PLIST" >/dev/null 2>&1 || true
rm -f "$DEST_PLIST"

echo "✅ Uninstalled: $LABEL"
