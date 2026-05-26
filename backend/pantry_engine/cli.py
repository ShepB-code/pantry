from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta


def main(argv: list[str] | None = None) -> int:
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

    args = parser.parse_args(argv)

    if args.command == "toast-pull":
        return _cmd_toast_pull(args)
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


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


if __name__ == "__main__":
    raise SystemExit(main())
