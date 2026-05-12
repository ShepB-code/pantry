import { useState, useMemo } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { cn } from "@/lib/utils";
import { ArrowUpDown, ArrowUp, ArrowDown, Search, X, Zap, CheckCircle2, AlertTriangle, ChevronLeft, ChevronRight } from "lucide-react";

const stockData = [
  { name: "Ribeye (Prime)", cat: "Protein", onHand: "42 lbs", par: "50 lbs", status: "Below par", statusColor: "text-warning", days: "3" },
  { name: "Salmon fillet", cat: "Protein", onHand: "18 lbs", par: "20 lbs", status: "Below par", statusColor: "text-warning", days: "2" },
  { name: "Short rib", cat: "Protein", onHand: "35 lbs", par: "30 lbs", status: "Good", statusColor: "text-success", days: "5" },
  { name: "Soft tofu", cat: "Produce", onHand: "8 containers", par: "10", status: "Expiring", statusColor: "text-destructive", days: "1" },
  { name: "Gochujang paste", cat: "Pantry", onHand: "4 jars", par: "3 jars", status: "Good", statusColor: "text-success", days: "60+" },
  { name: "Enoki mushrooms", cat: "Produce", onHand: "5 lbs", par: "6 lbs", status: "Expiring", statusColor: "text-destructive", days: "1" },
  { name: "Jasmine rice", cat: "Grain", onHand: "80 lbs", par: "50 lbs", status: "Good", statusColor: "text-success", days: "30+" },
  { name: "Sesame oil", cat: "Pantry", onHand: "6 bottles", par: "4 bottles", status: "Good", statusColor: "text-success", days: "90+" },
  { name: "Napa cabbage", cat: "Produce", onHand: "12 heads", par: "10 heads", status: "Good", statusColor: "text-success", days: "4" },
  { name: "Soju (assorted)", cat: "Beverage", onHand: "24 bottles", par: "30 bottles", status: "Below par", statusColor: "text-warning", days: "N/A" },
];

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

// Quick count — critical items only
const quickCountItems = [
  { name: "Ribeye (Prime)", estimate: "42 lbs", unit: "lbs", priority: "high", reason: "High cost · Below par", cat: "Protein" },
  { name: "Salmon fillet", estimate: "18 lbs", unit: "lbs", priority: "critical", reason: "Expiring in 2 days", cat: "Protein" },
  { name: "Short rib", estimate: "35 lbs", unit: "lbs", priority: "high", reason: "High cost", cat: "Protein" },
  { name: "Soft tofu", estimate: "8 containers", unit: "containers", priority: "critical", reason: "Expiring tomorrow", cat: "Produce" },
  { name: "Enoki mushrooms", estimate: "5 lbs", unit: "lbs", priority: "critical", reason: "Expiring tomorrow", cat: "Produce" },
  { name: "Soju (assorted)", estimate: "24 bottles", unit: "bottles", priority: "high", reason: "High variance last week", cat: "Beverage" },
  { name: "Chicken thigh", estimate: "28 lbs", unit: "lbs", priority: "medium", reason: "High velocity", cat: "Protein" },
  { name: "Jasmine rice", estimate: "80 lbs", unit: "lbs", priority: "medium", reason: "High volume", cat: "Grain" },
];

type QuickCountState = "idle" | "counting" | "done";

interface QuickCountEntry {
  name: string;
  estimate: string;
  actual: string;
  confirmed: boolean;
  flagged: boolean;
}

