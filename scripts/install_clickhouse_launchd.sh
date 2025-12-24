#!/bin/bash
set -euo pipefail

PLIST_NAME="com.tradelayout.clickhouse.plist"
LABEL="com.tradelayout.clickhouse"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_PLIST="$REPO_ROOT/launchd/$PLIST_NAME"
DEST_DIR="$HOME/Library/LaunchAgents"
DEST_PLIST="$DEST_DIR/$PLIST_NAME"

if [ ! -f "$SRC_PLIST" ]; then
  echo "❌ Missing source plist: $SRC_PLIST"
  exit 1
fi

mkdir -p "$DEST_DIR"
mkdir -p "$HOME/clickhouse_data/logs"

cp "$SRC_PLIST" "$DEST_PLIST"

launchctl bootout "gui/$UID" "$DEST_PLIST" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$UID" "$DEST_PLIST"
launchctl enable "gui/$UID/$LABEL" >/dev/null 2>&1 || true
launchctl kickstart -k "gui/$UID/$LABEL" >/dev/null 2>&1 || true

echo "✅ Installed and started: $LABEL"
echo "Logs: $HOME/clickhouse_data/logs/launchd-clickhouse.*.log"
