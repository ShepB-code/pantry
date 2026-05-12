import { useState } from "react";
import { MetricCard } from "@/components/MetricCard";
import { cn } from "@/lib/utils";
import { X, AlertTriangle, ChevronRight, CheckCircle2, HelpCircle, Package, Truck, Scissors } from "lucide-react";

const budgetItems = [
  { cat: "Proteins", spent: 8840, budget: 9200 },
  { cat: "Produce", spent: 3950, budget: 3800 },
  { cat: "Dry goods", spent: 1980, budget: 2200 },
  { cat: "Beverages", spent: 4200, budget: 4500 },
  { cat: "Dairy", spent: 1380, budget: 1400 },
];

const profitMargins = [
  { cat: "Appetizers", margin: 85 },
  { cat: "Sides", margin: 83 },
  { cat: "Entrees", margin: 76 },
  { cat: "Beverages", margin: 78 },
  { cat: "Desserts", margin: 81 },
];

interface VarianceDiagnosis {
  cause: string;
  confidence: number;
  icon: typeof AlertTriangle;
  iconColor: string;
  detail: string;
  action: string;
}

interface VarianceItem {
  ingredient: string;
  theoretical: string;
  actual: string;
  variance: string;
  varColor: string;
  impact: string;
  impColor: string;
  diagnoses: VarianceDiagnosis[];
}

const variance: VarianceItem[] = [
  {
    ingredient: "Ribeye", theoretical: "58 lbs", actual: "67 lbs", variance: "+15.5%",
    varColor: "text-destructive", impact: "-$166.50", impColor: "text-destructive",
    diagnoses: [
      { cause: "Portioning issue", confidence: 72, icon: Scissors, iconColor: "text-destructive",
        detail: "Sales data shows 67 ribeye dishes sold. At spec (12 oz), theoretical usage = 50.25 lbs. Actual = 67 lbs. Suggests average portion is running ~14 oz instead of 12 oz.",
        action: "Audit portion sizes with line cooks. Consider re-training or adding a portion scale to the expo station." },
      { cause: "Receiving discrepancy", confidence: 21, icon: Truck, iconColor: "text-warning",
        detail: "Last Sysco delivery invoiced 40 lbs. Verify physical receipt matched invoice. Short-shipments of 2–3 lbs would account for ~18% of variance.",
        action: "Cross-check Apr 14 delivery receipt against the Sysco invoice in the Suppliers tab." },
      { cause: "Waste or spoilage", confidence: 7, icon: Package, iconColor: "text-muted-foreground",
        detail: "No expiration alerts were triggered for ribeye this week. Low likelihood of spoilage-driven variance.",
        action: "No action needed. Monitor next week." },
    ],
  },
  {
    ingredient: "Salmon", theoretical: "32 lbs", actual: "35 lbs", variance: "+9.4%",
    varColor: "text-warning", impact: "-$39.60", impColor: "text-destructive",
    diagnoses: [
      { cause: "Portioning issue", confidence: 55, icon: Scissors, iconColor: "text-warning",
        detail: "24 salmon dishes sold this week. Theoretical usage = 32 lbs at 8 oz spec. Actual usage 3 lbs over suggests slight over-portioning (~8.9 oz average vs 8 oz).",
        action: "Spot-check salmon portions during next dinner service." },
      { cause: "Trim loss variance", confidence: 35, icon: Scissors, iconColor: "text-warning",
        detail: "Salmon yield can vary 5–15% depending on fillet quality. If this delivery had more belly/tail portions, yield loss would naturally increase.",
        action: "Log yield % on next salmon delivery. If consistently below 85%, negotiate trim specifications with Pacific Seafood." },
      { cause: "Waste or spoilage", confidence: 10, icon: Package, iconColor: "text-muted-foreground",
        detail: "3 lbs of salmon were flagged as expiring this week. Some waste-related usage is possible.",
        action: "Review expiring items tab for this week's salmon status." },
    ],
  },
  {
    ingredient: "Chicken thigh", theoretical: "45 lbs", actual: "44 lbs", variance: "-2.2%",
    varColor: "text-success", impact: "+$4.20", impColor: "text-success",
    diagnoses: [
      { cause: "Within acceptable range", confidence: 95, icon: CheckCircle2, iconColor: "text-success",
        detail: "Actual usage is 1 lb below theoretical. This is within the normal ±3% variance band and likely reflects slight under-portioning or yield efficiency.",
        action: "No action needed. Consistent with prior weeks." },
    ],
  },
  {
    ingredient: "Short rib", theoretical: "38 lbs", actual: "40 lbs", variance: "+5.3%",
    varColor: "text-warning", impact: "-$24.00", impColor: "text-destructive",
    diagnoses: [
      { cause: "Braising / prep loss", confidence: 60, icon: Scissors, iconColor: "text-warning",
        detail: "Short rib loses 25–35% of weight during braising. If batch sizes were adjusted mid-week, total prep weight consumed could differ from theoretical sold weight.",
        action: "Reconcile weekly batch prep logs against sold quantities. Consider adjusting theoretical weight to account for braise loss." },
      { cause: "Portioning issue", confidence: 30, icon: Scissors, iconColor: "text-warning",
        detail: "2 lbs over 38 lbs theoretical. If 22 galbi-jjim plates were served at a 6-oz spec, a portion of ~6.4 oz average would explain the gap.",
        action: "Audit galbi-jjim portions with kitchen manager." },
      { cause: "Inventory count error", confidence: 10, icon: HelpCircle, iconColor: "text-muted-foreground",
        detail: "Manual counts have ±5% human error margin. Small variance may be measurement artifact.",
        action: "Use the Quick Count tab to recount short rib today for confirmation." },
    ],
  },
  {
    ingredient: "Soju", theoretical: "36 btl", actual: "42 btl", variance: "+16.7%",
    varColor: "text-destructive", impact: "-$51.00", impColor: "text-destructive",
    diagnoses: [
      { cause: "Unrecorded complimentary pours", confidence: 50, icon: Package, iconColor: "text-warning",
        detail: "6 bottles over theoretical. Complimentary pours for VIP guests or staff drinks may not be rung through Toast. Each unrecorded bottle = $8.50 unaccounted.",
        action: "Implement a comps & voids policy for beverage. All comp pours should be recorded in Toast with a comp reason code." },
      { cause: "Over-pouring / free-pouring", confidence: 35, icon: Scissors, iconColor: "text-warning",
        detail: "If staff free-pour rather than using a jigger, soju cocktails likely run 10–15% over spec per drink. At 60+ soju cocktails/week, this adds up quickly.",
        action: "Enforce jigger use for all soju pours. Consider a training refresher with bar staff." },
      { cause: "Theft or shrinkage", confidence: 15, icon: AlertTriangle, iconColor: "text-destructive",
        detail: "Persistent 15%+ beverage variance is a common signal of untracked removal. Review CCTV footage if variance continues next week.",
        action: "Flag for owner review if variance persists beyond 2 consecutive weeks." },
    ],
  },
];

