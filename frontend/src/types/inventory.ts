export type QuickCountPriority = "critical" | "high" | "medium";
export type QuickCountMode = "confirm" | "numeric" | "estimate";
export type EstimateLevel = "low" | "ok" | "high";

export interface QuickCountFlags {
  belowPar: boolean;
  likelyRunOutToday: boolean;
  overstocked: boolean;
  nearingExpiration: boolean;
  countMismatch: boolean;
  orderToday: boolean;
}

export interface QuickCountItem {
  id: string;
  name: string;
  category: string;
  priority: QuickCountPriority;
  score: number;
  reasons: string[];
  expectedOnHand: number;
  expectedDisplay: string;
  parLevel: number;
  parDisplay: string;
  countUnits: string[];
  defaultCountUnit: string;
  weighable: boolean;
  vendor: string | null;
  flags: QuickCountFlags;
  submitted?: boolean;
  actualOnHand?: number;
  submittedFlags?: QuickCountFlags;
}

export interface QuickCountLine {
  itemId: string;
  name: string;
  mode: QuickCountMode;
  unit: string;
  expected: number;
  actual: number;
  flagged: boolean;
  flags: QuickCountFlags;
  submittedAt: string;
}

export interface QuickCountSession {
  sessionDate: string;
  completed: boolean;
  completedAt: string | null;
  estimatedMinutes: number;
  itemCount: number;
  submittedCount: number;
  items: QuickCountItem[];
  lines: QuickCountLine[];
}

export interface QuickCountLineSubmission {
  itemId: string;
  mode: QuickCountMode;
  value?: number | EstimateLevel;
  unit?: string;
}
