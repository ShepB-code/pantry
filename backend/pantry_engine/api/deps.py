from pantry_engine.db.inventory_repo import InventoryRepository
from pantry_engine.db.quick_count_repo import QuickCountRepository
from pantry_engine.db.recipe_repo import RecipeRepository


def inventory_repo() -> InventoryRepository:
    return InventoryRepository()


def quick_count_repo() -> QuickCountRepository:
    return QuickCountRepository(inventory_repo=inventory_repo())


def recipe_repo() -> RecipeRepository:
    return RecipeRepository()
