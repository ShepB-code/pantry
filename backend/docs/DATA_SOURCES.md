# Where data comes from (menu vs ingredients)

This is the short reference for **what comes from Toast**, **what comes from xtraCHEF**, and how they connect. Read this when the UI labels feel confusing.

## One sentence

- **Menu items** = what you **sell** (Toast POS).
- **Ingredients** = what you **stock** (xtraCHEF catalog → `inventory_items`).
- **Recipes** = your manual link: “this sale uses these ingredients.”

There is **no separate `ingredients` table**. “Ingredient” in the UI is a row in **`inventory_items`**.

---

## Side-by-side

| | Menu items | Ingredients (inventory) |
|--|------------|-------------------------|
| **Real-world source** | Toast POS | xtraCHEF (item library / invoices later) |
| **CSV / files** | `data/toast/pos/{location}/MenuItem_Export.csv` | `data/toast/xtraCHEF/{location}/*Item_Detail_Report*.csv` |
| | `data/toast/pos/{location}/ItemSelectionDetails*.csv` (sales) | |
| **Database table** | `menu_items` | `inventory_items` |
| **Stable ID** | `menu_items.id` (POS menu id) | `inventory_items.id` (slug from xtraCHEF description) |
| **UI** | Menu & Recipes (pick dish) | Inventory → Current Stock; recipe ingredient picker |
| **Typical use** | Sales, recipes, depletion | On-hand, par, quick count, (future) receiving |

---

## Flow diagram

```text
                    TOAST                           xtraCHEF
                      │                                 │
         MenuItem_Export.csv              Item_Detail_Report.csv
         ItemSelectionDetails.csv                    │
                      │                                 │
                      ▼                                 ▼
               ┌─────────────┐                 ┌─────────────────┐
               │ menu_items  │                 │ inventory_items │
               │  (POS ids)  │                 │  (stock SKUs)   │
               └──────┬──────┘                 └────────┬────────┘
                      │                                   │
                      │         recipe_lines              │
                      │    (you configure in UI)          │
                      └──────────────┬────────────────────┘
                                     │
                                     ▼
                            pos_sales_daily
                            (qty sold per day)
                                     │
                                     ▼
                         depletion → on_hand ↓
                         (only if recipe or
                          direct link exists)
```

**Invoices (not built yet):** will add to **`inventory_items.on_hand`** directly at ingredient level — no menu item involved.

---

## Menu items (Toast POS)

### What they represent

A line on a guest check: “Dipping Sauce”, “Bulgogi bibimbap”, “Scallop”, etc.

### How they get into Pantry

| Path | File / API | What it fills |
|------|------------|----------------|
| Seed / export | `MenuItem_Export.csv` | `menu_items` (Toast numeric Item ID + name) |
| Sales ingest | `ItemSelectionDetails*.csv` or SFTP pull | `menu_items` + **`pos_sales_daily`** |

### POS id (important)

Pantry keys menu items by **`menu_items.id`**.

- From **sales** files, the id is usually a **slug from the name** (e.g. `dipping_sauce`, `chicken_tender_sandwich`).
- From **MenuItem_Export**, the id is often Toast’s **long numeric** Item ID.

**For recipes and depletion**, the id must match what appears in **`pos_sales_daily`** (sales path). When in doubt, use **“Only items with POS sales”** in the recipe builder.

### Menu items are not ingredients

Toast does **not** tell Pantry which xtraCHEF SKU was used. That’s what **recipes** are for.

---

## Ingredients (xtraCHEF → inventory)

### What they represent

Purchasable / countable stock: “WORCESTERSHIRE SAUCE”, “Salmon fillet”, etc.

### How they get into Pantry

| Path | What it fills |
|------|----------------|
| `POST /api/inventory/sync-catalog` or API startup | `inventory_items` from latest Item Detail export |
| `./scripts/bootstrap-db.sh` | Same, on first setup |

### Two names in the Inventory UI (same row)

| UI column | DB column | Source |
|-----------|-----------|--------|
| **Ingredient** | `name` | Kitchen-friendly label (`Product(s)` when present, rules, or manual edit) |
| **Inventory Item** | `catalog_name` | Raw xtraCHEF **Item Description** |

### Ingredient id

`inventory_items.id` = stable slug from xtraCHEF description (e.g. `worcestershire sauce`). Use this in **recipe_lines**, not the display name.

---

## Recipes (you configure — not from a vendor export)

Recipes are **not** downloaded from Toast or xtraCHEF. You define them in **Menu & Recipes** (or SQL).

Stored as:

```text
recipe_lines
  menu_item_id      → menu_items.id     (what sold)
  inventory_item_id → inventory_items.id  (what depletes)
  qty_per_serving   → how much per 1 sale
```

**Singular sale** (menu item ≈ one SKU, e.g. scallop): use **direct depletion** on `menu_items` (`direct_inventory_item_id`) instead of multiple lines.

### What the recipe table shows

The Menu & Recipes table lists only menu items that have a **saved recipe** or **direct link** — not your full Toast menu.

---

## When something sells (POS event)

For each `menu_item_id` in **`pos_sales_daily`** for that day:

| Step | Rule |
|------|------|
| 1 | If **`recipe_lines`** exist for that menu item → deplete each ingredient (qty sold × qty per serving). |
| 2 | Else if **`menu_items.direct_inventory_item_id`** is set → deplete that one ingredient. |
| 3 | Else → **log only** (sale is stored; `on_hand` unchanged). |

CLI: `toast-pull --apply` runs ingest + this logic.

---

## Common confusions

| Confusion | Clarification |
|-----------|----------------|
| “Ingredient” vs “Inventory Item” in the table | Same DB row; two labels (kitchen vs vendor text). |
| I saved a recipe but don’t see the dish | Table only shows items **with** a recipe/direct link; need menu item + at least one ingredient with qty > 0. |
| Recipe saved but depletion doesn’t move stock | `menu_item_id` in recipe must match **`pos_sales_daily`** (use sold items from POS, not only export ids). |
| Toast gives me ingredients | No — Toast gives **menu items**. xtraCHEF gives **ingredients**. |
| Every menu item needs a recipe | No — only items where you want automatic depletion. |

---

## File cheat sheet (`perilla` example)

```text
data/toast/
  xtraCHEF/perilla/*Item_Detail_Report*.csv   → inventory_items
  pos/perilla/MenuItem_Export.csv             → menu_items (export ids)
  pos/perilla/ItemSelectionDetails*.csv       → menu_items + pos_sales_daily (POS ids)
```

---

## Related docs

- [INVENTORY.md](./INVENTORY.md) — APIs, sync behavior, field list
- [DATABASE.md](./DATABASE.md) — Postgres setup, migrations
- [RUNNING.md](./RUNNING.md) — bootstrap, API, CLI
- [data/toast/README.md](../../data/toast/README.md) — folder layout on disk
