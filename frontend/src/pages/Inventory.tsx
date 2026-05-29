import { useState, useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { cn } from "@/lib/utils";
import { ArrowUpDown, ArrowUp, ArrowDown, Search, X, Zap, Pencil, Check } from "lucide-react";
import { QuickCountWizard } from "@/components/inventory/QuickCountWizard";
import { fetchInventory, updateIngredientName } from "@/api/inventory";
import { DataSourceBadge } from "@/components/DataSourceBadge";

function formatQty(value: number, unit: string) {
  const rounded = value % 1 === 0 ? String(Math.round(value)) : value.toFixed(1);
  return `${rounded} ${unit}`;
}

const expiringItems = [
  { name: "Salmon fillet", qty: "8 lbs", urgency: "Tomorrow", urgencyColor: "bg-destructive/10 text-destructive", suggestion: "Run miso-glazed salmon special tonight" },
  { name: "Soft tofu", qty: "3 containers", urgency: "Tomorrow", urgencyColor: "bg-destructive/10 text-destructive", suggestion: "Add sundubu jjigae as lunch feature" },
  { name: "Enoki mushrooms", qty: "2 lbs", urgency: "Tomorrow", urgencyColor: "bg-destructive/10 text-destructive", suggestion: "Use in japchae or bibimbap topping" },
  { name: "Bean sprouts", qty: "4 lbs", urgency: "2 days", urgencyColor: "bg-warning/10 text-warning", suggestion: "Increase banchan portions" },
  { name: "Scallions", qty: "3 bunches", urgency: "2 days", urgencyColor: "bg-warning/10 text-warning", suggestion: "Prep pajeon (scallion pancake) special" },
  { name: "Pork belly", qty: "6 lbs", urgency: "3 days", urgencyColor: "bg-warning/10 text-warning", suggestion: "Feature bossam platter" },
];

const countItems = [
  { name: "Ribeye (Prime)", estimate: "42 lbs", confirmed: false },
  { name: "Salmon fillet", estimate: "18 lbs", confirmed: false },
  { name: "Short rib", estimate: "35 lbs", confirmed: false },
  { name: "Soft tofu", estimate: "8 containers", confirmed: false },
  { name: "Jasmine rice", estimate: "80 lbs", confirmed: true },
  { name: "Gochujang paste", estimate: "4 jars", confirmed: true },
];

export default function Inventory() {
  const [counts, setCounts] = useState(countItems);
  const queryClient = useQueryClient();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editDraft, setEditDraft] = useState("");

  const { data: inventory, isLoading: inventoryLoading, isError: inventoryError } = useQuery({
    queryKey: ["inventory"],
    queryFn: fetchInventory,
  });

  const nameMutation = useMutation({
    mutationFn: ({ itemId, name }: { itemId: string; name: string }) =>
      updateIngredientName(itemId, name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["inventory"] });
      setEditingId(null);
      setEditDraft("");
    },
  });

  const stockData = useMemo(() => {
    if (!inventory?.items) return [];
    return inventory.items.map((item) => ({
      id: item.id,
      name: item.name,
      nameSource: item.nameSource,
      inventoryItem: item.inventoryItem,
      cat: item.category,
      onHand: formatQty(item.onHand, item.unit),
      par: item.parLevel != null ? formatQty(item.parLevel, item.unit) : "—",
      status: item.status,
      statusColor: item.statusColor,
      days: "—",
    }));
  }, [inventory]);

  // Filter/sort state
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("All");
  const [statusFilter, setStatusFilter] = useState("All");
  const [sortCol, setSortCol] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

  const allCategories = ["All", ...Array.from(new Set(stockData.map(i => i.cat)))];
  const allStatuses = ["All", ...Array.from(new Set(stockData.map(i => i.status)))];

  const toggleSort = (col: string) => {
    if (sortCol === col) setSortDir(d => d === "asc" ? "desc" : "asc");
    else { setSortCol(col); setSortDir("asc"); }
  };

  const SortIcon = ({ col }: { col: string }) => {
    if (sortCol !== col) return <ArrowUpDown className="h-3.5 w-3.5 opacity-40" />;
    return sortDir === "asc" ? <ArrowUp className="h-3.5 w-3.5 text-primary" /> : <ArrowDown className="h-3.5 w-3.5 text-primary" />;
  };

  const parseDays = (d: string) => {
    if (d === "N/A") return 999;
    const n = parseInt(d);
    return isNaN(n) ? 9999 : n;
  };

  const parseQty = (s: string) => {
    const n = parseFloat(s.replace(/[^0-9.]/g, ""));
    return isNaN(n) ? 0 : n;
  };

  const filteredData = useMemo(() => {
    let data = [...stockData];
    if (search.trim()) {
      const q = search.toLowerCase();
      data = data.filter(
        i =>
          i.name.toLowerCase().includes(q) ||
          i.inventoryItem.toLowerCase().includes(q) ||
          i.cat.toLowerCase().includes(q),
      );
    }
    if (categoryFilter !== "All") data = data.filter(i => i.cat === categoryFilter);
    if (statusFilter !== "All") data = data.filter(i => i.status === statusFilter);
    if (sortCol) {
      data.sort((a, b) => {
        let av: string | number, bv: string | number;
        if (sortCol === "name") { av = a.name; bv = b.name; }
        else if (sortCol === "inventoryItem") { av = a.inventoryItem; bv = b.inventoryItem; }
        else if (sortCol === "cat") { av = a.cat; bv = b.cat; }
        else if (sortCol === "onHand") { av = parseQty(a.onHand); bv = parseQty(b.onHand); }
        else if (sortCol === "par") { av = parseQty(a.par); bv = parseQty(b.par); }
        else if (sortCol === "status") { av = a.status; bv = b.status; }
        else if (sortCol === "days") { av = parseDays(a.days); bv = parseDays(b.days); }
        else return 0;
        if (typeof av === "string") return sortDir === "asc" ? av.localeCompare(bv as string) : (bv as string).localeCompare(av);
        return sortDir === "asc" ? av - (bv as number) : (bv as number) - av;
      });
    }
    return data;
  }, [stockData, search, categoryFilter, statusFilter, sortCol, sortDir]);

  const hasActiveFilters = search.trim() || categoryFilter !== "All" || statusFilter !== "All";

  const clearFilters = () => { setSearch(""); setCategoryFilter("All"); setStatusFilter("All"); };

  const startEditing = (item: (typeof stockData)[number]) => {
    setEditingId(item.id);
    setEditDraft(item.name);
  };

  const saveEditing = (itemId: string) => {
    const trimmed = editDraft.trim();
    if (!trimmed) return;
    nameMutation.mutate({ itemId, name: trimmed });
  };

  return (
    <div className="space-y-6 max-w-7xl">
      <h1 className="text-2xl font-bold">Inventory</h1>

      <Tabs defaultValue="current" className="w-full">
        <TabsList>
          <TabsTrigger value="current" className="gap-1.5">
            Current Stock
            <DataSourceBadge source="live" />
          </TabsTrigger>
          <TabsTrigger value="expiring" className="gap-1.5">
            Expiring Soon
            <DataSourceBadge source="mock" />
          </TabsTrigger>
          <TabsTrigger value="quick" className="gap-1.5">
            <Zap className="h-3.5 w-3.5 mr-1" />
            Quick Count
            <DataSourceBadge source="live" />
          </TabsTrigger>
          <TabsTrigger value="counts" className="gap-1.5">
            Full Count
            <DataSourceBadge source="mock" />
          </TabsTrigger>
        </TabsList>

        <TabsContent value="current" className="mt-4">
          {inventoryLoading && (
            <p className="text-sm text-muted-foreground mb-4">Loading inventory from database…</p>
          )}
          {inventoryError && (
            <p className="text-sm text-destructive mb-4">Could not load inventory. Is the API running?</p>
          )}
          {!inventoryLoading && !inventoryError && stockData.length === 0 && (
            <p className="text-sm text-muted-foreground mb-4">
              No inventory items yet. Restart the API to sync xtraCHEF, or POST /api/inventory/sync-catalog.
            </p>
          )}
          {/* Filter bar */}
          <div className="flex flex-wrap items-center gap-3 mb-4">
            <div className="relative flex-1 min-w-[180px]">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
              <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search ingredients…" className="w-full rounded-md border bg-background pl-8 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
            </div>
            <div className="flex items-center gap-2">
              <label className="text-xs text-muted-foreground font-medium">Category</label>
              <select value={categoryFilter} onChange={e => setCategoryFilter(e.target.value)} className="rounded-md border bg-background px-2.5 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring">
                {allCategories.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div className="flex items-center gap-2">
              <label className="text-xs text-muted-foreground font-medium">Status</label>
              <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="rounded-md border bg-background px-2.5 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring">
                {allStatuses.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            {hasActiveFilters && (
              <button onClick={clearFilters} className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors">
                <X className="h-3.5 w-3.5" /> Clear
              </button>
            )}
            <span className="text-xs text-muted-foreground ml-auto">{filteredData.length} of {stockData.length} items</span>
          </div>

          <div className="bg-card rounded-lg border overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-muted/50">
                  {([
                    { col: "name", label: "Ingredient" },
                    { col: "inventoryItem", label: "Inventory Item" },
                    { col: "cat", label: "Category" },
                    { col: "onHand", label: "On Hand" },
                    { col: "par", label: "Par Level" },
                    { col: "status", label: "Status" },
                    { col: "days", label: "Est. Days Left" },
                  ] as { col: string; label: string }[]).map(({ col, label }) => (
                    <th key={col} className="text-left p-3 font-medium">
                      <button onClick={() => toggleSort(col)} className="flex items-center gap-1.5 hover:text-foreground transition-colors group">
                        {label}
                        <SortIcon col={col} />
                      </button>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filteredData.length === 0 ? (
                  <tr><td colSpan={7} className="p-6 text-center text-muted-foreground text-sm">No items match your filters.</td></tr>
                ) : filteredData.map((item) => (
                  <tr key={item.id} className="border-b last:border-0 hover:bg-muted/30 transition-colors">
                    <td className="p-3 font-medium">
                      {editingId === item.id ? (
                        <div className="flex items-center gap-1.5">
                          <Input
                            value={editDraft}
                            onChange={(e) => setEditDraft(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") saveEditing(item.id);
                              if (e.key === "Escape") setEditingId(null);
                            }}
                            className="h-8 text-sm"
                            autoFocus
                          />
                          <button
                            type="button"
                            onClick={() => saveEditing(item.id)}
                            disabled={nameMutation.isPending}
                            className="text-primary hover:text-primary/80"
                            aria-label="Save ingredient name"
                          >
                            <Check className="h-4 w-4" />
                          </button>
                        </div>
                      ) : (
                        <div className="flex items-center gap-1.5 group">
                          <span>{item.name}</span>
                          <button
                            type="button"
                            onClick={() => startEditing(item)}
                            className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-foreground transition-opacity"
                            aria-label="Edit ingredient name"
                          >
                            <Pencil className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      )}
                    </td>
                    <td className="p-3 text-muted-foreground max-w-[280px] truncate" title={item.inventoryItem}>
                      {item.inventoryItem}
                    </td>
                    <td className="p-3 text-muted-foreground">{item.cat}</td>
                    <td className="p-3">{item.onHand}</td>
                    <td className="p-3">{item.par}</td>
                    <td className={cn("p-3 font-medium", item.statusColor)}>{item.status}</td>
                    <td className="p-3">{item.days}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </TabsContent>

        <TabsContent value="expiring" className="mt-4">
          <p className="text-xs text-muted-foreground mb-4 flex items-center gap-2">
            <DataSourceBadge source="mock" />
            Sample expiry suggestions — not tied to inventory yet.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {expiringItems.map((item, i) => (
              <div key={i} className="bg-card rounded-lg border p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold">{item.name}</h3>
                  <span className={cn("text-[10px] font-semibold px-2 py-0.5 rounded-full", item.urgencyColor)}>{item.urgency}</span>
                </div>
                <p className="text-sm text-muted-foreground">{item.qty} remaining</p>
                <div className="bg-primary-light rounded-md p-3">
                  <p className="text-xs text-primary font-medium">💡 {item.suggestion}</p>
                </div>
                <Button size="sm" className="w-full">Apply</Button>
              </div>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="quick" className="mt-4">
          <QuickCountWizard />
        </TabsContent>

        <TabsContent value="counts" className="mt-4">
          <p className="text-sm text-muted-foreground mb-2 flex items-center gap-2 flex-wrap">
            <DataSourceBadge source="mock" />
            Pantry estimates stock based on POS sales and deliveries. Confirm or adjust each item.
          </p>
          <div className="bg-card rounded-lg border divide-y">
            {counts.map((item, i) => (
              <div key={i} className={cn("flex items-center gap-4 p-4", item.confirmed && "bg-primary-light/50")}>
                <Checkbox checked={item.confirmed} disabled />
                <span className="font-medium text-sm w-40">{item.name}</span>
                <span className="text-xs text-muted-foreground">AI estimate: <span className="font-medium text-foreground">{item.estimate}</span></span>
                <Input placeholder="Actual" className="w-28 h-8 text-sm" />
                <Button
                  size="sm"
                  variant={item.confirmed ? "secondary" : "default"}
                  onClick={() => {
                    const next = [...counts];
                    next[i] = { ...next[i], confirmed: true };
                    setCounts(next);
                  }}
                >
                  {item.confirmed ? "Confirmed" : "Confirm"}
                </Button>
              </div>
            ))}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
