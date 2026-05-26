from __future__ import annotations

import re
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

# pantry_eda lives in data_analysis/notebooks/lib
_LIB = Path(__file__).resolve().parents[2] / "data_analysis" / "notebooks" / "lib"
if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))

import pantry_eda  # noqa: E402

FOOD_CATEGORY_HINTS = (
    "produce",
    "seafood",
    "meat",
    "protein",
    "dairy",
    "dry goods",
    "food",
)
EXCLUDE_DESCRIPTION_PHRASES = ("purchase summary",)
NON_FOOD_CATEGORY_HINTS = (
    "restaurant supplies",
    "kitchen supplies",
    "chemicals",
    "dinnerware",
    "carryout",
    "paper",
    "bar supplies",
    "supplies & disposables",
)
DEFAULT_MAX_ITEMS = 10
OVERSTOCK_RATIO = 1.5
VARIANCE_THRESHOLD = 0.10
ESTIMATE_MULTIPLIERS = {"low": 0.33, "ok": 1.0, "high": 1.5}


@dataclass(frozen=True)
class QuickCountItem:
    id: str
    name: str
    category: str
    priority: str
    score: float
    reasons: list[str]
    expected_on_hand: float
    expected_display: str
    par_level: float
    par_display: str
    count_units: list[str]
    default_count_unit: str
    weighable: bool
    vendor: str | None
    flags: dict[str, bool]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "priority": self.priority,
            "score": self.score,
            "reasons": self.reasons,
            "expectedOnHand": self.expected_on_hand,
            "expectedDisplay": self.expected_display,
            "parLevel": self.par_level,
            "parDisplay": self.par_display,
            "countUnits": self.count_units,
            "defaultCountUnit": self.default_count_unit,
            "weighable": self.weighable,
            "vendor": self.vendor,
            "flags": self.flags,
        }


def _tokenize(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]{3,}", text.lower()) if len(t) >= 3}


def _is_food_row(row: pd.Series) -> bool:
    desc = str(row.get("item_description", "")).lower()
    if any(p in desc for p in EXCLUDE_DESCRIPTION_PHRASES):
        return False
    cat = str(row.get("category", "")).lower()
    cgroup = str(row.get("category_group", "")).lower()
    combined = f"{cat} {cgroup}"
    if any(p in combined for p in NON_FOOD_CATEGORY_HINTS):
        return False
    return any(h in combined for h in FOOD_CATEGORY_HINTS)


def _normalize_uom(uom: object) -> str:
    raw = str(uom or "").strip().lower()
    mapping = {
        "cs": "case",
        "case": "case",
        "ca": "case",
        "lb": "lb",
        "ea": "each",
        "each": "each",
        "piece": "each",
        "btl": "each",
        "bottle": "each",
        "gal": "gal",
        "bag": "bag",
    }
    return mapping.get(raw, raw or "each")


def _display_qty(value: float, unit: str) -> str:
    rounded = round(value, 1) if value % 1 else int(value)
    return f"{rounded} {unit}"


def _default_par(row: pd.Series, unit: str) -> float:
    weighable = str(row.get("weighable", "")).lower() == "true"
    if weighable or unit == "lb":
        return 20.0
    if unit in ("case", "gal"):
        return 2.0
    return 6.0


def _count_units_for_row(row: pd.Series, unit: str) -> list[str]:
    units = ["estimate"]
    if unit == "lb":
        units = ["lb", "case", "estimate"]
    elif unit == "case":
        units = ["case", "each", "estimate"]
    else:
        units = [unit, "each", "case", "estimate"]
    # stable unique order
    seen: set[str] = set()
    ordered: list[str] = []
    for u in units:
        if u not in seen:
            seen.add(u)
            ordered.append(u)
    return ordered


def _dedupe_food_items(food: pd.DataFrame) -> pd.DataFrame:
    food = food.copy()
    food["_group_key"] = food["product_s"].fillna("").astype(str).str.strip()
    food.loc[food["_group_key"] == "", "_group_key"] = food["item_key"]
    food = food.sort_values("last_purchased_date", ascending=False, na_position="last")
    return food.drop_duplicates(subset="_group_key", keep="first")


