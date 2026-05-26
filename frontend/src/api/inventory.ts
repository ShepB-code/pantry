import type { QuickCountLineSubmission, QuickCountSession } from "@/types/inventory";

export interface InventoryItemRow {
  id: string;
  name: string;
  inventoryItem: string;
  catalogSource: string;
  category: string;
  unit: string;
  vendor: string | null;
  onHand: number;
  parLevel: number | null;
  lastCountSource: string | null;
  lastCountedAt: string | null;
  status: string;
  statusColor: string;
}

export interface InventoryResponse {
  locationId: string;
  items: InventoryItemRow[];
  onHand: Record<string, number>;
}

export async function fetchInventory(): Promise<InventoryResponse> {
  const res = await fetch("/api/inventory");
  if (!res.ok) throw new Error("Failed to load inventory");
  return res.json();
}

export async function fetchQuickCountSession(): Promise<QuickCountSession> {
  const res = await fetch("/api/inventory/quick-count");
  if (!res.ok) throw new Error("Failed to load quick count");
  return res.json();
}

export async function submitQuickCountLine(
  body: QuickCountLineSubmission,
): Promise<{ line: QuickCountSession["lines"][0]; session: QuickCountSession }> {
  const res = await fetch("/api/inventory/quick-count/lines", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Failed to submit count");
  }
  return res.json();
}

export async function completeQuickCount(): Promise<QuickCountSession> {
  const res = await fetch("/api/inventory/quick-count/complete", { method: "POST" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Failed to complete quick count");
  }
  return res.json();
}

export async function resetQuickCount(): Promise<QuickCountSession> {
  const res = await fetch("/api/inventory/quick-count/reset", { method: "POST" });
  if (!res.ok) throw new Error("Failed to reset quick count");
  return res.json();
}
