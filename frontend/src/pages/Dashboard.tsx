import { useState, useEffect } from "react";
import { MetricCard } from "@/components/MetricCard";
import { DataSourceBadge, SectionLabel } from "@/components/DataSourceBadge";
import { Truck, AlertTriangle, Info, TrendingUp, ChevronLeft, ChevronRight, Lightbulb, RefreshCw } from "lucide-react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";

const expiringWindows = [
  { label: "24 hours", value: 3, change: "1 fewer vs yesterday", positive: true },
  { label: "48 hours", value: 7, change: "3 fewer vs last week", positive: true },
  { label: "7 days", value: 18, change: "2 more vs last week", positive: false },
  { label: "14 days", value: 34, change: "5 fewer vs last period", positive: true },
  { label: "1 month", value: 62, change: "On par with last month", positive: true },
];

const alerts = [
  { color: "destructive" as const, icon: AlertTriangle, label: "Expiring tomorrow", desc: "Salmon (8 lbs), Soft tofu (3 containers), Enoki mushrooms (2 lbs)", action: "Action needed", bg: "bg-destructive/10", text: "text-destructive" },
  { color: "warning" as const, icon: AlertTriangle, label: "Place order by 2pm", desc: "Sysco order cutoff, suggested PO ready for review", action: "In 4 hours", bg: "bg-warning/10", text: "text-warning" },
  { color: "info" as const, icon: Info, label: "Delivery arriving", desc: "US Foods delivery, 14 items, ETA 10:30am", action: "In 2 hours", bg: "bg-info/10", text: "text-info" },
  { color: "success" as const, icon: TrendingUp, label: "Variance alert", desc: "Ribeye usage was 15% over spec last week, review portioning", action: "Weekly", bg: "bg-success/10", text: "text-success" },
  { color: "accent" as const, icon: Lightbulb, label: "Trending now", desc: "Gochujang butter is trending on TikTok, you have all ingredients in stock", action: "Trend alert", bg: "bg-accent/10", text: "text-accent" },
];

const deliveries = [
  { name: "US Foods", time: "Today 10:30am", items: 14, badge: "In transit", badgeClass: "bg-info/10 text-info" },
  { name: "Kim's Produce", time: "Today 2:00pm", items: 8, badge: "Confirmed", badgeClass: "bg-success/10 text-success" },
  { name: "Pacific Seafood", time: "Wed 8:00am", items: 5, badge: "Scheduled", badgeClass: "bg-muted text-muted-foreground" },
];

const defaultRevenueTrend = [
  { day: "Wed", revenue: 6800, cost: 1980 },
  { day: "Thu", revenue: 7200, cost: 2050 },
  { day: "Fri", revenue: 9400, cost: 2680 },
  { day: "Sat", revenue: 11200, cost: 3180 },
  { day: "Sun", revenue: 9800, cost: 2790 },
  { day: "Mon", revenue: 7100, cost: 2020 },
  { day: "Tue", revenue: 8420, cost: 2390 },
];

const wasteByCategory = [
  { category: "Produce", waste: 142 },
  { category: "Seafood", waste: 86 },
  { category: "Dairy", waste: 44 },
  { category: "Meat", waste: 28 },
  { category: "Pantry", waste: 12 },
];

const costBreakdown = [
  { name: "Food", value: 28.4, color: "hsl(var(--primary))" },
  { name: "Labor", value: 31.2, color: "hsl(var(--warning))" },
  { name: "Overhead", value: 18.6, color: "hsl(var(--info))" },
  { name: "Profit", value: 21.8, color: "hsl(var(--success))" },
];

const tooltipStyle = {
  backgroundColor: "hsl(var(--background))",
  border: "1px solid hsl(var(--border))",
  borderRadius: "0.5rem",
  fontSize: "12px",
};

function formatRefreshTime(date: Date) {
  return date.toLocaleString("en-US", {
    month: "short", day: "numeric", year: "numeric",
    hour: "numeric", minute: "2-digit", second: "2-digit", hour12: true,
  });
}

