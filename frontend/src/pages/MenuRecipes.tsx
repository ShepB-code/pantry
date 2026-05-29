import { Fragment, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { MetricCard } from "@/components/MetricCard";
import { cn } from "@/lib/utils";
import {
  ChevronDown,
  ChevronUp,
  Plus,
  Trash2,
  X,
  Minus,
  Save,
  ChevronRight,
  AlertTriangle,
  CheckCircle2,
  TrendingUp,
  Pencil,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  fetchInventoryOptions,
  fetchMenuItems,
  fetchRecipesOverview,
  fetchRecipe,
  saveRecipe,
  type RecipeOverviewRow,
} from "@/api/menu";
import { toast } from "sonner";
import { DataSourceBadge } from "@/components/DataSourceBadge";

interface PriceAlert {
  dish: string;
  currentFoodCostPct: number;
  targetFoodCostPct: number;
  currentMenuPrice: number;
  suggestedMenuPrice: number;
  triggerIngredient: string;
  dismissed: boolean;
  accepted: boolean;
}

const initialPriceAlerts: PriceAlert[] = [
  {
    dish: "Miso salmon bowl",
    currentFoodCostPct: 34.1,
    targetFoodCostPct: 30,
    currentMenuPrice: 24,
    suggestedMenuPrice: 26,
    triggerIngredient: "Salmon fillet (+10%)",
    dismissed: false,
    accepted: false,
  },
  {
    dish: "Ribeye (12oz)",
    currentFoodCostPct: 30.1,
    targetFoodCostPct: 28,
    currentMenuPrice: 52,
    suggestedMenuPrice: 54,
    triggerIngredient: "Ribeye Prime (+3.9%)",
    dismissed: false,
    accepted: false,
  },
];

interface DraftLine {
  rowId: string;
  inventoryItemId: string;
  qtyPerServing: string;
}

const blankLine = (): DraftLine => ({
  rowId: crypto.randomUUID(),
  inventoryItemId: "",
  qtyPerServing: "",
});

export default function MenuRecipes() {
  const queryClient = useQueryClient();
  const [expanded, setExpanded] = useState<string | null>(null);
  const [drawerState, setDrawerState] = useState<"closed" | "open" | "minimized">("closed");
  const [selectedMenuItemId, setSelectedMenuItemId] = useState("");
  const [menuSearch, setMenuSearch] = useState("");
  const [soldOnly, setSoldOnly] = useState(true);
  const [lines, setLines] = useState<DraftLine[]>([blankLine()]);
  const [priceAlerts, setPriceAlerts] = useState<PriceAlert[]>(initialPriceAlerts);
  const [alertsExpanded, setAlertsExpanded] = useState(true);

  const { data: recipes = [], isLoading } = useQuery({
    queryKey: ["menu-recipes"],
    queryFn: fetchRecipesOverview,
  });

  const { data: menuItems = [] } = useQuery({
    queryKey: ["menu-items", menuSearch, soldOnly],
    queryFn: () => fetchMenuItems({ q: menuSearch || undefined, soldOnly }),
    enabled: drawerState === "open",
  });

  const { data: inventoryOptions = [] } = useQuery({
    queryKey: ["recipe-inventory-options"],
    queryFn: fetchInventoryOptions,
    enabled: drawerState === "open",
  });

  const inventoryById = useMemo(
    () => new Map(inventoryOptions.map((i) => [i.id, i])),
    [inventoryOptions],
  );

  const selectedMenuItem = menuItems.find((m) => m.id === selectedMenuItemId);

  const saveMutation = useMutation({
    mutationFn: async () => {
      const payload = lines
        .filter((l) => l.inventoryItemId && parseFloat(l.qtyPerServing) > 0)
        .map((l) => ({
          inventoryItemId: l.inventoryItemId,
          qtyPerServing: parseFloat(l.qtyPerServing),
        }));
      return saveRecipe(selectedMenuItemId, payload);
    },
    onSuccess: (saved) => {
      queryClient.invalidateQueries({ queryKey: ["menu-recipes"] });
      toast.success(`Recipe saved for ${saved.menuItemName}`);
      closeDrawer();
    },
    onError: (err: Error) => {
      toast.error(err.message || "Failed to save recipe");
    },
  });

  const activeAlerts = priceAlerts.filter((a) => !a.dismissed && !a.accepted);

  const acceptPriceChange = (idx: number) => {
    setPriceAlerts((prev) =>
      prev.map((a, i) => (i === idx ? { ...a, accepted: true } : a)),
    );
  };

  const dismissAlert = (idx: number) => {
    setPriceAlerts((prev) =>
      prev.map((a, i) => (i === idx ? { ...a, dismissed: true } : a)),
    );
  };

  const openCreateDrawer = () => {
    setSelectedMenuItemId("");
    setMenuSearch("");
    setLines([blankLine()]);
    setDrawerState("open");
  };

  const openEditDrawer = async (menuItemId: string) => {
    setSoldOnly(false);
    const detail = await fetchRecipe(menuItemId);
    setSelectedMenuItemId(detail.menuItemId);
    setMenuSearch(detail.menuItemName);
    setLines(
      detail.lines.length
        ? detail.lines.map((l) => ({
            rowId: crypto.randomUUID(),
            inventoryItemId: l.inventoryItemId,
            qtyPerServing: String(l.qtyPerServing),
          }))
        : [blankLine()],
    );
    setDrawerState("open");
  };

  const closeDrawer = () => {
    setDrawerState("closed");
    setSelectedMenuItemId("");
    setMenuSearch("");
    setLines([blankLine()]);
  };

  const minimizeDrawer = () => setDrawerState("minimized");

  const updateLine = (rowId: string, patch: Partial<DraftLine>) =>
    setLines((prev) => prev.map((l) => (l.rowId === rowId ? { ...l, ...patch } : l)));

  const addLine = () => setLines((prev) => [...prev, blankLine()]);
  const removeLine = (rowId: string) =>
    setLines((prev) => (prev.length === 1 ? prev : prev.filter((l) => l.rowId !== rowId)));

  const canSave =
    selectedMenuItemId &&
    lines.some((l) => l.inventoryItemId && parseFloat(l.qtyPerServing) > 0);

  return (
    <div className="space-y-6 max-w-7xl">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Menu & Recipes</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Link Toast menu items to inventory ingredients for POS depletion.
          </p>
        </div>
        <Button onClick={openCreateDrawer} size="sm" disabled={drawerState === "open"}>
          <Plus className="h-4 w-4 mr-1" />
          Create Recipe
        </Button>
      </div>

      {activeAlerts.length > 0 && (
        <div className="rounded-lg border border-warning/30 bg-warning/5 overflow-hidden">
          <button
            onClick={() => setAlertsExpanded(!alertsExpanded)}
            className="w-full flex items-center justify-between px-5 py-3 hover:bg-warning/10 transition-colors text-left"
          >
            <div className="flex items-center gap-3 flex-wrap">
              <AlertTriangle className="h-4 w-4 text-warning flex-shrink-0" />
              <span className="text-sm font-medium">
                {activeAlerts.length} dish{activeAlerts.length > 1 ? "es are" : " is"} outside
                your target food cost range due to recent price changes
              </span>
              <DataSourceBadge source="mock" />
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-warning/20 text-warning">
                Action needed
              </span>
            </div>
            {alertsExpanded ? (
              <ChevronUp className="h-4 w-4 text-muted-foreground" />
            ) : (
              <ChevronDown className="h-4 w-4 text-muted-foreground" />
            )}
          </button>

          {alertsExpanded && (
            <div className="border-t border-warning/20 divide-y divide-warning/15">
              <div className="hidden md:grid grid-cols-[1.5fr_1fr_0.8fr_0.8fr_1fr_auto] gap-4 px-5 py-2 bg-warning/5 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                <div>Dish</div>
                <div>Current food cost</div>
                <div>Target</div>
                <div>Current price</div>
                <div>Suggested price</div>
                <div className="w-[140px]" />
              </div>

              {priceAlerts.map((alert, idx) => {
                if (alert.dismissed) return null;
                if (alert.accepted) {
                  return (
                    <div
                      key={idx}
                      className="grid grid-cols-[auto_1fr_auto_auto] gap-3 items-center px-5 py-3 bg-success/5"
                    >
                      <CheckCircle2 className="h-4 w-4 text-success" />
                      <span className="font-medium text-sm">{alert.dish}</span>
                      <span className="text-xs text-muted-foreground">
                        Menu price updated to ${alert.suggestedMenuPrice}
                      </span>
                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-success/10 text-success">
                        Margin restored
                      </span>
                    </div>
                  );
                }
                return (
                  <div
                    key={idx}
                    className="grid grid-cols-1 md:grid-cols-[1.5fr_1fr_0.8fr_0.8fr_1fr_auto] gap-4 items-center px-5 py-3"
                  >
                    <div>
                      <p className="font-medium text-sm">{alert.dish}</p>
                      <p className="text-[11px] text-muted-foreground mt-0.5">
                        Triggered by: {alert.triggerIngredient}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-destructive">
                        {alert.currentFoodCostPct}%
                      </p>
                      <p className="text-[10px] text-muted-foreground">food cost</p>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-muted-foreground">
                        &lt;{alert.targetFoodCostPct}%
                      </p>
                      <p className="text-[10px] text-muted-foreground">target</p>
                    </div>
                    <div>
                      <p className="text-sm font-medium">${alert.currentMenuPrice}</p>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <TrendingUp className="h-3.5 w-3.5 text-success" />
                      <div>
                        <p className="text-sm font-semibold text-success">
                          ${alert.suggestedMenuPrice}
                        </p>
                        <p className="text-[10px] text-muted-foreground">suggested</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-1 justify-end">
                      <button
                        onClick={() => acceptPriceChange(idx)}
                        className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors whitespace-nowrap"
                      >
                        Update Price
                      </button>
                      <button
                        onClick={() => dismissAlert(idx)}
                        className="p-1.5 rounded-lg hover:bg-muted transition-colors text-muted-foreground"
                        title="Keep current price"
                      >
                        <X className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <MetricCard
          title="Recipes configured"
          value={String(recipes.length)}
          change="in database"
          positive
          source="live"
          info="Menu items with at least one recipe line linked to inventory."
        />
        <MetricCard
          title="Avg. food cost per dish"
          value="$5.35"
          change="3% improvement"
          positive
          source="mock"
          info="Placeholder — will use recipe costs and supplier prices when wired."
        />
        <MetricCard
          title="Most profitable dish"
          value="Pajeon"
          change="87% margin"
          positive
          source="mock"
          info="Placeholder profitability ranking for UI reference."
        />
      </div>

      <div className="flex items-center gap-2">
        <h2 className="font-semibold text-sm">Configured recipes</h2>
        <DataSourceBadge source="live" />
      </div>

      <div className="bg-card rounded-lg border overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/50">
              <th className="text-left p-3 font-medium">Menu item</th>
              <th className="text-left p-3 font-medium">Category</th>
              <th className="text-left p-3 font-medium">Depletion</th>
              <th className="text-left p-3 font-medium">Ingredients</th>
              <th className="text-left p-3 font-medium">Units sold</th>
              <th className="text-left p-3 font-medium">Popularity</th>
              <th className="text-right p-3 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr>
                <td colSpan={7} className="p-4 text-center text-muted-foreground">
                  Loading recipes…
                </td>
              </tr>
            )}
            {!isLoading && recipes.length === 0 && (
              <tr>
                <td colSpan={7} className="p-6 text-center text-muted-foreground">
                  No recipes yet. This table only lists menu items that have a saved
                  recipe or direct ingredient link — not every item on your menu.
                  <br />
                  <span className="text-xs mt-2 block">
                    Create Recipe → pick menu item → select inventory + qty per serving → Save.
                  </span>
                </td>
              </tr>
            )}
            {!isLoading &&
              recipes.map((item: RecipeOverviewRow) => {
                const isOpen = expanded === item.menuItemId;
                const depletionLabel =
                  item.depletionType === "direct"
                    ? "Direct"
                    : item.depletionType === "recipe"
                      ? "Recipe"
                      : "—";
                return (
                  <Fragment key={item.menuItemId}>
                    <tr
                      className="border-b hover:bg-muted/30 cursor-pointer transition-colors"
                      onClick={() => setExpanded(isOpen ? null : item.menuItemId)}
                    >
                      <td className="p-3 font-medium">
                        <span className="flex items-center gap-2">
                          {isOpen ? (
                            <ChevronUp className="h-3.5 w-3.5" />
                          ) : (
                            <ChevronDown className="h-3.5 w-3.5" />
                          )}
                          {item.dish}
                        </span>
                        <p className="text-[10px] text-muted-foreground font-mono mt-0.5">
                          {item.menuItemId}
                        </p>
                      </td>
                      <td className="p-3 text-muted-foreground">{item.cat}</td>
                      <td className="p-3 text-muted-foreground">{depletionLabel}</td>
                      <td className="p-3">{item.ingredientCount}</td>
                      <td className="p-3">{item.quantitySold > 0 ? item.quantitySold : "—"}</td>
                      <td className={cn("p-3 font-medium", item.popColor)}>{item.popularity}</td>
                      <td className="p-3 text-right">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={(e) => {
                            e.stopPropagation();
                            openEditDrawer(item.menuItemId);
                          }}
                        >
                          <Pencil className="h-3.5 w-3.5 mr-1" />
                          Edit
                        </Button>
                      </td>
                    </tr>
                    {isOpen && (
                      <tr>
                        <td colSpan={7} className="p-0">
                          <div className="bg-muted/30 p-4">
                            <h4 className="font-semibold text-sm mb-3">
                              Recipe — {item.dish}
                            </h4>
                            <table className="w-full text-xs">
                              <thead>
                                <tr className="border-b">
                                  <th className="text-left pb-2 font-medium">Ingredient</th>
                                  <th className="text-left pb-2 font-medium">Qty / serving</th>
                                  <th className="text-left pb-2 font-medium">Unit</th>
                                </tr>
                              </thead>
                              <tbody>
                                {item.ingredients.map((r) => (
                                  <tr key={r.id} className="border-b last:border-0">
                                    <td className="py-1.5">{r.name}</td>
                                    <td className="py-1.5 text-muted-foreground">
                                      {r.quantity}
                                    </td>
                                    <td className="py-1.5 text-muted-foreground">{r.unit}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
          </tbody>
        </table>
      </div>

      {/* Drawer */}
      <div
        className={cn(
          "fixed inset-0 z-40 pointer-events-none",
          drawerState === "closed" && "pointer-events-none",
        )}
        aria-hidden={drawerState === "closed"}
      >
        {drawerState === "open" && (
          <div
            className="absolute inset-0 bg-black/25 backdrop-blur-[2px] pointer-events-auto"
            onClick={minimizeDrawer}
          />
        )}

        {drawerState === "minimized" && (
          <button
            onClick={() => setDrawerState("open")}
            className="absolute right-0 top-1/2 -translate-y-1/2 pointer-events-auto flex items-center gap-2 pl-4 pr-3 py-5 rounded-l-2xl text-white text-xs font-semibold shadow-2xl"
            style={{ background: "hsl(var(--primary))" }}
          >
            <span>Draft recipe</span>
            <ChevronRight className="h-4 w-4" />
          </button>
        )}

        <div
          className={cn(
            "absolute top-3 right-3 bottom-3 w-[640px] rounded-2xl flex flex-col overflow-hidden transition-transform duration-300 ease-in-out",
            drawerState === "open"
              ? "translate-x-0 pointer-events-auto"
              : "translate-x-[calc(100%+1rem)]",
          )}
          style={{
            background: "hsl(var(--primary))",
            boxShadow: "0 24px 80px rgba(0,0,0,0.45)",
          }}
        >
          <div className="flex items-center justify-between px-6 pt-6 pb-4 border-b border-white/15 shrink-0">
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-white font-bold text-xl tracking-tight">Recipe builder</h2>
                <DataSourceBadge source="live" className="border-white/30 bg-white/10 text-white" />
              </div>
              <p className="text-white/50 text-xs mt-0.5">
                Select a Toast menu item, then add inventory ingredients
              </p>
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={minimizeDrawer}
                className="w-8 h-8 flex items-center justify-center rounded-lg text-white/55 hover:text-white hover:bg-white/10"
              >
                <Minus className="h-4 w-4" />
              </button>
              <button
                onClick={closeDrawer}
                className="w-8 h-8 flex items-center justify-center rounded-lg text-white/55 hover:text-white hover:bg-white/10"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
            <div className="space-y-2">
              <Label className="text-white/70 text-xs font-medium">Search menu items</Label>
              <Input
                placeholder="e.g. Dipping Sauce"
                value={menuSearch}
                onChange={(e) => setMenuSearch(e.target.value)}
                className="bg-white text-foreground border-0 h-9"
              />
              <label className="flex items-center gap-2 text-white/70 text-xs">
                <Checkbox
                  checked={soldOnly}
                  onCheckedChange={(v) => setSoldOnly(v === true)}
                  className="border-white/40 data-[state=checked]:bg-white data-[state=checked]:text-primary"
                />
                Only items with POS sales (recommended for depletion)
              </label>
            </div>

            <div className="space-y-1.5">
              <Label className="text-white/70 text-xs font-medium">Menu item *</Label>
              <Select value={selectedMenuItemId} onValueChange={setSelectedMenuItemId}>
                <SelectTrigger className="bg-white text-foreground border-0 h-9">
                  <SelectValue placeholder="Select menu item…" />
                </SelectTrigger>
                <SelectContent className="max-h-72">
                  {menuItems.map((m) => (
                    <SelectItem key={m.id} value={m.id}>
                      {m.name}
                      {m.quantitySold > 0 ? ` (${m.quantitySold} sold)` : ""}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {selectedMenuItem && (
                <p className="text-[10px] text-white/50 font-mono">id: {selectedMenuItem.id}</p>
              )}
            </div>

            <div className="space-y-2.5">
              <div className="flex items-center justify-between">
                <span className="text-white font-semibold text-sm">Ingredients</span>
                <button
                  type="button"
                  onClick={addLine}
                  className="flex items-center gap-1 text-xs text-white/60 hover:text-white"
                >
                  <Plus className="h-3.5 w-3.5" /> Add row
                </button>
              </div>

              <div className="grid grid-cols-12 gap-2 text-[10px] uppercase tracking-wider text-white/45">
                <div className="col-span-6">Inventory item</div>
                <div className="col-span-3">Qty / serving</div>
                <div className="col-span-2">Unit</div>
                <div className="col-span-1" />
              </div>

              {lines.map((line) => {
                const inv = inventoryById.get(line.inventoryItemId);
                return (
                  <div key={line.rowId} className="grid grid-cols-12 gap-2 items-center">
                    <div className="col-span-6">
                      <Select
                        value={line.inventoryItemId}
                        onValueChange={(v) =>
                          updateLine(line.rowId, { inventoryItemId: v })
                        }
                      >
                        <SelectTrigger className="h-8 text-xs bg-white text-foreground border-0">
                          <SelectValue placeholder="Select…" />
                        </SelectTrigger>
                        <SelectContent className="max-h-60">
                          {inventoryOptions.map((opt) => (
                            <SelectItem key={opt.id} value={opt.id}>
                              {opt.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <Input
                      className="col-span-3 h-8 text-xs bg-white text-foreground border-0"
                      placeholder="0.5"
                      value={line.qtyPerServing}
                      onChange={(e) =>
                        updateLine(line.rowId, { qtyPerServing: e.target.value })
                      }
                    />
                    <span className="col-span-2 text-xs text-white/80 truncate">
                      {inv?.unit ?? "—"}
                    </span>
                    <button
                      type="button"
                      onClick={() => removeLine(line.rowId)}
                      className="col-span-1 text-white/35 hover:text-red-300"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                );
              })}
            </div>

            {saveMutation.isError && (
              <p className="text-xs text-red-200">
                {(saveMutation.error as Error).message}
              </p>
            )}
          </div>

          <div className="px-6 py-4 border-t border-white/15 flex items-center gap-2 shrink-0">
            <button
              onClick={minimizeDrawer}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-white/25 text-white/75 text-xs font-medium hover:bg-white/10"
            >
              <Save className="h-3.5 w-3.5" />
              Minimize
            </button>
            <button
              onClick={() => saveMutation.mutate()}
              disabled={!canSave || saveMutation.isPending}
              className="flex-1 py-2.5 text-sm font-bold rounded-lg bg-white hover:bg-white/92 transition-colors disabled:opacity-40"
              style={{ color: "hsl(var(--primary))" }}
            >
              {saveMutation.isPending ? "Saving…" : "Save recipe"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
