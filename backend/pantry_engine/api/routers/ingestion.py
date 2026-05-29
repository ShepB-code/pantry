from datetime import date, timedelta

from fastapi import APIRouter, HTTPException

from pantry_engine.ingest.paths import IngestPaths
from pantry_engine.ingest.runs import IngestionRunStore, RunStatus
from pantry_engine.ingest.toast_sftp.apply import apply_pulled_sales
from pantry_engine.ingest.toast_sftp.config import ToastSftpConfig
from pantry_engine.ingest.toast_sftp.downloader import get_toast_downloader
from pantry_engine.ingest.toast_sftp.pull import pull_item_selection, pull_recent_days
from pantry_engine.root import repo_root

router = APIRouter(tags=["ingestion"])


@router.post("/api/ingestion/toast/apply")
def ingestion_toast_apply(business_date: str):
    try:
        parsed = date.fromisoformat(business_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="business_date must be YYYY-MM-DD") from exc
    try:
        return apply_pulled_sales(parsed)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/api/ingestion/toast/pull")
def ingestion_toast_pull(
    days: int = 7,
    force: bool = False,
    business_date: str | None = None,
    apply_sales: bool = False,
):
    try:
        config = ToastSftpConfig.from_env()
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if days < 1 or days > 7:
        raise HTTPException(
            status_code=400,
            detail="days must be between 1 and 7 (Toast SFTP retention window)",
        )

    parsed_date: date | None = None
    if business_date:
        try:
            parsed_date = date.fromisoformat(business_date)
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail="business_date must be YYYY-MM-DD",
            ) from exc

    paths = IngestPaths.from_repo(repo_root())
    downloader = get_toast_downloader(config)
    if parsed_date:
        results = [
            pull_item_selection(
                business_date=parsed_date,
                downloader=downloader,
                paths=paths,
                skip_if_unchanged=not force,
            )
        ]
    else:
        end = date.today() - timedelta(days=1)
        results = pull_recent_days(
            downloader=downloader,
            days=days,
            end_date=end,
            paths=paths,
            skip_if_unchanged=not force,
        )

    applied: list[dict] = []
    if apply_sales:
        for result in results:
            if result.status.value != "success" or not result.local_path:
                continue
            try:
                applied.append(apply_pulled_sales(result.business_date, paths=paths))
            except Exception as exc:
                applied.append(
                    {"businessDate": result.business_date.isoformat(), "error": str(exc)}
                )

    return {
        "results": [
            {
                "businessDate": r.business_date.isoformat(),
                "status": r.status.value,
                "rowCount": r.row_count,
                "message": r.message,
                "skipped": r.skipped,
                "path": str(r.local_path) if r.local_path else None,
            }
            for r in results
        ],
        "successCount": sum(1 for r in results if r.status == RunStatus.SUCCESS),
        "failedCount": sum(1 for r in results if r.status == RunStatus.FAILED),
        "applied": applied if apply_sales else None,
    }


@router.get("/api/ingestion/runs")
def ingestion_runs(source: str | None = "toast_sftp", limit: int = 30):
    store = IngestionRunStore()
    runs = store.list_runs(source=source, limit=limit)
    return [
        {
            "id": run.id,
            "locationId": run.location_id,
            "source": run.source,
            "businessDate": run.business_date.isoformat(),
            "filename": run.filename,
            "status": run.status.value,
            "rowCount": run.row_count,
            "errorMessage": run.error_message,
            "finishedAt": run.finished_at.isoformat() if run.finished_at else None,
        }
        for run in runs
    ]
