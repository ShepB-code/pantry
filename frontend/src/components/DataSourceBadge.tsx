import { cn } from "@/lib/utils";

export type DataSourceKind = "mock" | "live" | "partial";

const config: Record<
  DataSourceKind,
  { label: string; title: string; className: string }
> = {
  mock: {
    label: "Mock",
    title: "Placeholder for UI reference — not connected to the database",
    className: "border-warning/40 bg-warning/10 text-warning",
  },
  live: {
    label: "Live",
    title: "Loaded from the Pantry API / database",
    className: "border-success/40 bg-success/10 text-success",
  },
  partial: {
    label: "Partial",
    title: "Mix of real and estimated values — see section notes",
    className: "border-info/40 bg-info/10 text-info",
  },
};

interface DataSourceBadgeProps {
  source: DataSourceKind;
  className?: string;
}

export function DataSourceBadge({ source, className }: DataSourceBadgeProps) {
  const { label, title, className: sourceClass } = config[source];
  return (
    <span
      title={title}
      className={cn(
        "inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide",
        sourceClass,
        className,
      )}
    >
      {label}
    </span>
  );
}

interface SectionLabelProps {
  title: string;
  source: DataSourceKind;
  hint?: string;
  className?: string;
}

export function SectionLabel({ title, source, hint, className }: SectionLabelProps) {
  return (
    <div className={cn("flex flex-wrap items-center gap-2", className)}>
      <h2 className="font-semibold text-lg">{title}</h2>
      <DataSourceBadge source={source} />
      {hint && <span className="text-xs text-muted-foreground">{hint}</span>}
    </div>
  );
}
