import { useState } from "react";
import { cn } from "@/lib/utils";
import {
  Plus, Send, X, FileText, ChevronDown, ChevronUp, Trash2, Building2,
  Upload, CheckCircle2, AlertTriangle, ChevronRight, RefreshCw, Package,
} from "lucide-react";

const initialSuppliers = [
  { name: "Sysco", type: "Broadline", deliveries: "Mon, Wed, Fri", cutoff: "Day before, 2pm", spend: "$3,240/wk" },
  { name: "Kim's Produce", type: "Specialty produce", deliveries: "Tue, Thu", cutoff: "Same day, 6am", spend: "$890/wk" },
  { name: "Pacific Seafood", type: "Seafood", deliveries: "Mon, Wed", cutoff: "Day before, 12pm", spend: "$1,450/wk" },
];

const spendData = [
  { name: "Sysco", weeks: ["$3,180", "$3,420", "$3,100", "$3,240"], total: "$12,940", trend: "↓ 2%", trendGood: true },
  { name: "Kim's Produce", weeks: ["$920", "$850", "$910", "$890"], total: "$3,570", trend: "↓ 3%", trendGood: true },
  { name: "Pacific Seafood", weeks: ["$1,500", "$1,380", "$1,520", "$1,450"], total: "$5,850", trend: "↓ 5%", trendGood: true },
];

const priceWatch = [
  { item: "Ribeye (Prime)", supplier: "Sysco", from: "$17.80/lb", to: "$18.50/lb", change: "+3.9%", severity: "warning" },
  { item: "Salmon fillet", supplier: "Pacific Seafood", from: "$12.00/lb", to: "$13.20/lb", change: "+10%", severity: "destructive" },
  { item: "Sesame oil", supplier: "Sysco", from: "$7.50/btl", to: "$8.00/btl", change: "+6.7%", severity: "warning" },
];

interface InvoiceChange {
  item: string;
  unit: string;
  oldPrice: number;
  newPrice: number;
  pctChange: number;
  severity: "warning" | "destructive";
  affectedDishes: {
    name: string;
    currentCost: number;
    newCost: number;
    currentMargin: number;
    newMargin: number;
    currentMenuPrice: number;
  }[];
}

type ParseState = "idle" | "uploading" | "parsing" | "done" | "accepted";

const catalogItems: Record<string, { name: string; unit: string; unitCost: number }[]> = {
  "Sysco": [
    { name: "Ribeye (Prime)", unit: "lb", unitCost: 18.50 },
    { name: "Chicken thigh", unit: "lb", unitCost: 4.20 },
    { name: "Soju (assorted)", unit: "btl", unitCost: 8.50 },
    { name: "Sesame oil", unit: "btl", unitCost: 8.00 },
    { name: "Soy sauce", unit: "gal", unitCost: 12.00 },
    { name: "Jasmine rice", unit: "lb", unitCost: 0.80 },
    { name: "Gochujang paste", unit: "jar", unitCost: 5.00 },
  ],
  "Kim's Produce": [
    { name: "Napa cabbage", unit: "head", unitCost: 2.50 },
    { name: "Enoki mushrooms", unit: "lb", unitCost: 6.00 },
    { name: "Bean sprouts", unit: "lb", unitCost: 1.80 },
    { name: "Scallions", unit: "bunch", unitCost: 1.20 },
    { name: "Spinach", unit: "lb", unitCost: 3.50 },
    { name: "Zucchini", unit: "lb", unitCost: 2.00 },
  ],
  "Pacific Seafood": [
    { name: "Salmon fillet", unit: "lb", unitCost: 13.20 },
    { name: "Shrimp (16/20)", unit: "lb", unitCost: 14.00 },
    { name: "Squid", unit: "lb", unitCost: 7.50 },
    { name: "Mussels", unit: "lb", unitCost: 5.00 },
    { name: "Sea bass", unit: "lb", unitCost: 16.00 },
  ],
};

interface POLineItem {
  name: string;
  unit: string;
  unitCost: number;
  qty: number;
}

