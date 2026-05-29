from fastapi import APIRouter, HTTPException

from pantry_engine.api.deps import inventory_repo, quick_count_repo
from pantry_engine.api.schemas import (
    IngredientNameUpdate,
    ParLevelUpdate,
    QuickCountLineSubmission,
)
from pantry_engine.db.catalog_sync import sync_xtrachef_from_exports
from pantry_engine.db.seed import default_location_id
from pantry_engine.db.session import get_session_factory
from pantry_engine.quick_count import evaluate_submission, resolve_actual_count

router = APIRouter(tags=["inventory"])


@router.get("/api/inventory")
def get_inventory():
    repo = inventory_repo()
    return {
        "locationId": repo.location_id,
        "items": repo.list_items(),
        "onHand": repo.on_hand_map(),
    }


@router.post("/api/inventory/sync-catalog")
def sync_catalog():
    with get_session_factory()() as session:
        created, updated = sync_xtrachef_from_exports(session, default_location_id())
    return {"created": created, "updated": updated}


@router.patch("/api/inventory/{item_id}/par")
def update_inventory_par(item_id: str, body: ParLevelUpdate):
    try:
        return inventory_repo().set_par_level(item_id, body.parLevel)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Item not found") from exc


@router.patch("/api/inventory/{item_id}/name")
def update_inventory_name(item_id: str, body: IngredientNameUpdate):
    try:
        return inventory_repo().set_name(item_id, body.name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Item not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/inventory/quick-count")
def get_quick_count():
    return quick_count_repo().build_session_payload()


@router.post("/api/inventory/quick-count/lines")
def submit_quick_count_line(body: QuickCountLineSubmission):
    qc = quick_count_repo()
    payload = qc.build_session_payload()
    if payload["completed"]:
        raise HTTPException(status_code=400, detail="Quick count already completed for today")

    item = next((i for i in payload["items"] if i["id"] == body.itemId), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not in today's quick count list")

    if body.mode == "numeric":
        if body.value is None:
            raise HTTPException(status_code=400, detail="Numeric count requires a value")
        actual = resolve_actual_count(
            expected=item["expectedOnHand"],
            par=item["parLevel"],
            mode="numeric",
            value=float(body.value),
        )
    elif body.mode == "estimate":
        if not isinstance(body.value, str):
            raise HTTPException(status_code=400, detail="Estimate requires low, ok, or high")
        actual = resolve_actual_count(
            expected=item["expectedOnHand"],
            par=item["parLevel"],
            mode="estimate",
            value=body.value,
        )
    else:
        actual = resolve_actual_count(
            expected=item["expectedOnHand"],
            par=item["parLevel"],
            mode="confirm",
        )

    evaluation = evaluate_submission(
        expected=item["expectedOnHand"],
        par=item["parLevel"],
        actual=actual,
        category=item["category"],
    )

    try:
        return qc.submit_line(
            item_id=body.itemId,
            mode=body.mode,
            unit=body.unit or item["defaultCountUnit"],
            name=item["name"],
            expected=item["expectedOnHand"],
            actual=actual,
            flagged=evaluation["flagged"],
            flags=evaluation["flags"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/inventory/quick-count/reset")
def reset_quick_count():
    return quick_count_repo().reset_session()


@router.post("/api/inventory/quick-count/complete")
def complete_quick_count():
    try:
        return quick_count_repo().complete_session()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
