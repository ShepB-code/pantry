from fastapi import APIRouter, HTTPException

from pantry_engine.api.deps import recipe_repo
from pantry_engine.api.pantry_eda import ensure_pantry_eda_path
from pantry_engine.api.schemas import DirectDepletionBody, RecipeReplaceBody
from pantry_engine.db.seed import default_location_id
from pantry_engine.db.session import get_session_factory

router = APIRouter(tags=["menu"])


@router.get("/api/menu/items")
def list_menu_items(q: str | None = None, sold_only: bool = False):
    return recipe_repo().list_menu_items(search=q, sold_only=sold_only)


@router.get("/api/menu/inventory-options")
def list_recipe_inventory_options():
    return recipe_repo().list_inventory_options()


@router.get("/api/menu/recipes")
def list_recipes_overview():
    return recipe_repo().list_overview()


@router.post("/api/menu/sync-export")
def sync_menu_export():
    ensure_pantry_eda_path()
    import pantry_eda

    from pantry_engine.db.pos_sales_sync import ingest_menu_item_export_file

    loc_id = default_location_id()
    menu_export = pantry_eda.pos_location_dir(location_id=loc_id) / "MenuItem_Export.csv"
    if not menu_export.exists():
        raise HTTPException(
            status_code=404,
            detail=f"MenuItem_Export.csv not found at {menu_export}",
        )
    with get_session_factory()() as session:
        return ingest_menu_item_export_file(session, csv_path=menu_export, location_id=loc_id)


@router.get("/api/menu/{menu_item_id}/recipe")
def get_menu_recipe(menu_item_id: str):
    config = recipe_repo().get_menu_depletion(menu_item_id)
    if config is None:
        raise HTTPException(status_code=404, detail="Menu item not found")
    return config


@router.put("/api/menu/{menu_item_id}/recipe")
def put_menu_recipe(menu_item_id: str, body: RecipeReplaceBody):
    try:
        return recipe_repo().replace_recipe(
            menu_item_id,
            [line.model_dump() for line in body.lines],
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/api/menu/{menu_item_id}/direct-depletion")
def put_menu_direct_depletion(menu_item_id: str, body: DirectDepletionBody):
    try:
        return recipe_repo().set_direct_depletion(
            menu_item_id,
            inventory_item_id=body.inventoryItemId,
            qty_per_serving=body.qtyPerServing,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/api/menu/{menu_item_id}/direct-depletion")
def delete_menu_direct_depletion(menu_item_id: str):
    try:
        return recipe_repo().clear_direct_depletion(menu_item_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
