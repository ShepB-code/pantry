import { useState } from "react";
import { MetricCard } from "@/components/MetricCard";
import { cn } from "@/lib/utils";
import { ChevronDown, ChevronUp, Plus, Trash2, X, Minus, Save, ChevronRight, AlertTriangle, CheckCircle2, TrendingUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface Ingredient {
  id: string;
  name: string;
  quantity: string;
  unit: string;
  unitCost: string;
}

// Menu price alert — driven by recent ingredient cost increases
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
    dismissed: false, accepted: false,
  },
  {
    dish: "Ribeye (12oz)",
    currentFoodCostPct: 30.1,
    targetFoodCostPct: 28,
    currentMenuPrice: 52,
    suggestedMenuPrice: 54,
    triggerIngredient: "Ribeye Prime (+3.9%)",
    dismissed: false, accepted: false,
  },
];

interface Recipe {
  dish: string;
  cat: string;
  cost: string;
  price: string;
  margin: number;
  popularity: string;
  popColor: string;
  ingredients?: (Ingredient & { cost: string })[];
  totalCost?: string;
}

const initialMenu: Recipe[] = [
  {
    dish: "Bulgogi bibimbap",
    cat: "Entree",
    cost: "$4.62",
    price: "$22.00",
    margin: 79,
    popularity: "High",
    popColor: "text-success",
    totalCost: "$4.62",
    ingredients: [
      { id: "1", name: "Bulgogi beef (marinated)", quantity: "6", unit: "oz", unitCost: "$6.20/lb", cost: "$2.33" },
      { id: "2", name: "Jasmine rice", quantity: "8", unit: "oz", unitCost: "$0.80/lb", cost: "$0.40" },
      { id: "3", name: "Spinach (blanched)", quantity: "2", unit: "oz", unitCost: "$3.50/lb", cost: "$0.44" },
      { id: "4", name: "Carrots (julienned)", quantity: "2", unit: "oz", unitCost: "$1.20/lb", cost: "$0.15" },
      { id: "5", name: "Zucchini", quantity: "2", unit: "oz", unitCost: "$2.00/lb", cost: "$0.25" },
      { id: "6", name: "Egg", quantity: "1", unit: "ea", unitCost: "$0.30/ea", cost: "$0.30" },
      { id: "7", name: "Gochujang sauce", quantity: "1.5", unit: "oz", unitCost: "$5.00/jar", cost: "$0.45" },
      { id: "8", name: "Sesame oil", quantity: "0.5", unit: "oz", unitCost: "$8.00/btl", cost: "$0.25" },
      { id: "9", name: "Sesame seeds", quantity: "1", unit: "pinch", unitCost: "$12.00/lb", cost: "$0.05" },
    ],
  },
  { dish: "Galbi-jjim", cat: "Entree", cost: "$8.45", price: "$34.00", margin: 75, popularity: "High", popColor: "text-success" },
  { dish: "Kimchi jjigae", cat: "Entree", cost: "$2.90", price: "$16.00", margin: 82, popularity: "Medium", popColor: "text-info" },
  { dish: "Ribeye (12oz)", cat: "Entree", cost: "$14.20", price: "$52.00", margin: 73, popularity: "High", popColor: "text-success" },
  { dish: "Japchae", cat: "Side", cost: "$2.10", price: "$12.00", margin: 83, popularity: "Medium", popColor: "text-info" },
  { dish: "Pajeon", cat: "Appetizer", cost: "$1.85", price: "$14.00", margin: 87, popularity: "High", popColor: "text-success" },
  { dish: "Sundubu jjigae", cat: "Entree", cost: "$3.10", price: "$18.00", margin: 83, popularity: "Low", popColor: "text-warning" },
];

const UNITS = ["oz", "lb", "g", "kg", "ea", "cup", "tbsp", "tsp", "ml", "L", "pinch"];
const CATEGORIES = ["Appetizer", "Side", "Entree", "Dessert", "Beverage"];

const blankIngredient = (): Ingredient => ({
  id: crypto.randomUUID(),
  name: "",
  quantity: "",
  unit: "oz",
  unitCost: "",
});