export default function Inventory() {
  const [counts, setCounts] = useState(countItems);

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
      data = data.filter(i => i.name.toLowerCase().includes(q) || i.cat.toLowerCase().includes(q));
    }
    if (categoryFilter !== "All") data = data.filter(i => i.cat === categoryFilter);
    if (statusFilter !== "All") data = data.filter(i => i.status === statusFilter);
    if (sortCol) {
      data.sort((a, b) => {
        let av: string | number, bv: string | number;
        if (sortCol === "name") { av = a.name; bv = b.name; }
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
  }, [search, categoryFilter, statusFilter, sortCol, sortDir]);

  const hasActiveFilters = search.trim() || categoryFilter !== "All" || statusFilter !== "All";

  const clearFilters = () => { setSearch(""); setCategoryFilter("All"); setStatusFilter("All"); };

  // ── Quick count state ──
  const [qcState, setQcState] = useState<QuickCountState>("idle");
  const [qcIndex, setQcIndex] = useState(0);
  const [qcEntries, setQcEntries] = useState<QuickCountEntry[]>(
    quickCountItems.map(i => ({ name: i.name, estimate: i.estimate, actual: "", confirmed: false, flagged: false }))
  );
  const [qcInput, setQcInput] = useState("");

  const currentQCItem = quickCountItems[qcIndex];
  const currentEntry = qcEntries[qcIndex];

  const confirmQcItem = (actual: string, flagged = false) => {
    const updated = [...qcEntries];
    updated[qcIndex] = { ...updated[qcIndex], actual: actual || updated[qcIndex].estimate, confirmed: true, flagged };
    setQcEntries(updated);
    setQcInput("");
    if (qcIndex < quickCountItems.length - 1) setQcIndex(qcIndex + 1);
    else setQcState("done");
  };

  const looksRight = () => confirmQcItem(currentEntry.estimate, false);

  const submitActual = () => {
    if (!qcInput.trim()) return;
    const est = parseQty(currentEntry.estimate);
    const actual = parseQty(qcInput);
    const variance = est === 0 ? 0 : Math.abs((actual - est) / est);
    confirmQcItem(qcInput, variance > 0.10);
  };

  const resetQC = () => {
    setQcState("idle");
    setQcIndex(0);
    setQcInput("");
    setQcEntries(quickCountItems.map(i => ({ name: i.name, estimate: i.estimate, actual: "", confirmed: false, flagged: false })));
  };

  const flaggedItems = qcEntries.filter(e => e.flagged);
  const completedCount = qcEntries.filter(e => e.confirmed).length;

  return (
    <div className="space-y-6 max-w-7xl">
      <h1 className="text-2xl font-bold">Inventory</h1>

      <Tabs defaultValue="current" className="w-full">
        <TabsList>
          <TabsTrigger value="current">Current Stock</TabsTrigger>
          <TabsTrigger value="expiring">Expiring Soon</TabsTrigger>
          <TabsTrigger value="quick">
            <Zap className="h-3.5 w-3.5 mr-1" />
            Quick Count
          </TabsTrigger>
          <TabsTrigger value="counts">Full Count</TabsTrigger>
        </TabsList>

        <TabsContent value="current" className="mt-4">
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
                  <tr><td colSpan={6} className="p-6 text-center text-muted-foreground text-sm">No items match your filters.</td></tr>
                ) : filteredData.map((item, i) => (
                  <tr key={i} className="border-b last:border-0 hover:bg-muted/30 transition-colors">
                    <td className="p-3 font-medium">{item.name}</td>
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
          {qcState === "idle" && (
            <div className="bg-card rounded-lg border p-6 max-w-2xl mx-auto space-y-5">
              <div className="flex items-start gap-3">
                <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                  <Zap className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <h2 className="font-semibold text-lg">Quick Count</h2>
                  <p className="text-sm text-muted-foreground mt-1">
                    A 3–5 minute daily pulse check on your {quickCountItems.length} most critical items.
                    Pantry shows AI estimates — just confirm or correct.
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div className="rounded-lg border p-3 text-center">
                  <p className="text-xl font-bold text-destructive">{quickCountItems.filter(i => i.priority === "critical").length}</p>
                  <p className="text-[11px] text-muted-foreground mt-0.5">Critical items</p>
                </div>
                <div className="rounded-lg border p-3 text-center">
                  <p className="text-xl font-bold text-warning">{quickCountItems.filter(i => i.priority === "high").length}</p>
                  <p className="text-[11px] text-muted-foreground mt-0.5">High priority</p>
                </div>
                <div className="rounded-lg border p-3 text-center">
                  <p className="text-xl font-bold">~4 min</p>
                  <p className="text-[11px] text-muted-foreground mt-0.5">Est. time</p>
                </div>
              </div>

              <div className="space-y-1.5">
                {quickCountItems.map((item, i) => (
                  <div key={i} className="flex items-center gap-3 text-sm py-1.5 border-b last:border-0">
                    <span className={cn(
                      "h-2 w-2 rounded-full flex-shrink-0",
                      item.priority === "critical" ? "bg-destructive" : item.priority === "high" ? "bg-warning" : "bg-muted-foreground/40"
                    )} />
                    <span className="font-medium flex-1">{item.name}</span>
                    <span className="text-xs text-muted-foreground">{item.reason}</span>
                  </div>
                ))}
              </div>

              <Button onClick={() => setQcState("counting")} className="w-full" size="lg">
                <Zap className="h-4 w-4 mr-2" /> Start Quick Count
              </Button>
            </div>
          )}

          {qcState === "counting" && (
            <div className="max-w-2xl mx-auto space-y-4">
              {/* Progress bar */}
              <div className="flex items-center gap-3">
                <span className="text-xs font-semibold tabular-nums text-muted-foreground">{qcIndex + 1} / {quickCountItems.length}</span>
                <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
                  <div className="h-full bg-primary rounded-full transition-all" style={{ width: `${((qcIndex) / quickCountItems.length) * 100}%` }} />
                </div>
                <button onClick={resetQC} className="text-xs text-muted-foreground hover:text-foreground transition-colors">Cancel</button>
              </div>

              {/* Completed chips */}
              {qcIndex > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {qcEntries.slice(0, qcIndex).map((e, i) => (
                    <span key={i} className={cn(
                      "text-[10px] px-2 py-0.5 rounded-full font-medium",
                      e.flagged ? "bg-warning/10 text-warning" : "bg-success/10 text-success"
                    )}>
                      {e.flagged ? "⚠" : "✓"} {e.name.split(" ")[0]}
                    </span>
                  ))}
                </div>
              )}

              {/* Current item card */}
              <div className="bg-card rounded-xl border p-6 space-y-5">
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <span className={cn(
                      "text-[10px] font-semibold px-2 py-0.5 rounded-full",
                      currentQCItem.priority === "critical" ? "bg-destructive/10 text-destructive" :
                      currentQCItem.priority === "high" ? "bg-warning/10 text-warning" : "bg-muted text-muted-foreground"
                    )}>
                      {currentQCItem.priority === "critical" ? "Critical" : currentQCItem.priority === "high" ? "High" : "Medium"}
                    </span>
                    <p className="text-xs text-muted-foreground">{currentQCItem.cat} · {currentQCItem.reason}</p>
                  </div>
                  {qcIndex > 0 && (
                    <button onClick={() => { setQcIndex(qcIndex - 1); setQcInput(""); }} className="p-1 rounded hover:bg-muted transition-colors">
                      <ChevronLeft className="h-4 w-4 text-muted-foreground" />
                    </button>
                  )}
                </div>

                <div className="space-y-1">
                  <h3 className="text-2xl font-bold">{currentQCItem.name}</h3>
                  <div className="flex items-baseline gap-2">
                    <span className="text-xs text-muted-foreground">AI estimate:</span>
                    <span className="text-lg font-semibold">{currentEntry.estimate}</span>
                  </div>
                </div>

                <div className="space-y-3">
                  <Button onClick={looksRight} className="w-full" size="lg">
                    <CheckCircle2 className="h-4 w-4 mr-2" />
                    Looks Right — Confirm {currentEntry.estimate}
                  </Button>

                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-px bg-border" />
                    <p className="text-[10px] uppercase tracking-wide text-muted-foreground font-medium">or enter actual</p>
                    <div className="flex-1 h-px bg-border" />
                  </div>

                  <div className="flex gap-2">
                    <input
                      value={qcInput}
                      onChange={e => setQcInput(e.target.value)}
                      onKeyDown={e => e.key === "Enter" && submitActual()}
                      placeholder={`Actual amount in ${currentQCItem.unit}`}
                      className="flex-1 rounded-lg border bg-background px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                      autoFocus
                    />
                    <Button onClick={submitActual} variant="outline" size="lg" disabled={!qcInput.trim()}>
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>

                  <p className="text-[11px] text-muted-foreground text-center">Variance &gt;10% will be flagged for investigation</p>
                </div>
              </div>
            </div>
          )}

          {qcState === "done" && (
            <div className="max-w-2xl mx-auto space-y-4">
              <div className="bg-card rounded-xl border p-6 space-y-5">
                <div className="flex items-start gap-3">
                  <div className="h-10 w-10 rounded-lg bg-success/10 flex items-center justify-center flex-shrink-0">
                    <CheckCircle2 className="h-5 w-5 text-success" />
                  </div>
                  <div>
                    <h2 className="font-semibold text-lg">Quick Count Complete</h2>
                    <p className="text-sm text-muted-foreground mt-0.5">
                      {completedCount} items checked · {flaggedItems.length > 0 ? `${flaggedItems.length} flagged for investigation` : "No variance flags"}
                    </p>
                  </div>
                </div>

                {flaggedItems.length > 0 && (
                  <div className="rounded-lg border border-warning/30 bg-warning/5 p-4 space-y-3">
                    <p className="text-sm font-semibold flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4 text-warning" /> Items to investigate
                    </p>
                    {flaggedItems.map((item, i) => (
                      <div key={i} className="flex items-center justify-between text-sm">
                        <span className="font-medium">{item.name}</span>
                        <div className="flex items-baseline gap-3 text-xs">
                          <span className="text-muted-foreground">AI: <span className="font-medium text-foreground">{item.estimate}</span></span>
                          <span className="text-muted-foreground">Actual: <span className="font-medium text-warning">{item.actual}</span></span>
                        </div>
                      </div>
                    ))}
                    <p className="text-xs text-muted-foreground pt-1 border-t border-warning/20">
                      Check the Variance report in Financials for diagnostics on flagged items.
                    </p>
                  </div>
                )}

                {flaggedItems.length === 0 && (
                  <div className="rounded-lg border border-success/30 bg-success/5 p-4">
                    <p className="text-sm">All items within normal range. No action needed.</p>
                  </div>
                )}

                <div className="space-y-2">
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Full summary</p>
                  {qcEntries.map((e, i) => (
                    <div key={i} className="flex items-center justify-between text-sm py-1.5 border-b last:border-0">
                      <span className="font-medium">{e.name}</span>
                      <div className="flex items-center gap-2">
                        {e.actual !== e.estimate && <span className="text-xs text-muted-foreground line-through">{e.estimate}</span>}
                        <span className="font-semibold">{e.actual || e.estimate}</span>
                        {e.flagged ? <AlertTriangle className="h-3.5 w-3.5 text-warning" /> : <CheckCircle2 className="h-3.5 w-3.5 text-success" />}
                      </div>
                    </div>
                  ))}
                </div>

                <Button onClick={resetQC} variant="outline" className="w-full">Start New Quick Count</Button>
              </div>
            </div>
          )}
        </TabsContent>

        <TabsContent value="counts" className="mt-4">
          <p className="text-sm text-muted-foreground mb-4">Pantry estimates stock based on POS sales and deliveries. Confirm or adjust each item.</p>
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