export default function Financials() {
  const [selectedRow, setSelectedRow] = useState<string | null>(null);
  const selectedItem = variance.find(v => v.ingredient === selectedRow);

  return (
    <div className="space-y-6 max-w-7xl">
      <h1 className="text-2xl font-bold">Financials</h1>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard title="Food Cost %" value="28.4%" change="1.2% vs last month" positive={false} info="Total food cost divided by food revenue for the current month, expressed as a percentage." />
        <MetricCard title="Weekly Food Spend" value="$5,580" change="4% reduction" positive info="Sum of all food purchases received from suppliers over the past 7 days." />
        <MetricCard title="Waste Cost (Weekly)" value="$312" change="18% reduction" positive info="Dollar value of food discarded this week, calculated from logged waste entries multiplied by each item's unit cost." />
        <MetricCard title="Revenue (MTD)" value="$94,200" change="8% vs last month" positive info="Total sales recorded month-to-date, pulled directly from POS transactions." />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-card rounded-lg border p-5">
          <h2 className="font-semibold mb-4">Budget vs. Actual</h2>
          <div className="space-y-4">
            {budgetItems.map((b, i) => {
              const pct = Math.round((b.spent / b.budget) * 100);
              const over = pct > 100;
              return (
                <div key={i}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="font-medium">{b.cat}</span>
                    <span className={cn("text-xs", over ? "text-destructive font-semibold" : "text-muted-foreground")}>
                      ${b.spent.toLocaleString()} / ${b.budget.toLocaleString()} ({pct}%)
                    </span>
                  </div>
                  <div className="h-2 bg-muted rounded-full overflow-hidden">
                    <div className={cn("h-full rounded-full transition-all", over ? "bg-destructive" : "bg-primary")} style={{ width: `${Math.min(pct, 100)}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="bg-card rounded-lg border p-5">
          <h2 className="font-semibold mb-4">Profit Margin by Category</h2>
          <div className="space-y-4">
            {profitMargins.map((p, i) => (
              <div key={i}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="font-medium">{p.cat}</span>
                  <span className={cn("text-xs font-semibold", p.margin >= 80 ? "text-success" : "text-accent")}>{p.margin}%</span>
                </div>
                <div className="h-2 bg-muted rounded-full overflow-hidden">
                  <div className={cn("h-full rounded-full", p.margin >= 80 ? "bg-success" : "bg-accent")} style={{ width: `${p.margin}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="bg-card rounded-lg border p-5">
        <div className="mb-4">
          <h2 className="font-semibold">Variance Report</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Click any row to see AI-powered diagnostic — ranked causes and recommended actions.
          </p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/50">
                <th className="text-left p-3 font-medium">Ingredient</th>
                <th className="text-left p-3 font-medium">Theoretical</th>
                <th className="text-left p-3 font-medium">Actual</th>
                <th className="text-left p-3 font-medium">Variance</th>
                <th className="text-right p-3 font-medium">Est. Cost Impact</th>
                <th className="p-3 w-10"></th>
              </tr>
            </thead>
            <tbody>
              {variance.map((v, i) => (
                <tr
                  key={i}
                  onClick={() => setSelectedRow(selectedRow === v.ingredient ? null : v.ingredient)}
                  className={cn(
                    "border-b last:border-0 cursor-pointer transition-colors",
                    selectedRow === v.ingredient ? "bg-primary/5 border-primary/20" : "hover:bg-muted/30"
                  )}
                >
                  <td className="p-3 font-medium">{v.ingredient}</td>
                  <td className="p-3">{v.theoretical}</td>
                  <td className="p-3">{v.actual}</td>
                  <td className={cn("p-3 font-medium", v.varColor)}>{v.variance}</td>
                  <td className={cn("p-3 text-right font-medium", v.impColor)}>{v.impact}</td>
                  <td className="p-3 text-muted-foreground">
                    <ChevronRight className={cn("h-4 w-4 transition-transform", selectedRow === v.ingredient && "rotate-90")} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Diagnostic Panel */}
        {selectedItem && (
          <div className="mt-5 border-t pt-5 space-y-4">
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-baseline gap-2 flex-wrap">
                <h3 className="font-semibold">{selectedItem.ingredient} — variance diagnostic</h3>
                <span className={cn("text-sm font-semibold", selectedItem.varColor)}>{selectedItem.variance}</span>
                <span className="text-xs text-muted-foreground">({selectedItem.impact} this week)</span>
              </div>
              <button onClick={() => setSelectedRow(null)} className="text-muted-foreground hover:text-foreground transition-colors">
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="space-y-3">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                Possible causes — ranked by confidence
              </p>

              {selectedItem.diagnoses.map((d, di) => {
                const Icon = d.icon;
                const isTop = di === 0;
                return (
                  <div key={di} className={cn("border rounded-lg p-4 space-y-3", isTop && "border-primary/30 bg-primary/5")}>
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex items-center gap-2 min-w-0">
                        <Icon className={cn("h-4 w-4 flex-shrink-0", d.iconColor)} />
                        <span className="font-medium text-sm">{d.cause}</span>
                        {isTop && (
                          <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-primary/10 text-primary">
                            Most likely
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        <div className="w-24 h-1.5 bg-muted rounded-full overflow-hidden">
                          <div
                            className={cn(
                              "h-full rounded-full",
                              d.confidence >= 60 ? "bg-destructive" : d.confidence >= 30 ? "bg-warning" : "bg-muted-foreground/40"
                            )}
                            style={{ width: `${d.confidence}%` }}
                          />
                        </div>
                        <span className="text-xs font-semibold text-muted-foreground tabular-nums w-9 text-right">{d.confidence}%</span>
                      </div>
                    </div>

                    <p className="text-xs text-muted-foreground leading-relaxed">{d.detail}</p>

                    <div className="flex items-start gap-2 pt-1 border-t">
                      <span className="text-[10px] font-bold uppercase tracking-wide text-primary mt-2">Action</span>
                      <p className="text-xs text-foreground mt-1.5 flex-1">{d.action}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