def _top_menu_tokens(pos_df: pd.DataFrame, top_n: int = 40) -> Counter[str]:
    if pos_df.empty:
        return Counter()
    grouped = (
        pos_df.groupby("menu_item_key", as_index=False)
        .agg(qty=("qty", "sum"), menu_item=("menu_item", "first"))
        .sort_values("qty", ascending=False)
        .head(top_n)
    )
    tokens: Counter[str] = Counter()
    for _, row in grouped.iterrows():
        for token in _tokenize(str(row["menu_item"])):
            tokens[token] += float(row["qty"])
    return tokens


def _pos_match_score(row: pd.Series, menu_tokens: Counter[str]) -> float:
    if not menu_tokens:
        return 0.0
    text = " ".join(
        [
            str(row.get("item_description", "")),
            str(row.get("product_s", "")),
            str(row.get("item_key", "")),
        ]
    ).lower()
    item_tokens = _tokenize(text)
    if not item_tokens:
        return 0.0
    score = 0.0
    for token in item_tokens:
        if token in menu_tokens:
            score += menu_tokens[token]
    return score


def _category_boost(row: pd.Series) -> float:
    combined = f"{row.get('category', '')} {row.get('category_group', '')}".lower()
    if any(k in combined for k in ("seafood", "produce")):
        return 3.0
    if any(k in combined for k in ("meat", "protein", "dairy")):
        return 2.0
    return 1.0


def _recency_boost(row: pd.Series, today: date) -> float:
    purchased = row.get("last_purchased_date")
    if pd.isna(purchased):
        return 0.0
    if isinstance(purchased, pd.Timestamp):
        purchased_date = purchased.date()
    elif isinstance(purchased, datetime):
        purchased_date = purchased.date()
    elif isinstance(purchased, date):
        purchased_date = purchased
    else:
        return 0.0
    days = (today - purchased_date).days
    if days <= 7:
        return 3.0
    if days <= 30:
        return 2.0
    if days <= 90:
        return 1.0
    return 0.0


def _priority_for_score(score: float, max_score: float) -> str:
    if max_score <= 0:
        return "medium"
    ratio = score / max_score
    if ratio >= 0.85:
        return "critical"
    if ratio >= 0.55:
        return "high"
    return "medium"


def _build_reasons(
    row: pd.Series,
    pos_score: float,
    menu_tokens: Counter[str],
) -> list[str]:
    reasons: list[str] = []
    text = " ".join(
        [
            str(row.get("item_description", "")),
            str(row.get("product_s", "")),
        ]
    ).lower()
    if pos_score > 0 and menu_tokens:
        matched = [t for t in _tokenize(text) if t in menu_tokens][:2]
        if matched:
            reasons.append(f"Menu velocity ({', '.join(matched)})")
    price = row.get("last_purchased_price")
    if pd.notna(price) and float(price) >= 100:
        reasons.append("High purchase cost")
    combined = f"{row.get('category', '')}".lower()
    if "seafood" in combined or "produce" in combined:
        reasons.append("Prep-critical category")
    purchased = row.get("last_purchased_date")
    if pd.notna(purchased):
        reasons.append("Recently purchased")
    if not reasons:
        reasons.append("Active inventory item")
    return reasons[:3]


def _compute_flags(
    on_hand: float,
    par: float,
    expected: float,
    category: str,
) -> dict[str, bool]:
    daily_usage = max(par / 3.0, 0.1)
    combined = category.lower()
    nearing_expiration = any(k in combined for k in ("produce", "seafood", "dairy"))
    return {
        "belowPar": on_hand < par,
        "likelyRunOutToday": on_hand < daily_usage,
        "overstocked": on_hand > par * OVERSTOCK_RATIO,
        "nearingExpiration": nearing_expiration and on_hand > 0,
        "countMismatch": False,
        "orderToday": on_hand < par * 0.5,
    }