// Conversion table — each unit maps to { category, factor } where factor converts
// qty into the canonical base unit for that category. Cross-category conversion
// is intentionally disallowed (e.g. you can't convert oz of weight to ml of volume).
const unitInfo: Record<string, { category: string; factor: number }> = {
  // Weight — base: gram
  oz: { category: "weight", factor: 28.3495 },
  lb: { category: "weight", factor: 453.592 },
  g: { category: "weight", factor: 1 },
  kg: { category: "weight", factor: 1000 },
  // Volume — base: ml
  ml: { category: "volume", factor: 1 },
  l: { category: "volume", factor: 1000 },
  tsp: { category: "volume", factor: 4.92892 },
  tbsp: { category: "volume", factor: 14.7868 },
  cup: { category: "volume", factor: 236.588 },
  // Count — base: each
  ea: { category: "count", factor: 1 },
  pinch: { category: "count", factor: 1 },
  jar: { category: "count", factor: 1 },
  btl: { category: "count", factor: 1 },
};

function calcLineCost(quantity: string, unit: string, unitCostStr: string): string {
  const qty = parseFloat(quantity);
  if (!qty || isNaN(qty) || !unitCostStr.trim()) return "";
  // Parse "$6.20/lb" or "6.20/oz" or "$0.30/ea"
  const match = unitCostStr.replace(/[$,\s]/g, "").match(/^([\d.]+)(?:\/([\w]+))?$/);
  if (!match) return "";
  const pricePerUnit = parseFloat(match[1]);
  if (isNaN(pricePerUnit)) return "";
  const costUnit = (match[2] || unit).toLowerCase();
  const ingUnit = unit.toLowerCase();
  let convertedQty = qty;
  if (ingUnit !== costUnit) {
    const ingInfo = unitInfo[ingUnit];
    const costInfo = unitInfo[costUnit];
    // Only convert when both units exist and belong to the same category.
    if (ingInfo && costInfo && ingInfo.category === costInfo.category) {
      convertedQty = (qty * ingInfo.factor) / costInfo.factor;
    }
  }
  return `$${(convertedQty * pricePerUnit).toFixed(2)}`;
}

function parseDollar(s: string): number {
  const n = parseFloat(s.replace(/[^0-9.]/g, ""));
  return isNaN(n) ? 0 : n;
}

