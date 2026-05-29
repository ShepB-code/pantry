from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Pantry ingestion utilities (Toast nightly SFTP exports)."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    toast = sub.add_parser(
        "toast-pull",
        help="Download ItemSelectionDetails.csv from Toast SFTP",
    )
    toast.add_argument(
        "--date",
        type=_parse_date,
        help="Business date (YYYY-MM-DD). Default: yesterday",
    )
    toast.add_argument(
        "--days",
        type=int,
        default=None,
        help="Pull each day in the last N days ending yesterday (or --end)",
    )
    toast.add_argument(
        "--end",
        type=_parse_date,
        help="Last business date when using --days",
    )
    toast.add_argument(
        "--force",
        action="store_true",
        help="Re-download even if this date was already ingested successfully",
    )
    toast.add_argument(
        "--apply",
        action="store_true",
        help="After pull, ingest sales into DB and apply recipe depletion to on_hand",
    )

    seed = sub.add_parser(
        "db-seed",
        help="Seed the database from files under data/toast/",
    )
    seed.add_argument(
        "--location",
        default=None,
        help="Location id / folder slug (default: PANTRY_DEFAULT_LOCATION_ID)",
    )
    seed.add_argument(
        "--pos-file",
        action="append",
        default=[],
        help="Path to an ItemSelectionDetails CSV to ingest (repeatable).",
    )
    seed.add_argument(
        "--skip-xtrachef",
        action="store_true",
        help="Skip xtraCHEF inventory sync",
    )
    seed.add_argument(
        "--skip-menu-export",
        action="store_true",
        help="Skip Toast MenuItem_Export.csv sync",
    )
    seed.add_argument(
        "--skip-pos",
        action="store_true",
        help="Skip ItemSelectionDetails*.csv backfill",
    )

    args = parser.parse_args(argv)

    if args.command == "toast-pull":
        return _cmd_toast_pull(args)
    if args.command == "db-seed":
        return _cmd_db_seed(args)
    return 1


def _cmd_toast_pull(args: argparse.Namespace) -> int:
    from pantry_engine.ingest.paths import IngestPaths
    from pantry_engine.ingest.runs import RunStatus
    from pantry_engine.ingest.toast_sftp.config import ToastSftpConfig
    from pantry_engine.ingest.toast_sftp.downloader import get_toast_downloader
    from pantry_engine.ingest.toast_sftp.pull import (
        pull_item_selection,
        pull_recent_days,
    )

    try:
        config = ToastSftpConfig.from_env()
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2

    paths = IngestPaths.from_repo()
    client = get_toast_downloader(config)
    skip = not args.force

    if args.date:
        results = [
            pull_item_selection(
                business_date=args.date,
                downloader=client,
                paths=paths,
                skip_if_unchanged=skip,
            )
        ]
    else:
        days = args.days if args.days is not None else 7
        end = args.end or (date.today() - timedelta(days=1))
        results = pull_recent_days(
            downloader=client,
            days=days,
            end_date=end,
            paths=paths,
            skip_if_unchanged=skip,
        )

    exit_code = 0
    for result in results:
        label = result.business_date.isoformat()
        if result.status == RunStatus.SUCCESS:
            print(f"{label}: OK — {result.message}")
            if args.apply:
                from pantry_engine.ingest.toast_sftp.apply import apply_pulled_sales

                try:
                    applied = apply_pulled_sales(result.business_date, paths=paths)
                    dep = applied.get("depletion") or {}
                    print(f"{label}: APPLY — {dep.get('message', applied['ingest'])}")
                except Exception as exc:
                    print(f"{label}: APPLY FAILED — {exc}", file=sys.stderr)
                    exit_code = 1
        elif result.status == RunStatus.SKIPPED:
            print(f"{label}: SKIP — {result.message}")
        else:
            print(f"{label}: FAIL — {result.message}", file=sys.stderr)
            exit_code = 1
    return exit_code


def _cmd_db_seed(args: argparse.Namespace) -> int:
    # pantry_eda lives in data_analysis/notebooks/lib (repo root)
    from pantry_engine.root import repo_root

    lib_path = repo_root() / "data_analysis" / "notebooks" / "lib"
    if str(lib_path) not in sys.path:
        sys.path.append(str(lib_path))

    import pantry_eda

    from pantry_engine.db.catalog_sync import sync_xtrachef_from_exports
    from pantry_engine.db.pos_sales_sync import (
        ingest_item_selection_file_all_dates,
        ingest_menu_item_export_file,
    )
    from pantry_engine.db.seed import ensure_default_location
    from pantry_engine.db.session import get_session_factory, init_db

    init_db()
    location_id = args.location

    with get_session_factory()() as session:
        loc_id = ensure_default_location(session, location_id=location_id)

        if not args.skip_menu_export:
            menu_export = pantry_eda.pos_location_dir(location_id=loc_id) / "MenuItem_Export.csv"
            if menu_export.exists():
                out = ingest_menu_item_export_file(
                    session, csv_path=menu_export, location_id=loc_id
                )
                print(f"menu export: {out.get('menuItemsUpserted', 0)} upserted")
            else:
                print(f"menu export: skipped (missing {menu_export})")

        if not args.skip_xtrachef:
            try:
                created, updated = sync_xtrachef_from_exports(session, loc_id)
                print(f"xtrachef: {created} created, {updated} updated")
            except Exception as exc:
                session.rollback()
                print(f"xtrachef: skipped ({exc})")

        if args.skip_pos:
            print("pos: skipped (--skip-pos)")
            return 0

        # POS backfill from explicit files, else ingest any ItemSelectionDetails*.csv in the location folder.
        pos_files = [Path(p).expanduser() for p in args.pos_file]
        if not pos_files:
            loc_root = pantry_eda.pos_location_dir(location_id=loc_id)
            pos_files = sorted(loc_root.glob("ItemSelectionDetails*.csv"))

        if not pos_files:
            print("pos: skipped (no ItemSelectionDetails*.csv files found)")
            return 0

        total_days = 0
        for path in pos_files:
            out = ingest_item_selection_file_all_dates(
                session, csv_path=path, location_id=loc_id
            )
            total_days += int(out.get("days") or 0)
            print(f"pos: {path.name} — {out.get('days', 0)} day(s), {out.get('salesLines', 0)} lines")
        print(f"pos: total days ingested: {total_days}")

    return 0


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


if __name__ == "__main__":
    raise SystemExit(main())
