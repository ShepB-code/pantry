import { cn } from "@/lib/utils";
import { AlertTriangle, Info, TrendingUp, Megaphone, FileText } from "lucide-react";

const alertsData = [
  { unread: true, icon: AlertTriangle, color: "text-destructive", bg: "bg-destructive/5", label: "Expiring", title: "3 items expiring tomorrow", desc: "Salmon, Soft tofu, Enoki mushrooms", time: "8:02am" },
  { unread: true, icon: AlertTriangle, color: "text-warning", bg: "bg-warning/5", label: "Action needed", title: "Sysco order cutoff at 2pm", desc: "Suggested PO ready, $756.50", time: "8:00am" },
  { unread: true, icon: Info, color: "text-info", bg: "bg-info/5", label: "Info", title: "US Foods delivery arriving 10:30am", desc: "14 items, invoice auto-sync", time: "7:45am" },
  { unread: true, icon: Megaphone, color: "text-accent", bg: "bg-accent/5", label: "Trend", title: "Trending: Gochujang butter", desc: "Viral on TikTok, 12M views, all ingredients in stock", time: "7:30am" },
  { unread: false, icon: FileText, color: "text-success", bg: "", label: "Report", title: "Weekly variance report ready", desc: "Ribeye 15% over spec, Soju 16.7% over", time: "Yesterday" },
  { unread: false, icon: Info, color: "text-info", bg: "", label: "Info", title: "Kim's Produce delivery completed", desc: "8 items received, all matched invoice", time: "Yesterday" },
  { unread: false, icon: AlertTriangle, color: "text-warning", bg: "", label: "Action needed", title: "Salmon price increase detected", desc: "Pacific Seafood +10%", time: "2 days ago" },
  { unread: false, icon: FileText, color: "text-success", bg: "", label: "Report", title: "Waste-prevention special worked", desc: "Pork belly special moved 5 lbs, $62 saved", time: "2 days ago" },
  { unread: false, icon: Info, color: "text-info", bg: "", label: "Info", title: "Forecast updated", desc: "Weekend projections +25% due to Bulls game", time: "3 days ago" },
];

export default function Alerts() {
  return (
    <div className="space-y-6 max-w-7xl">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-bold">Alerts</h1>
        <span className="bg-destructive text-destructive-foreground text-xs font-semibold rounded-full px-2 py-0.5">4 unread</span>
      </div>

      <div className="space-y-2">
        {alertsData.map((a, i) => (
          <div key={i} className={cn("flex items-start gap-3 p-4 rounded-lg border transition-colors", a.unread ? `${a.bg} border-primary/10` : "bg-card")}>
            {a.unread && <div className="w-2 h-2 rounded-full bg-primary mt-1.5 shrink-0" />}
            <a.icon className={cn("h-4 w-4 mt-0.5 shrink-0", a.color)} />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-0.5">
                <span className={cn("text-[10px] font-semibold", a.color)}>{a.label}</span>
                <span className="text-xs text-muted-foreground">· {a.time}</span>
              </div>
              <p className="text-sm font-medium">{a.title}</p>
              <p className="text-xs text-muted-foreground">{a.desc}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