export default function MenuRecipes() {
  const [expanded, setExpanded] = useState<string | null>(null);
  const [menu, setMenu] = useState<Recipe[]>(initialMenu);
  const [drawerState, setDrawerState] = useState<"closed" | "open" | "minimized">("closed");
  const [savedDish, setSavedDish] = useState("");
  const [dishName, setDishName] = useState("");
  const [category, setCategory] = useState("Entree");
  const [price, setPrice] = useState("");
  const [ingredients, setIngredients] = useState<Ingredient[]>([blankIngredient()]);

  // Price alert state
  const [priceAlerts, setPriceAlerts] = useState<PriceAlert[]>(initialPriceAlerts);
  const [alertsExpanded, setAlertsExpanded] = useState(true);

  const activeAlerts = priceAlerts.filter(a => !a.dismissed && !a.accepted);

  const acceptPriceChange = (idx: number) => {
    const alert = priceAlerts[idx];
    setPriceAlerts(prev => prev.map((a, i) => i === idx ? { ...a, accepted: true } : a));
    setMenu(prev => prev.map(r => {
      if (r.dish !== alert.dish) return r;
      const cost = parseDollar(r.cost);
      const newMargin = Math.round(((alert.suggestedMenuPrice - cost) / alert.suggestedMenuPrice) * 100);
      return { ...r, price: `$${alert.suggestedMenuPrice}.00`, margin: newMargin };
    }));
  };

  const dismissAlert = (idx: number) => {
    setPriceAlerts(prev => prev.map((a, i) => i === idx ? { ...a, dismissed: true } : a));
  };

  const computedCosts = ingredients.map((ing) => calcLineCost(ing.quantity, ing.unit, ing.unitCost));
  const totalCost = computedCosts.reduce((sum, c) => sum + parseDollar(c), 0);
  const priceNum = parseDollar(price);
  const marginPct = priceNum > 0 ? Math.round(((priceNum - totalCost) / priceNum) * 100) : 0;

  const openDrawer = () => setDrawerState("open");

  const minimizeDrawer = () => {
    setSavedDish(dishName);
    setDrawerState("minimized");
  };

  const closeDrawer = () => {
    setDrawerState("closed");
    setSavedDish("");
    setDishName("");
    setCategory("Entree");
    setPrice("");
    setIngredients([blankIngredient()]);
  };

  const updateIngredient = (id: string, patch: Partial<Ingredient>) =>
    setIngredients((prev) => prev.map((i) => (i.id === id ? { ...i, ...patch } : i)));

  const addIngredient = () => setIngredients((prev) => [...prev, blankIngredient()]);
  const removeIngredient = (id: string) =>
    setIngredients((prev) => (prev.length === 1 ? prev : prev.filter((i) => i.id !== id)));

  const saveRecipe = () => {
    if (!dishName.trim() || !price.trim()) return;
    const withCosts = ingredients
      .filter((i) => i.name.trim())
      .map((i, idx) => ({ ...i, cost: computedCosts[idx] || "$0.00" }));
    setMenu((prev) => [{
      dish: dishName.trim(), cat: category,
      cost: `$${totalCost.toFixed(2)}`,
      price: priceNum > 0 ? `$${priceNum.toFixed(2)}` : price,
      margin: marginPct,
      popularity: "New", popColor: "text-muted-foreground",
      ingredients: withCosts,
      totalCost: `$${totalCost.toFixed(2)}`,
    }, ...prev]);
    setExpanded(dishName.trim());
    closeDrawer();
  };

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Header */}
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-2xl font-bold">Menu & Recipes</h1>
        <Button onClick={openDrawer} size="sm" disabled={drawerState === "open"}>
          <Plus className="h-4 w-4 mr-1" />
          Create Recipe
          {drawerState === "minimized" && (
            <span className="ml-1.5 text-[10px] bg-primary-foreground/20 px-1.5 py-0.5 rounded-full">
              Draft{savedDish ? `: ${savedDish}` : ""}
            </span>
          )}
        </Button>
      </div>

      {/* ── MENU PRICE ALERT BANNER ── */}
      {activeAlerts.length > 0 && (
        <div className="rounded-lg border border-warning/30 bg-warning/5 overflow-hidden">
          <button
            onClick={() => setAlertsExpanded(!alertsExpanded)}
            className="w-full flex items-center justify-between px-5 py-3 hover:bg-warning/10 transition-colors text-left"
          >
            <div className="flex items-center gap-3">
              <AlertTriangle className="h-4 w-4 text-warning flex-shrink-0" />
              <span className="text-sm font-medium">
                {activeAlerts.length} dish{activeAlerts.length > 1 ? "es are" : " is"} outside your target food cost range due to recent price changes
              </span>
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-warning/20 text-warning">
                Action needed
              </span>
            </div>
            {alertsExpanded ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
          </button>

          {alertsExpanded && (
            <div className="border-t border-warning/20 divide-y divide-warning/15">
              {/* Header row */}
              <div className="hidden md:grid grid-cols-[1.5fr_1fr_0.8fr_0.8fr_1fr_auto] gap-4 px-5 py-2 bg-warning/5 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                <div>Dish</div>
                <div>Current food cost</div>
                <div>Target</div>
                <div>Current price</div>
                <div>Suggested price</div>
                <div className="w-[140px]"></div>
              </div>

              {priceAlerts.map((alert, idx) => {
                if (alert.dismissed) return null;
                if (alert.accepted) {
                  return (
                    <div key={idx} className="grid grid-cols-[auto_1fr_auto_auto] gap-3 items-center px-5 py-3 bg-success/5">
                      <CheckCircle2 className="h-4 w-4 text-success" />
                      <span className="font-medium text-sm">{alert.dish}</span>
                      <span className="text-xs text-muted-foreground">Menu price updated to ${alert.suggestedMenuPrice}</span>
                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-success/10 text-success">Margin restored</span>
                    </div>
                  );
                }
                return (
                  <div key={idx} className="grid grid-cols-1 md:grid-cols-[1.5fr_1fr_0.8fr_0.8fr_1fr_auto] gap-4 items-center px-5 py-3">
                    <div>
                      <p className="font-medium text-sm">{alert.dish}</p>
                      <p className="text-[11px] text-muted-foreground mt-0.5">Triggered by: {alert.triggerIngredient}</p>
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-destructive">{alert.currentFoodCostPct}%</p>
                      <p className="text-[10px] text-muted-foreground">food cost</p>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-muted-foreground">&lt;{alert.targetFoodCostPct}%</p>
                      <p className="text-[10px] text-muted-foreground">target</p>
                    </div>
                    <div>
                      <p className="text-sm font-medium">${alert.currentMenuPrice}</p>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <TrendingUp className="h-3.5 w-3.5 text-success" />
                      <div>
                        <p className="text-sm font-semibold text-success">${alert.suggestedMenuPrice}</p>
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

      {/* Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <MetricCard title="Avg. Food Cost per Dish" value="$5.35" change="3% improvement" positive info="Average ingredient cost across all active menu items, calculated from each recipe's components at current supplier prices." />
        <MetricCard title="Most Profitable Dish" value="Pajeon" change="87% margin" positive info="Menu item with the highest profit margin, calculated as (menu price minus food cost) divided by menu price." />
        <MetricCard title="Least Profitable Dish" value="Ribeye" change="73% margin" positive={false} info="Menu item with the lowest profit margin, calculated as (menu price minus food cost) divided by menu price." />
      </div>

      {/* Menu table */}
      <div className="bg-card rounded-lg border overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/50">
              <th className="text-left p-3 font-medium">Dish</th>
              <th className="text-left p-3 font-medium">Category</th>
              <th className="text-left p-3 font-medium">Food Cost</th>
              <th className="text-left p-3 font-medium">Menu Price</th>
              <th className="text-left p-3 font-medium">Margin</th>
              <th className="text-left p-3 font-medium">Popularity</th>
            </tr>
          </thead>
          <tbody>
            {menu.map((item, i) => {
              const isOpen = expanded === item.dish;
              return (
                <>
                  <tr key={i} className="border-b hover:bg-muted/30 cursor-pointer transition-colors" onClick={() => setExpanded(isOpen ? null : item.dish)}>
                    <td className="p-3 font-medium">
                      <span className="flex items-center gap-2">
                        {isOpen ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                        {item.dish}
                      </span>
                    </td>
                    <td className="p-3 text-muted-foreground">{item.cat}</td>
                    <td className="p-3">{item.cost}</td>
                    <td className="p-3">{item.price}</td>
                    <td className={cn("p-3 font-medium", item.margin >= 80 ? "text-success" : "text-accent")}>{item.margin}%</td>
                    <td className={cn("p-3 font-medium", item.popColor)}>{item.popularity}</td>
                  </tr>
                  {isOpen && (
                    <tr key={`${i}-detail`}>
                      <td colSpan={6} className="p-0">
                        <div className="bg-muted/30 p-4">
                          <h4 className="font-semibold text-sm mb-3">Recipe breakdown — {item.dish}</h4>
                          {item.ingredients?.length ? (
                            <table className="w-full text-xs">
                              <thead><tr className="border-b">
                                <th className="text-left pb-2 font-medium">Ingredient</th>
                                <th className="text-left pb-2 font-medium">Portion</th>
                                <th className="text-left pb-2 font-medium">Unit Cost</th>
                                <th className="text-right pb-2 font-medium">Line Cost</th>
                              </tr></thead>
                              <tbody>
                                {item.ingredients.map((r) => (
                                  <tr key={r.id} className="border-b last:border-0">
                                    <td className="py-1.5">{r.name}</td>
                                    <td className="py-1.5 text-muted-foreground">{r.quantity} {r.unit}</td>
                                    <td className="py-1.5 text-muted-foreground">{r.unitCost || "—"}</td>
                                    <td className="py-1.5 text-right font-medium">{r.cost || "—"}</td>
                                  </tr>
                                ))}
                                <tr className="font-bold">
                                  <td className="pt-2" colSpan={3}>Total plate cost</td>
                                  <td className="pt-2 text-right">{item.totalCost ?? item.cost}</td>
                                </tr>
                              </tbody>
                            </table>
                          ) : (
                            <p className="text-xs text-muted-foreground italic">No ingredient breakdown yet.</p>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* ── Sliding Drawer ── */}
      <div
        className={cn(
          "fixed inset-0 z-40 pointer-events-none",
          drawerState === "closed" && "pointer-events-none"
        )}
        aria-hidden={drawerState === "closed"}
      >

          {/* Backdrop */}
          {drawerState === "open" && (
            <div
              className="absolute inset-0 bg-black/25 backdrop-blur-[2px] pointer-events-auto"
              onClick={minimizeDrawer}
            />
          )}

          {/* Minimized tab — peek from right edge */}
          {drawerState === "minimized" && (
            <button
              onClick={openDrawer}
              className="absolute right-0 top-1/2 -translate-y-1/2 pointer-events-auto flex items-center gap-2 pl-4 pr-3 py-5 rounded-l-2xl text-white text-xs font-semibold shadow-2xl hover:pl-5 transition-all duration-200"
              style={{
                background: "hsl(var(--primary))",
                boxShadow: "-6px 0 28px hsl(var(--primary) / 0.5), 0 8px 32px rgba(0,0,0,0.3)",
              }}
            >
              <div className="flex flex-col items-start gap-0.5 max-w-[100px]">
                <span className="text-white/55 text-[9px] font-normal uppercase tracking-wider leading-none">Draft recipe</span>
                <span className="truncate text-white font-semibold leading-tight">{savedDish || "Untitled"}</span>
              </div>
              <ChevronRight className="h-4 w-4 text-white/60 shrink-0" />
            </button>
          )}

          {/* Drawer panel */}
          <div
            className={cn(
              "absolute top-3 right-3 bottom-3 w-[600px] rounded-2xl flex flex-col overflow-hidden transition-transform duration-300 ease-in-out",
              drawerState === "open" ? "translate-x-0 pointer-events-auto" : "translate-x-[calc(100%+1rem)]"
            )}
            style={{
              background: "hsl(var(--primary))",
              boxShadow:
                "0 0 0 1px hsl(0 0% 100% / 0.12)," +
                "-8px 0 40px hsl(var(--primary) / 0.4)," +
                "0 24px 80px rgba(0,0,0,0.45)," +
                "inset 0 1px 0 hsl(0 0% 100% / 0.18)",
            }}
          >
            {/* Header */}
            <div className="flex items-center justify-between px-6 pt-6 pb-4 border-b border-white/15 shrink-0">
              <div>
                <h2 className="text-white font-bold text-xl tracking-tight">New Recipe Card</h2>
                <p className="text-white/50 text-xs mt-0.5">Enter quantity &amp; unit cost — line cost calculates automatically</p>
              </div>
              <div className="flex items-center gap-1">
                <button onClick={minimizeDrawer} title="Minimize" className="w-8 h-8 flex items-center justify-center rounded-lg text-white/55 hover:text-white hover:bg-white/10 transition-colors">
                  <Minus className="h-4 w-4" />
                </button>
                <button onClick={closeDrawer} title="Close" className="w-8 h-8 flex items-center justify-center rounded-lg text-white/55 hover:text-white hover:bg-white/10 transition-colors">
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>

            {/* Body */}
            <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">

              {/* Dish / Category / Price */}
              <div className="grid grid-cols-3 gap-3">
                <div className="space-y-1.5">
                  <Label className="text-white/70 text-xs font-medium">Dish name</Label>
                  <Input placeholder="e.g. Spicy pork bowl" value={dishName} onChange={(e) => setDishName(e.target.value)}
                    className="bg-white text-foreground placeholder:text-muted-foreground border-0 h-9 focus-visible:ring-2 focus-visible:ring-white/40" />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-white/70 text-xs font-medium">Category</Label>
                  <Select value={category} onValueChange={setCategory}>
                    <SelectTrigger className="bg-white text-foreground border-0 h-9 focus:ring-2 focus:ring-white/40">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {CATEGORIES.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label className="text-white/70 text-xs font-medium">Menu price ($)</Label>
                  <Input placeholder="18.00" value={price} onChange={(e) => setPrice(e.target.value)}
                    className="bg-white text-foreground placeholder:text-muted-foreground border-0 h-9 focus-visible:ring-2 focus-visible:ring-white/40" />
                </div>
              </div>

              {/* Live margin panel */}
              {priceNum > 0 && (
                <div className="grid grid-cols-3 gap-0 rounded-xl border border-white/20 bg-white/10 overflow-hidden">
                  <div className="text-center px-3 py-3">
                    <p className="text-white/50 text-[10px] uppercase tracking-wide mb-0.5">Plate cost</p>
                    <p className="text-white font-bold text-lg">${totalCost.toFixed(2)}</p>
                  </div>
                  <div className="text-center px-3 py-3 border-x border-white/15">
                    <p className="text-white/50 text-[10px] uppercase tracking-wide mb-0.5">Menu Price</p>
                    <p className="text-white font-bold text-lg">${priceNum.toFixed(2)}</p>
                  </div>
                  <div className="text-center px-3 py-3">
                    <p className="text-white/50 text-[10px] uppercase tracking-wide mb-0.5">Margin</p>
                    <p className={cn("font-bold text-lg", marginPct >= 70 ? "text-green-300" : "text-red-300")}>
                      {marginPct}%
                    </p>
                  </div>
                </div>
              )}

              {/* Ingredients */}
              <div className="space-y-2.5">
                <div className="flex items-center justify-between">
                  <span className="text-white font-semibold text-sm">Ingredients</span>
                  <button onClick={addIngredient} className="flex items-center gap-1 text-xs text-white/60 hover:text-white transition-colors">
                    <Plus className="h-3.5 w-3.5" /> Add row
                  </button>
                </div>

                {/* Column labels */}
                <div className="grid grid-cols-12 gap-2 text-[10px] uppercase tracking-wider text-white/45 px-0.5">
                  <div className="col-span-4">Ingredient</div>
                  <div className="col-span-2">Qty</div>
                  <div className="col-span-2">Unit</div>
                  <div className="col-span-2">Unit Cost</div>
                  <div className="col-span-2 text-right pr-1">Cost</div>
                </div>

                {ingredients.map((ing, idx) => (
                  <div key={ing.id} className="grid grid-cols-12 gap-2 items-center">
                    <Input
                      className="col-span-4 h-8 text-xs bg-white text-foreground placeholder:text-muted-foreground border-0 focus-visible:ring-1 focus-visible:ring-white/40"
                      placeholder="Ingredient name"
                      value={ing.name}
                      onChange={(e) => updateIngredient(ing.id, { name: e.target.value })}
                    />
                    <Input
                      className="col-span-2 h-8 text-xs bg-white text-foreground placeholder:text-muted-foreground border-0 focus-visible:ring-1 focus-visible:ring-white/40"
                      placeholder="6"
                      value={ing.quantity}
                      onChange={(e) => updateIngredient(ing.id, { quantity: e.target.value })}
                    />
                    <div className="col-span-2">
                      <Select value={ing.unit} onValueChange={(v) => updateIngredient(ing.id, { unit: v })}>
                        <SelectTrigger className="h-8 text-xs bg-white text-foreground border-0 focus:ring-1 focus:ring-white/40">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {UNITS.map((u) => <SelectItem key={u} value={u}>{u}</SelectItem>)}
                        </SelectContent>
                      </Select>
                    </div>
                     <Input
                       className="col-span-2 h-8 text-xs bg-white text-foreground placeholder:text-muted-foreground border-0 focus-visible:ring-1 focus-visible:ring-white/40"
                       placeholder="$6.20/lb"
                       value={ing.unitCost}
                       onChange={(e) => updateIngredient(ing.id, { unitCost: e.target.value })}
                     />
                    {/* Auto-calculated cost read-only + delete */}
                    <div className="col-span-2 flex items-center justify-end gap-1.5">
                      <span className="text-xs font-bold text-white tabular-nums min-w-[36px] text-right">
                        {computedCosts[idx] || <span className="text-white/30 font-normal">—</span>}
                      </span>
                      <button onClick={() => removeIngredient(ing.id)} className="text-white/35 hover:text-red-300 transition-colors shrink-0">
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Footer */}
            <div className="px-6 py-4 border-t border-white/15 flex items-center gap-2 shrink-0">
              <button
                onClick={minimizeDrawer}
                className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-white/25 text-white/75 text-xs font-medium hover:bg-white/10 transition-colors"
              >
                <Save className="h-3.5 w-3.5" />
                Save Draft
              </button>
              <button
                onClick={saveRecipe}
                disabled={!dishName.trim() || !price.trim()}
                className="flex-1 py-2.5 text-sm font-bold rounded-lg bg-white hover:bg-white/92 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                style={{ color: "hsl(var(--primary))" }}
              >
                Save Recipe
              </button>
            </div>
          </div>
        </div>
    </div>
  );
}
