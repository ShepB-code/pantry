from pantry_engine.api.pantry_eda import ensure_pantry_eda_path
from pantry_engine.db import init_db
from pantry_engine.db.catalog_sync import sync_xtrachef_from_exports
from pantry_engine.db.pos_sales_sync import ingest_menu_item_export_file
from pantry_engine.db.seed import ensure_default_location
from pantry_engine.db.session import get_session_factory


def on_startup() -> None:
    init_db()
    ensure_pantry_eda_path()
    import pantry_eda

    with get_session_factory()() as session:
        loc_id = ensure_default_location(session)
        try:
            menu_export = pantry_eda.pos_location_dir(location_id=loc_id) / "MenuItem_Export.csv"
            if menu_export.exists():
                result = ingest_menu_item_export_file(
                    session, csv_path=menu_export, location_id=loc_id
                )
                print(f"Toast menu export sync: {result.get('menuItemsUpserted', 0)} upserted")
        except Exception as exc:
            session.rollback()
            print(f"Toast menu export sync skipped: {exc}")

        try:
            created, updated = sync_xtrachef_from_exports(session, loc_id)
            print(f"xtraCHEF catalog sync: {created} created, {updated} updated")
        except Exception as exc:
            session.rollback()
            print(f"xtraCHEF catalog sync skipped: {exc}")
