export interface MenuItemOption {
  id: string;
  name: string;
  category: string | null;
  menuGroup: string | null;
  quantitySold: number;
}

export interface InventoryOption {
  id: string;
  name: string;
  inventoryItem: string;
  unit: string;
  category: string | null;
}

export interface RecipeLineDto {
  inventoryItemId: string;
  name: string;
  inventoryItem: string;
  qtyPerServing: number;
  wasteFactor: number;
  unit: string;
}

export interface RecipeDetail {
  menuItemId: string;
  menuItemName: string;
  category: string | null;
  lines: RecipeLineDto[];
}

export interface RecipeOverviewRow {
  menuItemId: string;
  dish: string;
  cat: string;
  quantitySold: number;
  depletionType?: "recipe" | "direct" | "none";
  popularity: string;
  popColor: string;
  ingredientCount: number;
  ingredients: {
    id: string;
    name: string;
    quantity: string;
    unit: string;
    unitCost: string;
    cost: string;
  }[];
  cost: string;
  price: string;
  margin: number;
  totalCost: string;
}

export async function fetchMenuItems(params?: {
  q?: string;
  soldOnly?: boolean;
}): Promise<MenuItemOption[]> {
  const search = new URLSearchParams();
  if (params?.q) search.set("q", params.q);
  if (params?.soldOnly) search.set("sold_only", "true");
  const qs = search.toString();
  const res = await fetch(`/api/menu/items${qs ? `?${qs}` : ""}`);
  if (!res.ok) throw new Error("Failed to load menu items");
  return res.json();
}

export async function fetchInventoryOptions(): Promise<InventoryOption[]> {
  const res = await fetch("/api/menu/inventory-options");
  if (!res.ok) throw new Error("Failed to load inventory items");
  return res.json();
}

export async function fetchRecipesOverview(): Promise<RecipeOverviewRow[]> {
  const res = await fetch("/api/menu/recipes");
  if (!res.ok) throw new Error("Failed to load recipes");
  return res.json();
}

export async function fetchRecipe(menuItemId: string): Promise<RecipeDetail> {
  const res = await fetch(`/api/menu/${encodeURIComponent(menuItemId)}/recipe`);
  if (!res.ok) throw new Error("Failed to load recipe");
  return res.json();
}

export async function saveRecipe(
  menuItemId: string,
  lines: { inventoryItemId: string; qtyPerServing: number; wasteFactor?: number }[],
): Promise<RecipeDetail> {
  const res = await fetch(`/api/menu/${encodeURIComponent(menuItemId)}/recipe`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ lines }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Failed to save recipe");
  }
  return res.json();
}
