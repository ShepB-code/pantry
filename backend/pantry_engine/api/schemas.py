from typing import Literal

from pydantic import BaseModel


class QuickCountLineSubmission(BaseModel):
    itemId: str
    mode: Literal["confirm", "numeric", "estimate"]
    value: float | str | None = None
    unit: str | None = None


class ParLevelUpdate(BaseModel):
    parLevel: float


class IngredientNameUpdate(BaseModel):
    name: str


class RecipeLineInput(BaseModel):
    inventoryItemId: str
    qtyPerServing: float
    wasteFactor: float = 0.0


class RecipeReplaceBody(BaseModel):
    lines: list[RecipeLineInput]


class DirectDepletionBody(BaseModel):
    inventoryItemId: str
    qtyPerServing: float = 1.0
