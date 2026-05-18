import { MetricCard } from "@/components/MetricCard";
import { Button } from "@/components/ui/button";
import { Cloud, Calendar, Trophy } from "lucide-react";

const coverData = [140, 155, 180, 210, 245, 195, 115];
const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const maxCover = Math.max(...coverData);

const poItems = [
  { item: "Ribeye (Prime)", stock: "42 lbs", need: "65 lbs", order: "25 lbs", unit: "$18.50/lb", total: "$462.50" },
  { item: "Chicken thigh", stock: "28 lbs", need: "50 lbs", order: "25 lbs", unit: "$4.20/lb", total: "$105.00" },
  { item: "Soju (assorted)", stock: "24 btl", need: "40 btl", order: "18 btl", unit: "$8.50/btl", total: "$153.00" },
  { item: "Sesame oil", stock: "6 btl", need: "4 btl", order: "—", unit: "—", total: "—" },
  { item: "Soy sauce", stock: "3 gal", need: "5 gal", order: "3 gal", unit: "$12.00/gal", total: "$36.00" },
];

export default function Forecasting() {
  return (
    <div className="space-y-6 max-w-7xl">
      <h1 className="text-2xl font-bold">Forecasting</h1>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <MetricCard title="Projected Covers This Week" value="1,240" info="Forecasted number of guests served this week, based on prior weeks' covers adjusted for reservations, weather, and local events.">
          <div className="flex items-end gap-1 mt-3 h-12">
            {coverData.map((v, i) => (
              <div key={i} className="flex-1 flex flex-col items-center gap-1">
                <div className="w-full bg-primary/80 rounded-sm" style={{ height: `${(v / maxCover) * 48}px` }} />
                <span className="text-[9px] text-muted-foreground">{days[i]}</span>
              </div>
            ))}
          </div>
        </MetricCard>
        <MetricCard title="Forecast Accuracy (4 Weeks)" value="94.2%" change="5.2% improvement" positive info="Average accuracy of cover forecasts vs actual covers over the last 4 weeks, calculated as 100% minus mean absolute percentage error.">
          <div className="flex items-end gap-1 mt-3 h-8">
            {[91, 89, 93, 94].map((v, i) => (
              <div key={i} className="flex-1 bg-primary/60 rounded-sm" style={{ height: `${(v / 100) * 32}px` }} />
            ))}
          </div>
        </MetricCard>
        <MetricCard title="External Factors Detected" value="" info="Outside signals (weather, sports, holidays, local events) detected for the upcoming week that may shift demand from baseline.">
          <div className="space-y-2 mt-1">
            <div className="flex items-center gap-2 text-xs"><Cloud className="h-3.5 w-3.5 text-info" /><span className="text-info font-medium">Rain Thu-Fri</span><span className="text-muted-foreground">+15% dine-in</span></div>
            <div className="flex items-center gap-2 text-xs"><Trophy className="h-3.5 w-3.5 text-accent" /><span className="text-accent font-medium">Bulls game Sat</span><span className="text-muted-foreground">+25% bar traffic</span></div>
            <div className="flex items-center gap-2 text-xs"><Calendar className="h-3.5 w-3.5 text-success" /><span className="text-success font-medium">No holidays</span><span className="text-muted-foreground">this week</span></div>
          </div>
        </MetricCard>
      </div>

      <div className="bg-card rounded-lg border p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="font-semibold">Suggested Purchase Order — Sysco</h2>
            <p className="text-xs text-muted-foreground">Due by 2pm today</p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm">Edit order</Button>
            <Button size="sm">Approve & send</Button>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/50">
                <th className="text-left p-3 font-medium">Item</th>
                <th className="text-left p-3 font-medium">Current Stock</th>
                <th className="text-left p-3 font-medium">Forecasted Need</th>
                <th className="text-left p-3 font-medium">Suggested Order</th>
                <th className="text-left p-3 font-medium">Unit Cost</th>
                <th className="text-right p-3 font-medium">Total</th>
              </tr>
            </thead>
            <tbody>
              {poItems.map((r, i) => (
                <tr key={i} className="border-b last:border-0">
                  <td className="p-3 font-medium">{r.item}</td>
                  <td className="p-3">{r.stock}</td>
                  <td className="p-3">{r.need}</td>
                  <td className="p-3">{r.order}</td>
                  <td className="p-3">{r.unit}</td>
                  <td className="p-3 text-right">{r.total}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-right font-bold mt-3">Estimated total: $756.50</p>
      </div>
    </div>
  );
}
