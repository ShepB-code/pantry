#!/usr/bin/env bash
# Minimal depletion demo — same flow as simulate-toast-sftp-drop.sh, but wired so
# exactly ONE inventory item changes in a predictable way.
#
# What this demo does
# -------------------
# 0. Ensures DB schema exists and xtraCHEF catalog was loaded (bootstrap)
# 1. Resets "Worcestershire sauce" on_hand to 10.0 in the database
# 2. Ensures a recipe: 1 Dipping Sauce sold → uses 0.5 Worcestershire
# 3. Drops a tiny POS file onto the local SFTP folder (10 Dipping Sauce sold)
# 4. Runs toast-pull --apply (ingest sales + deplete inventory)
#
# Expected result in Inventory → Current Stock
#   Ingredient: Worcestershire sauce (or similar)
#   On Hand:    10.0  →  5.0   (10 sold × 0.5 per serving = 5.0 used)
#
# Prerequisites (run once):
#   ./scripts/bootstrap-db.sh perilla
#
# Usage:
#   ./scripts/demo-toast-depletion.sh
#   ./scripts/demo-toast-depletion.sh perilla
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# --- demo constants (must match data/dev/demo/ItemSelectionDetails_depletion_demo.csv) ---
BUSINESS_DATE="2026-06-01"
DEMO_CSV="$ROOT/data/dev/demo/ItemSelectionDetails_depletion_demo.csv"
MENU_ITEM="Dipping Sauce"
INGREDIENT="Worcestershire sauce"
START_ON_HAND="10.0"
SALES_QTY="10"
QTY_PER_SERVING="0.5"
EXPECTED_AFTER="5.0"

LOCATION="${1:-${PANTRY_DEFAULT_LOCATION_ID:-perilla}}"
EXPORT_ID="${TOAST_SFTP_EXPORT_ID:-local_dev}"
SFTP_ROOT="${TOAST_SFTP_LOCAL_ROOT:-$ROOT/data/dev/toast-sftp}"
YYYYMMDD="${BUSINESS_DATE//-/}"
DEST="$SFTP_ROOT/$EXPORT_ID/$YYYYMMDD"

export PANTRY_DEFAULT_LOCATION_ID="$LOCATION"
export TOAST_SFTP_LOCAL_ROOT="$SFTP_ROOT"
export TOAST_SFTP_EXPORT_ID="$EXPORT_ID"

if [[ ! -f "$ROOT/backend/.env" ]]; then
  echo "Missing backend/.env — run first:" >&2
  echo "  ./scripts/bootstrap-db.sh $LOCATION" >&2
  exit 1
fi

if [[ ! -f "$DEMO_CSV" ]]; then
  echo "Missing demo CSV: $DEMO_CSV" >&2
  exit 1
fi

echo "══════════════════════════════════════════════════════════════"
echo "  Pantry depletion demo (location: $LOCATION)"
echo "══════════════════════════════════════════════════════════════"
echo ""
echo "Scenario:"
echo "  • Menu item sold:  $MENU_ITEM × $SALES_QTY  (business date $BUSINESS_DATE)"
echo "  • Recipe:          $QTY_PER_SERVING × $INGREDIENT per serving"
echo "  • On hand before:  $START_ON_HAND"
echo "  • On hand after:   $EXPECTED_AFTER  ($SALES_QTY × $QTY_PER_SERVING depleted)"
echo ""

cd "$ROOT/backend"

echo "Step 0/4 — Check database (schema + xtraCHEF catalog)"
if grep -q '^DATABASE_URL=' .env 2>/dev/null; then
  uv run alembic upgrade head
fi
uv run python - <<PY
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(".env"))

from pantry_engine.db.models import InventoryItemRecord
from pantry_engine.db.session import init_db, get_session_factory, resolve_database_url
from pantry_engine.demo.depletion import DEMO_INVENTORY_ITEM_ID

location = "${LOCATION}"
init_db()

with get_session_factory()() as session:
    row = session.get(
        InventoryItemRecord,
        {"location_id": location, "id": DEMO_INVENTORY_ITEM_ID},
    )
    if row is None:
        print(
            f"Inventory item {DEMO_INVENTORY_ITEM_ID!r} not found.\n"
            f"Run: ./scripts/bootstrap-db.sh {location}",
            file=sys.stderr,
        )
        sys.exit(1)

db = resolve_database_url()
print(f"  OK — using {db.split('@')[-1] if '@' in db else db}")
PY

echo ""
echo "Step 1/4 — Reset on_hand=$START_ON_HAND + recipe ($MENU_ITEM → $INGREDIENT)"
uv run python - <<PY
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(".env"))

from pantry_engine.demo.depletion import setup_demo_state
from pantry_engine.db.session import get_session_factory

location = "${LOCATION}"
with get_session_factory()() as session:
    setup_demo_state(session, location_id=location)
print("  OK — recipe and starting on_hand set")
PY

echo ""
echo "Step 2/4 — Simulate Toast SFTP drop"
mkdir -p "$DEST"
cp "$DEMO_CSV" "$DEST/ItemSelectionDetails.csv"
echo "  Dropped: $DEST/ItemSelectionDetails.csv"
echo "  (1 line: $SALES_QTY × $MENU_ITEM on $BUSINESS_DATE)"

echo ""
echo "Step 3/4 — Pull from SFTP + ingest sales + apply depletion"
uv run python -m pantry_engine.cli toast-pull --date "$BUSINESS_DATE" --force --apply

echo ""
echo "Step 4/4 — Done"
echo "  Open Inventory → Current Stock → search “$INGREDIENT”"
echo "  On Hand should be $EXPECTED_AFTER (was $START_ON_HAND)."