const revenueTrend = defaultRevenueTrend;
const todayRev = revenueTrend[revenueTrend.length - 1].revenue;

export default function Dashboard() {
  const [windowIdx, setWindowIdx] = useState(1);
  const win = expiringWindows[windowIdx];
  const cycle = (dir: 1 | -1) =>
    setWindowIdx((i) => (i + dir + expiringWindows.length) % expiringWindows.length);

  const wasteDecreased = true;
  const wasteChange = wasteDecreased ? "18% reduction" : "12% increase";

  const [lastRefreshed, setLastRefreshed] = useState(new Date());
  const [refreshing, setRefreshing] = useState(false);

  const handleRefresh = () => {
    setRefreshing(true);
    setTimeout(() => {
      setLastRefreshed(new Date());
      setRefreshing(false);
    }, 800);
  };

  useEffect(() => {
    const interval = setInterval(() => setLastRefreshed(new Date()), 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-6 max-w-7xl">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Good morning, Chef Lim</h1>
          <p className="text-muted-foreground text-sm">Here's what's happening at Perilla today.</p>
        </div>
        <div className="flex items-center gap-2 mt-1 shrink-0">
          <span className="text-xs text-muted-foreground">
            Last refreshed: <span className="font-medium text-foreground">{formatRefreshTime(lastRefreshed)}</span>
          </span>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded-md border hover:bg-muted transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`h-3 w-3 ${refreshing ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard className="shadow-lg hover:shadow-xl hover:-translate-y-0.5 transition-all duration-200" title="Today's Projected Revenue" value={`$${todayRev.toLocaleString()}`} change="sample data" positive source="mock" info="Placeholder until revenue is wired to Postgres POS rollups." />
        <MetricCard className="shadow-lg hover:shadow-xl hover:-translate-y-0.5 transition-all duration-200" title="Food Cost %" value="28.4%" change="1.2% improvement vs last week" positive source="mock" info="Cost of food sold divided by food revenue over the last 7 days, expressed as a percentage." />
        <MetricCard
          className="shadow-lg hover:shadow-xl hover:-translate-y-0.5 transition-all duration-200"
          info="Count of inventory items reaching their use-by date within the selected window, based on receiving dates and shelf-life data."
          title={
            <div className="flex items-center justify-between gap-2">
              <span>Items Expiring Within</span>
              <div className="flex items-center gap-0.5">
                <button
                  onClick={() => cycle(-1)}
                  className="p-0.5 rounded hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
                  aria-label="Previous window"
                >
                  <ChevronLeft className="h-3 w-3" />
                </button>
                <span className="text-xs font-medium text-foreground tabular-nums min-w-[3.25rem] text-center">
                  {win.label}
                </span>
                <button
                  onClick={() => cycle(1)}
                  className="p-0.5 rounded hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
                  aria-label="Next window"
                >
                  <ChevronRight className="h-3 w-3" />
                </button>
              </div>
            </div>
          }
          value={String(win.value)}
          change={win.change}
          positive={win.positive}
          source="mock"
        />
        <MetricCard
          className="shadow-lg hover:shadow-xl hover:-translate-y-0.5 transition-all duration-200"
          title="Weekly Waste"
          value="$312"
          change={wasteChange}
          positive={wasteDecreased}
          source="mock"
          info="Dollar value of food discarded this week, calculated from logged waste entries multiplied by each item's unit cost."
        />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-card rounded-lg border p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-semibold text-sm">Revenue vs Food Cost</h3>
                <DataSourceBadge source="mock" />
              </div>
              <p className="text-xs text-muted-foreground">Last 7 days · sample data</p>
            </div>
            <div className="flex items-center gap-3 text-xs">
              <span className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-success" /> Revenue
              </span>
              <span className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-destructive" /> Food cost
              </span>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={revenueTrend} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
              <defs>
                <linearGradient id="revFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="hsl(var(--success))" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="hsl(var(--success))" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="costFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="hsl(var(--destructive))" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="hsl(var(--destructive))" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
              <XAxis dataKey="day" stroke="hsl(var(--muted-foreground))" fontSize={11} tickLine={false} axisLine={false} />
              <YAxis stroke="hsl(var(--muted-foreground))" fontSize={11} tickLine={false} axisLine={false} tickFormatter={(v) => `$${v / 1000}k`} />
              <Tooltip contentStyle={tooltipStyle} formatter={(v: number) => `$${v.toLocaleString()}`} />
              <Area type="monotone" dataKey="revenue" stroke="hsl(var(--success))" strokeWidth={2} fill="url(#revFill)" />
              <Area type="monotone" dataKey="cost" stroke="hsl(var(--destructive))" strokeWidth={2} fill="url(#costFill)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-card rounded-lg border p-5">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="font-semibold text-sm">Cost Breakdown</h3>
            <DataSourceBadge source="mock" />
          </div>
          <p className="text-xs text-muted-foreground mb-2">% of revenue</p>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={costBreakdown} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={45} outerRadius={75} paddingAngle={2}>
                {costBreakdown.map((entry, i) => (
                  <Cell key={i} fill={entry.color} stroke="hsl(var(--background))" strokeWidth={2} />
                ))}
              </Pie>
              <Tooltip contentStyle={tooltipStyle} formatter={(v: number) => `${v}%`} />
              <Legend iconType="circle" wrapperStyle={{ fontSize: "11px" }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        <div className="lg:col-span-3 bg-card rounded-lg border p-5 space-y-3">
          <SectionLabel title="Today's Alerts" source="mock" />
          {alerts.map((a, i) => (
            <div key={i} className={`flex items-start gap-3 rounded-md p-3 ${a.bg}`}>
              <a.icon className={`h-4 w-4 mt-0.5 shrink-0 ${a.text}`} />
              <div className="flex-1 min-w-0">
                <p className={`text-sm font-semibold ${a.text}`}>{a.label}</p>
                <p className="text-xs text-muted-foreground mt-0.5">{a.desc}</p>
              </div>
              <span className="text-[10px] font-medium text-muted-foreground whitespace-nowrap mt-0.5">{a.action}</span>
            </div>
          ))}
        </div>

        <div className="lg:col-span-2 space-y-6">
          <div className="bg-card rounded-lg border p-5">
            <div className="flex items-center gap-2 mb-3">
              <h3 className="font-semibold text-sm">Waste by Category</h3>
              <DataSourceBadge source="mock" />
            </div>
            <p className="text-xs text-muted-foreground mb-3">This week ($)</p>
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={wasteByCategory} layout="vertical" margin={{ top: 0, right: 10, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" horizontal={false} />
                <XAxis type="number" stroke="hsl(var(--muted-foreground))" fontSize={11} tickLine={false} axisLine={false} />
                <YAxis dataKey="category" type="category" stroke="hsl(var(--muted-foreground))" fontSize={11} tickLine={false} axisLine={false} width={65} />
                <Tooltip contentStyle={tooltipStyle} formatter={(v: number) => `$${v}`} cursor={{ fill: "hsl(var(--muted))" }} />
                <Bar dataKey="waste" fill="hsl(var(--primary))" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="bg-card rounded-lg border p-5">
            <div className="flex items-center gap-2 mb-3">
              <Truck className="h-4 w-4 text-muted-foreground" />
              <h3 className="font-semibold text-sm">Upcoming Deliveries</h3>
              <DataSourceBadge source="mock" />
            </div>
            <div className="space-y-3">
              {deliveries.map((d, i) => (
                <div key={i} className="flex items-center justify-between text-sm">
                  <div>
                    <p className="font-medium">{d.name}</p>
                    <p className="text-xs text-muted-foreground">{d.time} · {d.items} items</p>
                  </div>
                  <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${d.badgeClass}`}>{d.badge}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
