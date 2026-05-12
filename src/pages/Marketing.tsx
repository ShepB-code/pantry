import { Button } from "@/components/ui/button";

const demandCampaigns = [
  {
    title: "Rainy day ramen push",
    desc: "Rain forecasted Thu-Fri. Historically your ramen sales increase 30% on rainy days. Push a warm bowl special to your email list Wednesday night.",
    badges: [{ label: "Send Wednesday 6pm", color: "bg-info/10 text-info" }, { label: "Email + Instagram", color: "bg-accent/10 text-accent" }],
  },
  {
    title: "Game day bar promo",
    desc: "Bulls play Saturday at 7pm. Bar traffic typically jumps 25%. Feature soju cocktail specials and appetizer combos.",
    badges: [{ label: "Post Friday afternoon", color: "bg-info/10 text-info" }, { label: "Instagram + in-store", color: "bg-accent/10 text-accent" }],
  },
];

const wastePromos = [
  {
    title: "Salmon special tonight",
    urgent: true,
    urgentColor: "bg-destructive/10 text-destructive",
    desc: "8 lbs of salmon expiring tomorrow. Feature a miso-glazed salmon bowl as tonight's special at $24 — projected to move 6 lbs.",
    savings: "Est. $79 in waste prevented",
  },
  {
    title: "Tofu Tuesday feature",
    urgent: true,
    urgentColor: "bg-warning/10 text-warning",
    desc: "3 containers of soft tofu expiring. Add sundubu jjigae as a $14 lunch special tomorrow.",
    savings: "Est. $18 in waste prevented",
  },
];

const trends = [
  { title: "Gochujang butter", source: "TikTok · 12M views", badge: "You have all ingredients", badgeColor: "bg-success/10 text-success" },
  { title: "Korean corn cheese", source: "Instagram · 3.2M posts", badge: "Need: sweet corn, mayo", badgeColor: "bg-warning/10 text-warning" },
  { title: "Birria-style Korean tacos", source: "TikTok · 8M views", badge: "Short rib fusion opportunity", badgeColor: "bg-info/10 text-info" },
];

export default function Marketing() {
  return (
    <div className="space-y-6 max-w-7xl">
      <h1 className="text-2xl font-bold">Marketing</h1>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-4">
          <h2 className="font-semibold">Demand-Driven Campaigns</h2>
          {demandCampaigns.map((c, i) => (
            <div key={i} className="bg-card rounded-lg border p-5 space-y-3">
              <h3 className="font-semibold">{c.title}</h3>
              <p className="text-sm text-muted-foreground">{c.desc}</p>
              <div className="flex flex-wrap gap-2">
                {c.badges.map((b, j) => (
                  <span key={j} className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${b.color}`}>{b.label}</span>
                ))}
              </div>
              <Button size="sm">Create Campaign</Button>
            </div>
          ))}
        </div>

        <div className="space-y-4">
          <h2 className="font-semibold">Waste-Prevention Promos</h2>
          {wastePromos.map((p, i) => (
            <div key={i} className="bg-card rounded-lg border p-5 space-y-3">
              <div className="flex items-center gap-2">
                <h3 className="font-semibold">{p.title}</h3>
                <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${p.urgentColor}`}>Urgent</span>
              </div>
              <p className="text-sm text-muted-foreground">{p.desc}</p>
              <p className="text-xs font-semibold text-success">{p.savings}</p>
              <Button size="sm" className="bg-accent hover:bg-accent/90 text-accent-foreground">Push Special</Button>
            </div>
          ))}
        </div>
      </div>

      <div>
        <h2 className="font-semibold mb-1">Trending Food Topics</h2>
        <p className="text-xs text-muted-foreground mb-4">Curated weekly digest of viral food trends relevant to your menu.</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {trends.map((t, i) => (
            <div key={i} className="bg-card rounded-lg border p-5 space-y-2">
              <h3 className="font-semibold">{t.title}</h3>
              <p className="text-xs text-muted-foreground">{t.source}</p>
              <span className={`inline-block text-[10px] font-semibold px-2 py-0.5 rounded-full ${t.badgeColor}`}>{t.badge}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
