"""Minimal Toast SFTP depletion demo (one menu item → one inventory item)."""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from pantry_engine.db.models import InventoryItemRecord, MenuItemRecord, RecipeLineRecord
from pantry_engine.db.seed import default_location_id, ensure_default_location
from pantry_engine.ingest.paths import IngestPaths
from pantry_engine.ingest.toast_sftp.apply import apply_pulled_sales
from pantry_engine.ingest.toast_sftp.config import ToastSftpConfig
from pantry_engine.ingest.toast_sftp.downloader import get_toast_downloader
from pantry_engine.ingest.toast_sftp.pull import pull_item_selection
from pantry_engine.root import repo_root

DEMO_BUSINESS_DATE = date(2026, 6, 1)
DEMO_CSV = repo_root() / "data/dev/demo/ItemSelectionDetails_depletion_demo.csv"
DEMO_MENU_ITEM_ID = "dipping_sauce"
DEMO_MENU_ITEM_NAME = "Dipping Sauce"
DEMO_INVENTORY_ITEM_ID = "worcestershire sauce"
DEMO_QTY_PER_SERVING = 0.5
DEMO_STARTING_ON_HAND = 10.0
DEMO_SALES_QTY = 10.0


def setup_demo_state(session: Session, *, location_id: str | None = None) -> dict:
    """Ensure recipe + starting on_hand for the depletion demo."""
    location_id = location_id or default_location_id()
    ensure_default_location(session, location_id=location_id)
    now = datetime.now(timezone.utc)

    inventory = session.get(
        InventoryItemRecord,
        {"location_id": location_id, "id": DEMO_INVENTORY_ITEM_ID},
    )
    if inventory is None:
        raise RuntimeError(
            f"Inventory item {DEMO_INVENTORY_ITEM_ID!r} not found for {location_id}. "
            "Run ./scripts/bootstrap-db.sh first (xtraCHEF catalog sync)."
        )

    menu = session.get(
        MenuItemRecord,
        {"location_id": location_id, "id": DEMO_MENU_ITEM_ID},
    )
    if menu is None:
        session.add(
            MenuItemRecord(
                location_id=location_id,
                id=DEMO_MENU_ITEM_ID,
                name=DEMO_MENU_ITEM_NAME,
                category="Food",
                menu_group="Course 1",
                updated_at=now,
            )
        )
    else:
        menu.name = DEMO_MENU_ITEM_NAME
        menu.updated_at = now

    recipe = session.get(
        RecipeLineRecord,
        {
            "location_id": location_id,
            "menu_item_id": DEMO_MENU_ITEM_ID,
            "inventory_item_id": DEMO_INVENTORY_ITEM_ID,
        },
    )
    if recipe is None:
        session.add(
            RecipeLineRecord(
                location_id=location_id,
                menu_item_id=DEMO_MENU_ITEM_ID,
                inventory_item_id=DEMO_INVENTORY_ITEM_ID,
                qty_per_serving=DEMO_QTY_PER_SERVING,
                waste_factor=0.0,
            )
        )
    else:
        recipe.qty_per_serving = DEMO_QTY_PER_SERVING
        recipe.waste_factor = 0.0

    inventory.name = inventory.name or "Worcestershire sauce"
    inventory.on_hand = DEMO_STARTING_ON_HAND
    inventory.last_count_source = "demo"
    inventory.last_counted_at = now
    inventory.updated_at = now
    session.commit()

    expected_used = DEMO_SALES_QTY * DEMO_QTY_PER_SERVING
    return {
        "locationId": location_id,
        "ingredient": inventory.name,
        "inventoryItemId": DEMO_INVENTORY_ITEM_ID,
        "menuItem": DEMO_MENU_ITEM_NAME,
        "startingOnHand": DEMO_STARTING_ON_HAND,
        "salesQty": DEMO_SALES_QTY,
        "qtyPerServing": DEMO_QTY_PER_SERVING,
        "expectedUsed": expected_used,
        "expectedOnHandAfter": DEMO_STARTING_ON_HAND - expected_used,
        "businessDate": DEMO_BUSINESS_DATE.isoformat(),
    }


def run_demo(*, location_id: str | None = None, force: bool = True) -> dict:
    """Reset demo state, simulate SFTP drop, pull, ingest, and deplete."""
    if not DEMO_CSV.is_file():
        raise FileNotFoundError(f"Demo CSV missing: {DEMO_CSV}")

    location_id = location_id or default_location_id()
    config = ToastSftpConfig.from_env()
    paths = IngestPaths.from_repo()
    yyyymmdd = DEMO_BUSINESS_DATE.strftime("%Y%m%d")
    if config.host == "local":
        sftp_root = Path(config.private_key_path)
    else:
        import os

        sftp_root = Path(
            os.environ.get("TOAST_SFTP_LOCAL_ROOT", repo_root() / "data/dev/toast-sftp")
        ).resolve()
    dest_dir = sftp_root / config.export_id / yyyymmdd
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_csv = dest_dir / "ItemSelectionDetails.csv"
    dest_csv.write_bytes(DEMO_CSV.read_bytes())

    from pantry_engine.db.session import get_session_factory
    from pantry_engine.ingest.runs import RunStatus

    factory = get_session_factory()
    with factory() as session:
        setup = setup_demo_state(session, location_id=location_id)

    client = get_toast_downloader(config)
    pull = pull_item_selection(
        business_date=DEMO_BUSINESS_DATE,
        downloader=client,
        paths=paths,
        skip_if_unchanged=not force,
    )
    if pull.status != RunStatus.SUCCESS:
        raise RuntimeError(f"Toast pull failed: {pull.message}")

    applied = apply_pulled_sales(
        DEMO_BUSINESS_DATE,
        paths=paths,
        location_id=location_id,
    )

    with factory() as session:
        row = session.get(
            InventoryItemRecord,
            {"location_id": location_id, "id": DEMO_INVENTORY_ITEM_ID},
        )
        ending_on_hand = row.on_hand if row else None

    return {
        "setup": setup,
        "pull": {"status": pull.status.value, "message": pull.message},
        "apply": applied,
        "endingOnHand": ending_on_hand,
        "lookFor": setup["ingredient"],
    }
