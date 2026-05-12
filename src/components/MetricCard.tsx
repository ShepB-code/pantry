import { cn } from "@/lib/utils";
import { Info } from "lucide-react";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";

interface MetricCardProps {
  title: React.ReactNode;
  value: string;
  change?: string;
  positive?: boolean;
  children?: React.ReactNode;
  className?: string;
  info?: string;
}

export function MetricCard({ title, value, change, positive, children, className, info }: MetricCardProps) {
  return (
    <div className={cn("bg-card rounded-lg border p-5 relative", className)}>
      {info && (
        <Popover>
          <PopoverTrigger asChild>
            <button
              type="button"
              aria-label="About this metric"
              className="absolute top-2 right-2 p-1 rounded-md text-muted-foreground/60 hover:text-foreground hover:bg-muted transition-colors"
            >
              <Info className="h-3.5 w-3.5" />
            </button>
          </PopoverTrigger>
          <PopoverContent side="top" align="end" className="w-64 text-xs leading-relaxed">
            {info}
          </PopoverContent>
        </Popover>
      )}
      <div className="text-sm text-muted-foreground mb-1 pr-6">{title}</div>
      <p className="text-2xl font-bold tracking-tight">{value}</p>
      {change && (
        <p className={cn("text-xs mt-1 font-medium", positive ? "text-success" : "text-destructive")}>
          {positive ? "↑" : "↓"} {change}
        </p>
      )}
      {children}
    </div>
  );
}