def build_quick_count_items(
    *,
    inventory: dict[str, float] | None = None,
    par_overrides: dict[str, float] | None = None,
    max_items: int = DEFAULT_MAX_ITEMS,
    today: date | None = None,
) -> list[dict[str, Any]]:
    today = today or date.today()
    inventory = inventory or {}
    par_overrides = par_overrides or {}

    xchef = pantry_eda.read_xtrachef_item_library()
    pos = pantry_eda.read_pos_item_selections()

    food = xchef[xchef.apply(_is_food_row, axis=1)].copy()
    food = _dedupe_food_items(food)
    menu_tokens = _top_menu_tokens(pos)

    if food.empty:
        return []

    scored_rows: list[tuple[float, pd.Series, float, list[str]]] = []
    for _, row in food.iterrows():
        pos_score = _pos_match_score(row, menu_tokens)
        price = float(row["last_purchased_price"]) if pd.notna(row["last_purchased_price"]) else 0.0
        cost_component = min(price / 50.0, 8.0) if price > 0 else 0.0
        score = (
            pos_score * 0.05
            + cost_component
            + _category_boost(row)
            + _recency_boost(row, today)
        )
        reasons = _build_reasons(row, pos_score, menu_tokens)
        scored_rows.append((score, row, pos_score, reasons))

    scored_rows.sort(key=lambda x: x[0], reverse=True)
    selected_rows: list[tuple[float, pd.Series, float, list[str]]] = []
    selected_token_sets: list[set[str]] = []
    for entry in scored_rows:
        if len(selected_rows) >= max_items:
            break
        row = entry[1]
        tokens = _tokenize(str(row.get("item_description", "")))
        if tokens and selected_token_sets:
            duplicate = False
            for existing in selected_token_sets:
                overlap = len(tokens & existing)
                union = len(tokens | existing)
                if union and overlap / union >= 0.6:
                    duplicate = True
                    break
            if duplicate:
                continue
        selected_rows.append(entry)
        if tokens:
            selected_token_sets.append(tokens)

    max_score = selected_rows[0][0] if selected_rows else 1.0

    items: list[QuickCountItem] = []
    for score, row, _pos_score, reasons in selected_rows:
        item_id = str(row["item_key"])
        unit = _normalize_uom(row.get("uom") or row.get("item_uom"))
        par = par_overrides.get(item_id, _default_par(row, unit))
        expected = inventory.get(item_id, par * 0.85)
        category = str(row.get("category_group") or row.get("category") or "Food")
        flags = _compute_flags(expected, par, expected, category)

        items.append(
            QuickCountItem(
                id=item_id,
                name=str(row["item_description"]),
                category=category,
                priority=_priority_for_score(score, max_score),
                score=score,
                reasons=reasons,
                expected_on_hand=expected,
                expected_display=_display_qty(expected, unit),
                par_level=par,
                par_display=_display_qty(par, unit),
                count_units=_count_units_for_row(row, unit),
                default_count_unit=unit,
                weighable=str(row.get("weighable", "")).lower() == "true",
                vendor=str(row["vendor_name"]) if pd.notna(row.get("vendor_name")) else None,
                flags=flags,
            )
        )

    return [item.to_dict() for item in items]


def resolve_actual_count(
    *,
    expected: float,
    par: float,
    mode: str,
    value: float | None = None,
) -> float:
    if mode == "confirm":
        return expected
    if mode == "estimate" and value is not None:
        mult = ESTIMATE_MULTIPLIERS.get(str(value).lower(), 1.0)
        return par * mult
    if mode == "numeric" and value is not None:
        return float(value)
    return expected


def evaluate_submission(
    *,
    expected: float,
    par: float,
    actual: float,
    category: str,
) -> dict[str, Any]:
    flags = _compute_flags(actual, par, expected, category)
    variance = 0.0 if expected == 0 else abs(actual - expected) / expected
    flags["countMismatch"] = variance > VARIANCE_THRESHOLD
    flagged = flags["countMismatch"]
    return {
        "actual": actual,
        "variance": round(variance, 4),
        "flagged": flagged,
        "flags": flags,
    }
