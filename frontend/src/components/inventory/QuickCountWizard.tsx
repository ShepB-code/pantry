import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  completeQuickCount,
  fetchQuickCountSession,
  resetQuickCount,
  submitQuickCountLine,
} from "@/api/inventory";
import type { EstimateLevel, QuickCountItem, QuickCountMode } from "@/types/inventory";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Loader2,
  Zap,
} from "lucide-react";

type WizardState = "idle" | "counting" | "done";

const FLAG_LABELS: { key: keyof QuickCountItem["flags"]; label: string }[] = [
  { key: "belowPar", label: "Below par" },
  { key: "likelyRunOutToday", label: "May run out today" },
  { key: "overstocked", label: "Overstocked" },
  { key: "nearingExpiration", label: "Use soon" },
  { key: "countMismatch", label: "Count differs from expected" },
  { key: "orderToday", label: "Order today" },
];

function activeFlags(flags: QuickCountItem["flags"]) {
  return FLAG_LABELS.filter(({ key }) => flags[key]);
}

export function QuickCountWizard() {
  const queryClient = useQueryClient();
  const { data: session, isLoading, isError, refetch } = useQuery({
    queryKey: ["quick-count"],
    queryFn: fetchQuickCountSession,
  });

  const [wizardState, setWizardState] = useState<WizardState>("idle");
  const [index, setIndex] = useState(0);
  const [countUnit, setCountUnit] = useState<string>("");
  const [numericInput, setNumericInput] = useState("");
  const [estimate, setEstimate] = useState<EstimateLevel | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const submitMutation = useMutation({
    mutationFn: submitQuickCountLine,
    onSuccess: (result) => {
      queryClient.setQueryData(["quick-count"], result.session);
      queryClient.invalidateQueries({ queryKey: ["inventory"] });
    },
  });

  useEffect(() => {
    if (session?.completed) {
      setWizardState("done");
    }
  }, [session?.completed]);

  const completeMutation = useMutation({
    mutationFn: completeQuickCount,
    onSuccess: (data) => {
      queryClient.setQueryData(["quick-count"], data);
      queryClient.invalidateQueries({ queryKey: ["inventory"] });
      setWizardState("done");
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16 text-muted-foreground">
        <Loader2 className="h-5 w-5 animate-spin mr-2" />
        Loading quick count…
      </div>
    );
  }

  if (isError || !session?.items?.length) {
    return (
      <div className="bg-card rounded-lg border p-6 max-w-2xl mx-auto text-center space-y-3">
        <p className="text-sm text-muted-foreground">Could not load today&apos;s quick count list.</p>
        <Button variant="outline" onClick={() => refetch()}>Retry</Button>
      </div>
    );
  }

  const items = session.items;
  const current = items[index];
  const lines = session.lines ?? [];
  const criticalCount = items.filter((i) => i.priority === "critical").length;
  const highCount = items.filter((i) => i.priority === "high").length;

  const resetItemInputs = (item: QuickCountItem) => {
    setCountUnit(item.defaultCountUnit);
    setNumericInput("");
    setEstimate(null);
  };

  const startCount = () => {
    setWizardState("counting");
    setIndex(0);
    resetItemInputs(items[0]);
  };

  const resetWizard = async () => {
    const data = await resetQuickCount();
    queryClient.setQueryData(["quick-count"], data);
    setWizardState("idle");
    setIndex(0);
  };

  const handleSubmit = async (mode: QuickCountMode, value?: number | EstimateLevel) => {
    if (!current) return;
    setSubmitting(true);
    try {
      const result = await submitMutation.mutateAsync({
        itemId: current.id,
        mode,
        value,
        unit: countUnit || current.defaultCountUnit,
      });
      const updated = result.session;
      if (index < items.length - 1) {
        const next = index + 1;
        setIndex(next);
        resetItemInputs(updated.items[next]);
      } else if (updated.submittedCount >= updated.itemCount) {
        await completeMutation.mutateAsync();
      } else {
        setWizardState("done");
      }
    } finally {
      setSubmitting(false);
    }
  };

  const looksRight = () => handleSubmit("confirm");

  const submitNumeric = () => {
    const n = parseFloat(numericInput);
    if (Number.isNaN(n)) return;
    handleSubmit("numeric", n);
  };

  const submitEstimate = (level: EstimateLevel) => {
    setEstimate(level);
    handleSubmit("estimate", level);
  };

  const isEstimateMode = countUnit === "estimate";

  if (wizardState === "idle" && !session.completed) {
    return (
      <div className="bg-card rounded-lg border p-6 max-w-2xl mx-auto space-y-5">
        <div className="flex items-start gap-3">
          <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
            <Zap className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h2 className="font-semibold text-lg">Quick Count</h2>
            <p className="text-sm text-muted-foreground mt-1">
              A {session.estimatedMinutes}–minute daily pulse check on your {items.length} most critical
              items from xtraCHEF, ranked using Toast sales.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-3">
          <div className="rounded-lg border p-3 text-center">
            <p className="text-xl font-bold text-destructive">{criticalCount}</p>
            <p className="text-[11px] text-muted-foreground mt-0.5">Critical items</p>
          </div>
          <div className="rounded-lg border p-3 text-center">
            <p className="text-xl font-bold text-warning">{highCount}</p>
            <p className="text-[11px] text-muted-foreground mt-0.5">High priority</p>
          </div>
          <div className="rounded-lg border p-3 text-center">
            <p className="text-xl font-bold">~{session.estimatedMinutes} min</p>
            <p className="text-[11px] text-muted-foreground mt-0.5">Est. time</p>
          </div>
        </div>

        <div className="space-y-1.5 max-h-64 overflow-y-auto">
          {items.map((item) => (
            <div key={item.id} className="flex items-center gap-3 text-sm py-1.5 border-b last:border-0">
              <span
                className={cn(
                  "h-2 w-2 rounded-full flex-shrink-0",
                  item.priority === "critical"
                    ? "bg-destructive"
                    : item.priority === "high"
                      ? "bg-warning"
                      : "bg-muted-foreground/40",
                )}
              />
              <span className="font-medium flex-1 truncate">{item.name}</span>
              <span className="text-xs text-muted-foreground truncate max-w-[40%]">
                {item.reasons[0]}
              </span>
            </div>
          ))}
        </div>

        <Button onClick={startCount} className="w-full" size="lg">
          <Zap className="h-4 w-4 mr-2" /> Start Quick Count
        </Button>
      </div>
    );
  }

  if (wizardState === "counting" && current) {
    const previewFlags = activeFlags(current.flags);

    return (
      <div className="max-w-2xl mx-auto space-y-4">
        <div className="flex items-center gap-3">
          <span className="text-xs font-semibold tabular-nums text-muted-foreground">
            {index + 1} / {items.length}
          </span>
          <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
            <div
              className="h-full bg-primary rounded-full transition-all"
              style={{ width: `${(index / items.length) * 100}%` }}
            />
          </div>
          <button
            type="button"
            onClick={resetWizard}
            className="text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            Cancel
          </button>
        </div>

        {index > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {lines.map((line) => (
              <span
                key={line.itemId}
                className={cn(
                  "text-[10px] px-2 py-0.5 rounded-full font-medium",
                  line.flagged ? "bg-warning/10 text-warning" : "bg-success/10 text-success",
                )}
              >
                {line.flagged ? "⚠" : "✓"} {line.name.split(" ")[0]}
              </span>
            ))}
          </div>
        )}

        <div className="bg-card rounded-xl border p-6 space-y-5">
          <div className="flex items-start justify-between">
            <div className="space-y-1">
              <span
                className={cn(
                  "text-[10px] font-semibold px-2 py-0.5 rounded-full",
                  current.priority === "critical"
                    ? "bg-destructive/10 text-destructive"
                    : current.priority === "high"
                      ? "bg-warning/10 text-warning"
                      : "bg-muted text-muted-foreground",
                )}
              >
                {current.priority === "critical"
                  ? "Critical"
                  : current.priority === "high"
                    ? "High"
                    : "Medium"}
              </span>
              <p className="text-xs text-muted-foreground">
                {current.category}
                {current.vendor ? ` · ${current.vendor}` : ""} · {current.reasons.join(" · ")}
              </p>
            </div>
            {index > 0 && (
              <button
                type="button"
                onClick={() => {
                  const prev = index - 1;
                  setIndex(prev);
                  resetItemInputs(items[prev]);
                }}
                className="p-1 rounded hover:bg-muted transition-colors"
              >
                <ChevronLeft className="h-4 w-4 text-muted-foreground" />
              </button>
            )}
          </div>

          <div className="space-y-1">
            <h3 className="text-2xl font-bold">{current.name}</h3>
            <div className="flex flex-wrap gap-4 text-sm">
              <div>
                <span className="text-xs text-muted-foreground">Expected: </span>
                <span className="font-semibold">{current.expectedDisplay}</span>
              </div>
              <div>
                <span className="text-xs text-muted-foreground">Par: </span>
                <span className="font-semibold">{current.parDisplay}</span>
              </div>
            </div>
            {previewFlags.length > 0 && (
              <div className="flex flex-wrap gap-1.5 pt-2">
                {previewFlags.map(({ key, label }) => (
                  <span
                    key={key}
                    className="text-[10px] px-2 py-0.5 rounded-full bg-muted text-muted-foreground font-medium"
                  >
                    {label}
                  </span>
                ))}
              </div>
            )}
          </div>

          <div className="flex flex-wrap gap-2">
            {current.countUnits.map((unit) => (
              <button
                key={unit}
                type="button"
                onClick={() => setCountUnit(unit)}
                className={cn(
                  "text-xs px-3 py-1.5 rounded-full border transition-colors capitalize",
                  (countUnit || current.defaultCountUnit) === unit
                    ? "bg-primary text-primary-foreground border-primary"
                    : "hover:bg-muted",
                )}
              >
                {unit}
              </button>
            ))}
          </div>

          {!isEstimateMode && (
            <>
              <Button
                onClick={looksRight}
                className="w-full"
                size="lg"
                disabled={submitting}
              >
                <CheckCircle2 className="h-4 w-4 mr-2" />
                Looks right — confirm {current.expectedDisplay}
              </Button>

              <div className="flex items-center gap-2">
                <div className="flex-1 h-px bg-border" />
                <p className="text-[10px] uppercase tracking-wide text-muted-foreground font-medium">
                  or enter actual
                </p>
                <div className="flex-1 h-px bg-border" />
              </div>

              <div className="flex gap-2">
                <input
                  value={numericInput}
                  onChange={(e) => setNumericInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && submitNumeric()}
                  placeholder={`Amount in ${countUnit || current.defaultCountUnit}`}
                  className="flex-1 rounded-lg border bg-background px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                />
                <Button
                  onClick={submitNumeric}
                  variant="outline"
                  size="lg"
                  disabled={!numericInput.trim() || submitting}
                >
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </>
          )}

          {isEstimateMode && (
            <div className="space-y-2">
              <p className="text-xs text-muted-foreground text-center">
                Quick estimate vs par ({current.parDisplay})
              </p>
              <div className="grid grid-cols-3 gap-2">
                {(["low", "ok", "high"] as EstimateLevel[]).map((level) => (
                  <Button
                    key={level}
                    variant={estimate === level ? "default" : "outline"}
                    size="lg"
                    className="capitalize"
                    disabled={submitting}
                    onClick={() => submitEstimate(level)}
                  >
                    {level}
                  </Button>
                ))}
              </div>
            </div>
          )}

          <p className="text-[11px] text-muted-foreground text-center">
            Variance &gt;10% from expected will be flagged
          </p>
        </div>
      </div>
    );
  }

  const flaggedLines = lines.filter((l) => l.flagged);
  const actionFlags = lines.flatMap((line) =>
    activeFlags(line.flags).map((f) => ({ ...f, itemName: line.name })),
  );

  return (
    <div className="max-w-2xl mx-auto space-y-4">
      <div className="bg-card rounded-xl border p-6 space-y-5">
        <div className="flex items-start gap-3">
          <div className="h-10 w-10 rounded-lg bg-success/10 flex items-center justify-center flex-shrink-0">
            <CheckCircle2 className="h-5 w-5 text-success" />
          </div>
          <div>
            <h2 className="font-semibold text-lg">Quick Count Complete</h2>
            <p className="text-sm text-muted-foreground mt-0.5">
              {lines.length} items checked
              {flaggedLines.length > 0
                ? ` · ${flaggedLines.length} flagged for investigation`
                : " · No variance flags"}
            </p>
          </div>
        </div>

        {flaggedLines.length > 0 && (
          <div className="rounded-lg border border-warning/30 bg-warning/5 p-4 space-y-3">
            <p className="text-sm font-semibold flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-warning" /> Items to investigate
            </p>
            {flaggedLines.map((line) => (
              <div key={line.itemId} className="flex items-center justify-between text-sm gap-2">
                <span className="font-medium truncate">{line.name}</span>
                <div className="flex items-baseline gap-3 text-xs flex-shrink-0">
                  <span className="text-muted-foreground">
                    Expected: <span className="font-medium text-foreground">{line.expected}</span>
                  </span>
                  <span className="text-muted-foreground">
                    Actual: <span className="font-medium text-warning">{line.actual}</span>
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}

        {actionFlags.length > 0 && (
          <div className="rounded-lg border p-4 space-y-2">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Pantry flags
            </p>
            <ul className="text-sm space-y-1">
              {[...new Map(actionFlags.map((f) => [`${f.itemName}-${f.label}`, f])).values()].map(
                (f) => (
                  <li key={`${f.itemName}-${f.label}`}>
                    <span className="font-medium">{f.itemName}</span>
                    <span className="text-muted-foreground"> — {f.label}</span>
                  </li>
                ),
              )}
            </ul>
          </div>
        )}

        {flaggedLines.length === 0 && (
          <div className="rounded-lg border border-success/30 bg-success/5 p-4">
            <p className="text-sm">All items within normal range. No action needed.</p>
          </div>
        )}

        <div className="space-y-2">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Full summary
          </p>
          {lines.map((line) => (
            <div
              key={line.itemId}
              className="flex items-center justify-between text-sm py-1.5 border-b last:border-0 gap-2"
            >
              <span className="font-medium truncate">{line.name}</span>
              <div className="flex items-center gap-2 flex-shrink-0">
                {line.actual !== line.expected && (
                  <span className="text-xs text-muted-foreground line-through">{line.expected}</span>
                )}
                <span className="font-semibold">{line.actual}</span>
                {line.flagged ? (
                  <AlertTriangle className="h-3.5 w-3.5 text-warning" />
                ) : (
                  <CheckCircle2 className="h-3.5 w-3.5 text-success" />
                )}
              </div>
            </div>
          ))}
        </div>

        <Button
          onClick={() => void resetWizard()}
          variant="outline"
          className="w-full"
        >
          Start new quick count
        </Button>
      </div>
    </div>
  );
}
