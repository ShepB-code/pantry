#!/usr/bin/env bash
# Simulate Toast dropping a nightly export onto SFTP (local folder) and ingest + deplete.
#
# Usage:
#   ./scripts/simulate-toast-sftp-drop.sh                    # yesterday, sample CSV
#   ./scripts/simulate-toast-sftp-drop.sh 2026-04-15         # specific business date
#   ./scripts/simulate-toast-sftp-drop.sh 2026-04-15 path/to/ItemSelectionDetails.csv
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

BUSINESS_DATE="${1:-$(date -v-1d +%Y-%m-%d 2>/dev/null || date -d yesterday +%Y-%m-%d)}"
SRC_CSV="${2:-$ROOT/data/toast/pos/2026/ItemSelectionDetails_2026_04_01-2026_04_30.csv}"
EXPORT_ID="${TOAST_SFTP_EXPORT_ID:-local_dev}"
SFTP_ROOT="${TOAST_SFTP_LOCAL_ROOT:-$ROOT/data/dev/toast-sftp}"
YYYYMMDD="${BUSINESS_DATE//-/}"

DEST="$SFTP_ROOT/$EXPORT_ID/$YYYYMMDD"
mkdir -p "$DEST"
cp "$SRC_CSV" "$DEST/ItemSelectionDetails.csv"
echo "Dropped: $DEST/ItemSelectionDetails.csv"

export TOAST_SFTP_LOCAL_ROOT="$SFTP_ROOT"
export TOAST_SFTP_EXPORT_ID="$EXPORT_ID"

cd "$ROOT/backend"
uv run python -m pantry_engine.cli toast-pull --date "$BUSINESS_DATE" --force --apply

echo ""
echo "Refresh Inventory in the UI (Current Stock tab)."
echo "For on_hand to drop from sales you need recipe_lines — example:"
echo "  psql \$DATABASE_URL -c \"INSERT INTO recipe_lines (location_id, menu_item_id, inventory_item_id, qty_per_serving, waste_factor) VALUES ('default', 'MENU_ID', 'INVENTORY_ID', 0.5, 0) ON CONFLICT DO NOTHING;\""