interface PurchaseOrder {
  id: string;
  supplier: string;
  items: POLineItem[];
  status: "draft" | "sent";
  createdAt: string;
}

const samplePOs: PurchaseOrder[] = [
  {
    id: "PO-1042",
    supplier: "Sysco",
    items: [
      { name: "Ribeye (Prime)", unit: "lb", unitCost: 18.50, qty: 25 },
      { name: "Chicken thigh", unit: "lb", unitCost: 4.20, qty: 25 },
      { name: "Soju (assorted)", unit: "btl", unitCost: 8.50, qty: 18 },
    ],
    status: "sent",
    createdAt: "Apr 14, 2026",
  },
  {
    id: "PO-1041",
    supplier: "Kim's Produce",
    items: [
      { name: "Napa cabbage", unit: "head", unitCost: 2.50, qty: 10 },
      { name: "Scallions", unit: "bunch", unitCost: 1.20, qty: 15 },
    ],
    status: "sent",
    createdAt: "Apr 13, 2026",
  },
];

const DELIVERY_DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const SUPPLIER_TYPES = ["Broadline", "Specialty produce", "Seafood", "Dairy", "Bakery", "Beverage", "Other"];

interface Supplier { name: string; type: string; deliveries: string; cutoff: string; spend: string; }

export default function Suppliers() {
  const [suppliers, setSuppliers] = useState<Supplier[]>(initialSuppliers);
  const [orders, setOrders] = useState<PurchaseOrder[]>(samplePOs);
  const [showCreate, setShowCreate] = useState(false);
  const [selectedSupplier, setSelectedSupplier] = useState(initialSuppliers[0].name);
  const [lineItems, setLineItems] = useState<POLineItem[]>([]);
  const [expandedPO, setExpandedPO] = useState<string | null>(null);

  // Add supplier modal state
  const [showAddSupplier, setShowAddSupplier] = useState(false);
  const [newSupplier, setNewSupplier] = useState({ name: "", type: "Broadline", deliveries: [] as string[], cutoff: "", spend: "" });
  const [addError, setAddError] = useState("");

  // Invoice parsing state
  const [parseState, setParseState] = useState<ParseState>("idle");
  const [expandedChange, setExpandedChange] = useState<number | null>(null);
  const [acceptedChanges, setAcceptedChanges] = useState<Set<number>>(new Set());
  const [dragOver, setDragOver] = useState(false);

  const [invoiceChanges, setInvoiceChanges] = useState<InvoiceChange[]>([]);

  const uploadInvoice = async (file: File) => {
    setParseState("uploading");
    
    // Switch to parsing state halfway through simulation to mimic processing steps
    const timer = setTimeout(() => setParseState("parsing"), 1000);
    
    try {
      const formData = new FormData();
      formData.append("file", file);
      
      const res = await fetch("/api/upload/invoice", {
        method: "POST",
        body: formData,
      });
      
      if (!res.ok) throw new Error("Upload failed");
      
      const data = await res.json();
      setInvoiceChanges(data);
      setParseState("done");
    } catch (err) {
      console.error(err);
      setParseState("idle"); // reset on error
    } finally {
      clearTimeout(timer);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      uploadInvoice(e.dataTransfer.files[0]);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      uploadInvoice(e.target.files[0]);
    }
  };

  const acceptChange = (idx: number) => {
    setAcceptedChanges(prev => new Set([...prev, idx]));
  };

  const acceptAll = () => {
    setAcceptedChanges(new Set(invoiceChanges.map((_, i) => i)));
    setTimeout(() => setParseState("accepted"), 400);
  };

  const resetInvoice = () => {
    setParseState("idle");
    setAcceptedChanges(new Set());
    setExpandedChange(null);
  };

  const toggleDeliveryDay = (day: string) => {
    setNewSupplier(s => ({
      ...s,
      deliveries: s.deliveries.includes(day) ? s.deliveries.filter(d => d !== day) : [...s.deliveries, day]
    }));
  };

  const saveNewSupplier = () => {
    if (!newSupplier.name.trim()) { setAddError("Supplier name is required."); return; }
    if (suppliers.find(s => s.name.toLowerCase() === newSupplier.name.trim().toLowerCase())) { setAddError("A supplier with this name already exists."); return; }
    const sorted = DELIVERY_DAYS.filter(d => newSupplier.deliveries.includes(d));
    setSuppliers(prev => [...prev, {
      name: newSupplier.name.trim(),
      type: newSupplier.type,
      deliveries: sorted.length > 0 ? sorted.join(", ") : "TBD",
      cutoff: newSupplier.cutoff.trim() || "TBD",
      spend: newSupplier.spend.trim() ? `$${newSupplier.spend.trim()}/wk` : "—",
    }]);
    setNewSupplier({ name: "", type: "Broadline", deliveries: [], cutoff: "", spend: "" });
    setAddError("");
    setShowAddSupplier(false);
  };

  const catalog = catalogItems[selectedSupplier] || [];
  const currentSupplierNames = suppliers.map(s => s.name);

  const addLineItem = (item: { name: string; unit: string; unitCost: number }) => {
    if (lineItems.find((l) => l.name === item.name)) return;
    setLineItems([...lineItems, { ...item, qty: 1 }]);
  };

  const updateQty = (index: number, qty: number) => {
    const updated = [...lineItems];
    updated[index].qty = Math.max(1, qty);
    setLineItems(updated);
  };

  const removeLineItem = (index: number) => {
    setLineItems(lineItems.filter((_, i) => i !== index));
  };

  const poTotal = lineItems.reduce((sum, l) => sum + l.unitCost * l.qty, 0);

  const nextPONumber = `PO-${1043 + orders.filter((o) => !samplePOs.includes(o)).length}`;

  const createOrder = (status: "draft" | "sent") => {
    if (lineItems.length === 0) return;
    const newOrder: PurchaseOrder = {
      id: nextPONumber,
      supplier: selectedSupplier,
      items: [...lineItems],
      status,
      createdAt: "Apr 16, 2026",
    };
    setOrders([newOrder, ...orders]);
    setLineItems([]);
    setShowCreate(false);
  };

  return (
    <div className="space-y-6 max-w-7xl">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Suppliers</h1>
        <div className="flex items-center gap-2">
          <button
            onClick={() => { setShowAddSupplier(true); setShowCreate(false); }}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            <Building2 className="h-4 w-4" />
            Add Supplier
          </button>
          <button
            onClick={() => setShowCreate(!showCreate)}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            {showCreate ? <X className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
            {showCreate ? "Cancel" : "New Purchase Order"}
          </button>
        </div>
      </div>

      {/* ── INVOICE UPLOAD & COST CASCADE ── */}
      <div className="bg-card rounded-lg border p-5 space-y-4">
        <div>
          <div className="flex items-center gap-2">
            <Upload className="h-5 w-5 text-primary" />
            <h2 className="font-semibold text-lg">Invoice Parsing & Cost Cascade</h2>
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            Upload a supplier invoice — Pantry detects price changes and updates all affected recipes automatically.
          </p>
        </div>

        {parseState === "idle" && (
          <div
            onDragOver={e => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            className={cn(
              "border-2 border-dashed rounded-xl p-8 flex flex-col items-center justify-center gap-3 transition-colors",
              dragOver ? "border-primary bg-primary/5" : "border-border hover:border-primary/50 hover:bg-muted/30"
            )}
          >
            <label className="w-full h-full flex flex-col items-center justify-center cursor-pointer">
              <Upload className="h-10 w-10 text-muted-foreground" />
              <div className="text-center space-y-1 mt-3">
                <p className="font-medium text-sm">Drop invoice PDF here or click to upload</p>
                <p className="text-xs text-muted-foreground">Supports PDF, CSV, or image files from Sysco, US Foods, Toast, and 50+ suppliers</p>
              </div>
              <input type="file" className="hidden" accept="application/pdf,image/*,.csv" onChange={handleFileSelect} />
            </label>
            <div className="flex flex-wrap gap-1.5 justify-center pt-2">
              {["Sysco", "US Foods", "Kim's Produce", "Pacific Seafood"].map(s => (
                <span key={s} className="text-[10px] px-2 py-0.5 rounded-full bg-muted text-muted-foreground">{s}</span>
              ))}
            </div>
          </div>
        )}

        {(parseState === "uploading" || parseState === "parsing") && (
          <div className="border rounded-xl p-8 flex items-center gap-4">
            <RefreshCw className="h-6 w-6 text-primary animate-spin" />
            <div className="flex-1">
              <p className="font-medium text-sm">
                {parseState === "uploading" ? "Uploading invoice…" : "Parsing line items and detecting price changes…"}
              </p>
              <p className="text-xs text-muted-foreground mt-0.5">
                {parseState === "uploading" ? "Securely transmitting document" : "Comparing against previous Sysco invoice from Apr 7, 2026"}
              </p>
            </div>
          </div>
        )}

        {parseState === "accepted" && (
          <div className="border rounded-xl p-6 flex items-center gap-4 bg-success/5">
            <CheckCircle2 className="h-8 w-8 text-success flex-shrink-0" />
            <div className="flex-1">
              <p className="font-medium text-sm">All changes accepted</p>
              <p className="text-xs text-muted-foreground mt-0.5">
                3 ingredient prices updated · 4 recipe food costs recalculated · 2 menu price alerts triggered
              </p>
            </div>
            <button onClick={resetInvoice} className="text-xs px-3 py-1.5 rounded-md border hover:bg-muted transition-colors font-medium">
              Upload Another Invoice
            </button>
          </div>
        )}

        {parseState === "done" && (
          <div className="space-y-3">
            {/* Summary bar */}
            <div className="flex items-center justify-between p-3 rounded-lg bg-warning/5 border border-warning/20">
              <div className="flex items-center gap-2 text-sm">
                <AlertTriangle className="h-4 w-4 text-warning" />
                <span className="font-medium">3 price changes detected on this Sysco invoice (Apr 14, 2026)</span>
              </div>
              <div className="flex items-center gap-2">
                <button onClick={resetInvoice} className="text-xs px-3 py-1.5 rounded-md border hover:bg-muted transition-colors font-medium">
                  Dismiss
                </button>
                <button onClick={acceptAll} className="text-xs px-3 py-1.5 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors font-medium">
                  Accept All & Update Recipes
                </button>
              </div>
            </div>

            {/* Change rows */}
            {invoiceChanges.map((change, idx) => {
              const isExpanded = expandedChange === idx;
              const isAccepted = acceptedChanges.has(idx);
              return (
                <div key={idx} className="border rounded-lg overflow-hidden">
                  <button
                    onClick={() => setExpandedChange(isExpanded ? null : idx)}
                    className="w-full flex items-center gap-3 p-3 text-sm hover:bg-muted/30 transition-colors text-left"
                  >
                    <span className={cn(
                      "text-[10px] font-bold px-2 py-0.5 rounded-full flex-shrink-0",
                      change.severity === "destructive" ? "bg-destructive/10 text-destructive" : "bg-warning/10 text-warning"
                    )}>
                      +{change.pctChange}%
                    </span>
                    <div className="flex-1 min-w-0">
                      <span className="font-medium">{change.item}</span>
                      <span className="text-muted-foreground ml-2 text-xs">
                        ${change.oldPrice.toFixed(2)}/{change.unit} → ${change.newPrice.toFixed(2)}/{change.unit}
                      </span>
                    </div>
                    <span className="text-xs text-muted-foreground flex items-center gap-1">
                      <Package className="h-3 w-3" />
                      {change.affectedDishes.length} dish{change.affectedDishes.length > 1 ? "es" : ""} affected
                    </span>
                    {isAccepted ? (
                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-success/10 text-success flex items-center gap-1">
                        <CheckCircle2 className="h-3 w-3" /> Accepted
                      </span>
                    ) : (
                      <button
                        onClick={(e) => { e.stopPropagation(); acceptChange(idx); }}
                        className="text-xs px-3 py-1 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors font-medium"
                      >
                        Accept
                      </button>
                    )}
                    <ChevronRight className={cn("h-4 w-4 text-muted-foreground transition-transform", isExpanded && "rotate-90")} />
                  </button>

                  {isExpanded && (
                    <div className="border-t bg-muted/20 p-4 space-y-3">
                      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Affected recipe costs</p>
                      <div className="space-y-2">
                        {change.affectedDishes.map((dish, di) => (
                          <div key={di} className="bg-card rounded-md border p-3 space-y-2">
                            <p className="font-medium text-sm">{dish.name}</p>
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                              <div>
                                <p className="text-muted-foreground mb-0.5">Food cost</p>
                                <p className="font-medium">
                                  <span className="text-muted-foreground line-through">{dish.currentCost}%</span>
                                  <span className={cn("ml-1.5 font-semibold", dish.newCost > 32 ? "text-destructive" : "text-warning")}>
                                    {dish.newCost}%
                                  </span>
                                </p>
                              </div>
                              <div>
                                <p className="text-muted-foreground mb-0.5">Margin</p>
                                <p className="font-medium">
                                  <span className="text-muted-foreground line-through">{dish.currentMargin}%</span>
                                  <span className="ml-1.5 font-semibold">{dish.newMargin}%</span>
                                </p>
                              </div>
                              <div>
                                <p className="text-muted-foreground mb-0.5">Menu price</p>
                                <p className="font-semibold">${dish.currentMenuPrice}</p>
                              </div>
                              {dish.newCost > 30 && (
                                <div className="flex items-end">
                                  <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-warning/10 text-warning">
                                    Price review suggested
                                  </span>
                                </div>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Add Supplier Modal */}
      {showAddSupplier && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={(e) => { if (e.target === e.currentTarget) setShowAddSupplier(false); }}>
          <div className="bg-card rounded-xl border shadow-2xl w-full max-w-lg mx-4 p-6 space-y-5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Building2 className="h-5 w-5 text-primary" />
                <h2 className="font-semibold text-lg">Add New Supplier</h2>
              </div>
              <button onClick={() => { setShowAddSupplier(false); setAddError(""); }} className="text-muted-foreground hover:text-foreground transition-colors"><X className="h-5 w-5" /></button>
            </div>

            <div className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground">Supplier name <span className="text-destructive">*</span></label>
                <input value={newSupplier.name} onChange={e => { setNewSupplier(s => ({ ...s, name: e.target.value })); setAddError(""); }} placeholder="e.g. Green City Farms" className="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground">Supplier type</label>
                <select value={newSupplier.type} onChange={e => setNewSupplier(s => ({ ...s, type: e.target.value }))} className="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring">
                  {SUPPLIER_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground">Delivery days</label>
                <div className="flex flex-wrap gap-2">
                  {DELIVERY_DAYS.map(day => (
                    <button key={day} onClick={() => toggleDeliveryDay(day)} className={cn("text-xs px-3 py-1.5 rounded-full border transition-colors", newSupplier.deliveries.includes(day) ? "bg-primary text-primary-foreground border-primary" : "hover:border-primary/50")}>
                      {day}
                    </button>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-muted-foreground">Order cutoff</label>
                  <input value={newSupplier.cutoff} onChange={e => setNewSupplier(s => ({ ...s, cutoff: e.target.value }))} placeholder="e.g. Day before, 2pm" className="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-muted-foreground">Avg weekly spend ($)</label>
                  <input value={newSupplier.spend} onChange={e => setNewSupplier(s => ({ ...s, spend: e.target.value }))} placeholder="e.g. 1200" className="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
                </div>
              </div>
            </div>

            {addError && <p className="text-xs text-destructive font-medium">{addError}</p>}

            <div className="flex justify-end gap-2 pt-2 border-t">
              <button onClick={() => { setShowAddSupplier(false); setAddError(""); }} className="px-4 py-2 text-sm font-medium rounded-lg border hover:bg-muted transition-colors">Cancel</button>
              <button onClick={saveNewSupplier} className="px-4 py-2 text-sm font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors">Add Supplier</button>
            </div>
          </div>
        </div>
      )}

      {/* Create purchase order Panel */}
      {showCreate && (
        <div className="bg-card rounded-lg border p-5 space-y-5">
          <div className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-primary" />
            <h2 className="font-semibold text-lg">Create Purchase Order — {nextPONumber}</h2>
          </div>

          {/* Supplier select */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">Supplier</label>
            <select
              value={selectedSupplier}
              onChange={(e) => { setSelectedSupplier(e.target.value); setLineItems([]); }}
              className="w-full max-w-xs rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            >
              {currentSupplierNames.map((s) => (
                <option key={s} value={s}>{s}{catalogItems[s] ? ` — ${suppliers.find(x => x.name === s)?.type}` : ""}</option>
              ))}
            </select>
          </div>

          {/* Add items from catalog */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">Add items from catalog</label>
            <div className="flex flex-wrap gap-2">
              {catalog.map((item) => {
                const added = lineItems.find((l) => l.name === item.name);
                return (
                  <button
                    key={item.name}
                    onClick={() => addLineItem(item)}
                    disabled={!!added}
                    className={cn(
                      "text-xs px-3 py-1.5 rounded-full border transition-colors",
                      added
                        ? "bg-muted text-muted-foreground cursor-default"
                        : "hover:bg-primary/10 hover:border-primary/30 cursor-pointer"
                    )}
                  >
                    {item.name} · ${item.unitCost.toFixed(2)}/{item.unit}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Line items table */}
          {lineItems.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-muted/50">
                    <th className="text-left p-3 font-medium">Item</th>
                    <th className="text-left p-3 font-medium">Unit Cost</th>
                    <th className="text-left p-3 font-medium w-28">Qty</th>
                    <th className="text-right p-3 font-medium">Total</th>
                    <th className="p-3 w-10"></th>
                  </tr>
                </thead>
                <tbody>
                  {lineItems.map((item, i) => (
                    <tr key={item.name} className="border-b last:border-0">
                      <td className="p-3 font-medium">{item.name}</td>
                      <td className="p-3 text-muted-foreground">${item.unitCost.toFixed(2)}/{item.unit}</td>
                      <td className="p-3">
                        <input
                          type="number"
                          min={1}
                          value={item.qty}
                          onChange={(e) => updateQty(i, parseInt(e.target.value) || 1)}
                          className="w-20 rounded-md border bg-background px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                        />
                      </td>
                      <td className="p-3 text-right font-semibold">${(item.unitCost * item.qty).toFixed(2)}</td>
                      <td className="p-3">
                        <button onClick={() => removeLineItem(i)} className="text-muted-foreground hover:text-destructive transition-colors">
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr className="border-t">
                    <td colSpan={3} className="p-3 text-right font-medium">Estimated Total</td>
                    <td className="p-3 text-right font-bold text-lg">${poTotal.toFixed(2)}</td>
                    <td></td>
                  </tr>
                </tfoot>
              </table>
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center gap-3 pt-2">
            <button
              onClick={() => createOrder("sent")}
              disabled={lineItems.length === 0}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <Send className="h-4 w-4" />
              Send to {selectedSupplier}
            </button>
            <button
              onClick={() => createOrder("draft")}
              disabled={lineItems.length === 0}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg border hover:bg-muted transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Save as Draft
            </button>
          </div>
        </div>
      )}

      {/* Recent purchase orders */}
      {orders.length > 0 && (
        <div className="bg-card rounded-lg border p-5">
          <h2 className="font-semibold mb-4">Recent Purchase Orders</h2>
          <div className="space-y-2">
            {orders.map((po) => (
              <div key={po.id} className="border rounded-lg">
                <button
                  onClick={() => setExpandedPO(expandedPO === po.id ? null : po.id)}
                  className="w-full flex items-center justify-between p-3 text-sm hover:bg-muted/30 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <span className="font-semibold">{po.id}</span>
                    <span className="text-muted-foreground">{po.supplier}</span>
                    <span className="text-muted-foreground">·</span>
                    <span className="text-muted-foreground">{po.items.length} items</span>
                    <span className="text-muted-foreground">·</span>
                    <span className="font-medium">${po.items.reduce((s, l) => s + l.unitCost * l.qty, 0).toFixed(2)}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-muted-foreground">{po.createdAt}</span>
                    <span className={cn(
                      "text-[10px] font-semibold px-2 py-0.5 rounded-full",
                      po.status === "sent" ? "bg-success/10 text-success" : "bg-warning/10 text-warning"
                    )}>
                      {po.status === "sent" ? "Sent" : "Draft"}
                    </span>
                    {expandedPO === po.id ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
                  </div>
                </button>
                {expandedPO === po.id && (
                  <div className="border-t px-3 pb-3">
                    <table className="w-full text-sm mt-2">
                      <thead>
                        <tr className="text-muted-foreground">
                          <th className="text-left p-2 font-medium text-xs">Item</th>
                          <th className="text-left p-2 font-medium text-xs">Unit Cost</th>
                          <th className="text-left p-2 font-medium text-xs">Qty</th>
                          <th className="text-right p-2 font-medium text-xs">Total</th>
                        </tr>
                      </thead>
                      <tbody>
                        {po.items.map((item) => (
                          <tr key={item.name} className="border-t">
                            <td className="p-2">{item.name}</td>
                            <td className="p-2 text-muted-foreground">${item.unitCost.toFixed(2)}/{item.unit}</td>
                            <td className="p-2">{item.qty} {item.unit}</td>
                            <td className="p-2 text-right font-medium">${(item.unitCost * item.qty).toFixed(2)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Supplier Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {suppliers.map((s, i) => (
          <div key={i} className="bg-card rounded-lg border p-5 space-y-2">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold">{s.name}</h3>
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-success/10 text-success">Active</span>
            </div>
            <p className="text-xs text-muted-foreground">{s.type}</p>
            <div className="text-xs space-y-1 pt-1">
              <p><span className="text-muted-foreground">Deliveries:</span> {s.deliveries}</p>
              <p><span className="text-muted-foreground">Order cutoff:</span> {s.cutoff}</p>
              <p><span className="text-muted-foreground">Avg weekly spend:</span> <span className="font-semibold">{s.spend}</span></p>
            </div>
          </div>
        ))}
      </div>

      {/* Spend Table */}
      <div className="bg-card rounded-lg border p-5">
        <h2 className="font-semibold mb-4">Spend by Supplier (Last 4 Weeks)</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/50">
                <th className="text-left p-3 font-medium">Supplier</th>
                <th className="text-left p-3 font-medium">Wk 1</th>
                <th className="text-left p-3 font-medium">Wk 2</th>
                <th className="text-left p-3 font-medium">Wk 3</th>
                <th className="text-left p-3 font-medium">Wk 4</th>
                <th className="text-left p-3 font-medium">Total</th>
                <th className="text-left p-3 font-medium">Trend</th>
              </tr>
            </thead>
            <tbody>
              {spendData.map((r, i) => (
                <tr key={i} className="border-b last:border-0">
                  <td className="p-3 font-medium">{r.name}</td>
                  {r.weeks.map((w, j) => <td key={j} className="p-3">{w}</td>)}
                  <td className="p-3 font-semibold">{r.total}</td>
                  <td className={cn("p-3 font-medium", r.trendGood ? "text-success" : "text-destructive")}>{r.trend}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Price Watch */}
      <div className="bg-card rounded-lg border p-5">
        <h2 className="font-semibold mb-1">Price Watch</h2>
        <p className="text-xs text-muted-foreground mb-4">AI monitors supplier pricing changes and alerts you to significant increases.</p>
        <div className="space-y-3">
          {priceWatch.map((p, i) => (
            <div key={i} className="flex items-center gap-3 text-sm">
              <span className={cn("text-[10px] font-bold px-2 py-0.5 rounded-full", p.severity === "destructive" ? "bg-destructive/10 text-destructive" : "bg-warning/10 text-warning")}>{p.change}</span>
              <span className="font-medium">{p.item}</span>
              <span className="text-muted-foreground">via {p.supplier}</span>
              <span className="text-muted-foreground">— {p.from} → <span className="font-medium text-foreground">{p.to}</span></span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
