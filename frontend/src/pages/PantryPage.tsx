import { useState, useRef } from "react";
import { Plus, Trash2, Camera, Receipt, ShoppingBasket } from "lucide-react";
import { usePantry } from "../hooks/usePantry";
import { addPantryItem, removePantryItem } from "../api/pantry";
import { scanPantry, scanReceipt } from "../api/ai";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";

function PantryListSkeleton() {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3" aria-busy="true" aria-label="Loading pantry">
      {Array.from({ length: 6 }, (_, i) => (
        <div key={i} className="h-[60px] rounded-2xl bg-stone-200 animate-pulse" />
      ))}
    </div>
  );
}

export function PantryPage() {
  const { items, loading, error, refresh } = usePantry();
  const [showForm, setShowForm] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [scanMsg, setScanMsg] = useState<string | null>(null);
  const [scanningReceipt, setScanningReceipt] = useState(false);
  const [receiptMsg, setReceiptMsg] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const receiptRef = useRef<HTMLInputElement>(null);

  async function handleDelete(id: number) {
    await removePantryItem(id);
    refresh();
  }

  async function handleScan(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setScanning(true);
    setScanMsg(null);
    try {
      const result = await scanPantry(file);
      const count = result.detected_items?.length ?? 0;
      setScanMsg(`Detected ${count} item${count !== 1 ? "s" : ""} and added them to your pantry.`);
      refresh();
    } catch (err) {
      setScanMsg(err instanceof Error ? err.message : "Scan failed");
    } finally {
      setScanning(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function handleReceiptScan(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setScanningReceipt(true);
    setReceiptMsg(null);
    try {
      const result = await scanReceipt(file);
      const count = result.detected_items?.length ?? 0;
      setReceiptMsg(`Found ${count} item${count !== 1 ? "s" : ""} on your receipt and added them to your pantry.`);
      refresh();
    } catch (err) {
      setReceiptMsg(err instanceof Error ? err.message : "Receipt scan failed");
    } finally {
      setScanningReceipt(false);
      if (receiptRef.current) receiptRef.current.value = "";
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="font-display text-2xl font-semibold text-stone-800">Pantry</h1>
        <div className="flex gap-2">
          <Button
            variant="secondary"
            icon={scanningReceipt ? undefined : <Receipt size={15} />}
            loading={scanningReceipt}
            onClick={() => receiptRef.current?.click()}
          >
            Scan receipt
          </Button>
          <input ref={receiptRef} type="file" accept="image/*" capture="environment" className="hidden" onChange={handleReceiptScan} />
          <Button
            variant="secondary"
            icon={scanning ? undefined : <Camera size={15} />}
            loading={scanning}
            onClick={() => fileRef.current?.click()}
          >
            Scan fridge
          </Button>
          <input ref={fileRef} type="file" accept="image/*" capture="environment" className="hidden" onChange={handleScan} />
          <Button icon={<Plus size={16} />} onClick={() => setShowForm(!showForm)}>
            Add item
          </Button>
        </div>
      </div>

      {receiptMsg && (
        <div className="p-3 bg-sage-50 border border-sage-200 text-sage-700 rounded-xl text-sm">
          {receiptMsg}
        </div>
      )}

      {scanMsg && (
        <div className="p-3 bg-sage-50 border border-sage-200 text-sage-700 rounded-xl text-sm">
          {scanMsg}
        </div>
      )}

      {showForm && <AddPantryForm onAdded={() => { setShowForm(false); refresh(); }} />}

      {loading && <PantryListSkeleton />}

      {error && !loading && (
        <section role="alert" className="rounded-xl border border-clay-400/30 bg-clay-400/10 p-4">
          <p className="text-sm font-medium text-clay-600">Could not load your pantry.</p>
          <p className="mt-1 text-sm text-clay-500">{error}</p>
          <button onClick={refresh} className="mt-2 text-sm text-clay-600 underline underline-offset-2">
            Try again
          </button>
        </section>
      )}

      {!loading && !error && items.length === 0 && (
        <div className="text-center py-16 text-stone-400">
          <ShoppingBasket size={40} className="mx-auto mb-3 opacity-40" />
          <p className="font-medium">Your pantry is empty</p>
          <p className="text-sm mt-1">Add items manually or scan your fridge</p>
        </div>
      )}

      {!loading && !error && <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {items.map((item) => (
          <Card key={item.id} className="flex items-center justify-between p-3">
            <div>
              <p className="font-medium text-stone-800 text-sm">{item.ingredient_name}</p>
              <p className="text-xs font-mono text-stone-400 mt-0.5">
                {item.quantity} {item.unit}
              </p>
            </div>
            <button
              onClick={() => handleDelete(item.id)}
              className="p-1.5 text-stone-300 hover:text-clay-500 transition-colors"
            >
              <Trash2 size={14} />
            </button>
          </Card>
        ))}
      </div>}
    </div>
  );
}

type PantryFormStatus = "idle" | "submitting" | "error";
const EMPTY_PANTRY = { name: "", quantity: "", unit: "" };

function AddPantryForm({ onAdded }: { onAdded: () => void }) {
  const [fields, setFields] = useState(EMPTY_PANTRY);
  const [status, setStatus] = useState<PantryFormStatus>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const { name, value } = e.target;
    setFields(prev => ({ ...prev, [name]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (status === "submitting") return;
    if (!fields.name.trim()) {
      setStatus("error");
      setErrorMessage("Ingredient name is required.");
      return;
    }
    setStatus("submitting");
    setErrorMessage(null);
    try {
      await addPantryItem({ ingredient_name: fields.name, quantity: fields.quantity || "1", unit: fields.unit || "unit" });
      setFields(EMPTY_PANTRY);
      setStatus("idle");
      onAdded();
    } catch (err) {
      setStatus("error");
      setErrorMessage(err instanceof Error ? err.message : "Failed to add item. Please try again.");
    }
  }

  const isSubmitting = status === "submitting";

  return (
    <Card className="p-4">
      <h2 className="font-medium text-stone-700 mb-4">Add Pantry Item</h2>
      {status === "error" && errorMessage && (
        <p role="alert" id="pantry-form-error" className="text-sm text-clay-500 bg-clay-400/10 border border-clay-400/30 rounded-xl px-3 py-2 mb-3">
          {errorMessage}
        </p>
      )}
      <form onSubmit={handleSubmit} className="flex flex-wrap gap-3">
        <div className="flex-1 min-w-40">
          <Input id="pname" name="name" label="Ingredient" value={fields.name} onChange={handleChange} placeholder="Olive oil" disabled={isSubmitting} aria-describedby={status === "error" ? "pantry-form-error" : undefined} required />
        </div>
        <div className="w-24">
          <Input id="pqty" name="quantity" label="Qty" value={fields.quantity} onChange={handleChange} placeholder="2" disabled={isSubmitting} />
        </div>
        <div className="w-28">
          <Input id="punit" name="unit" label="Unit" value={fields.unit} onChange={handleChange} placeholder="cups" disabled={isSubmitting} />
        </div>
        <div className="flex items-end">
          <Button type="submit" loading={isSubmitting}>{isSubmitting ? "Adding…" : "Add"}</Button>
        </div>
      </form>
    </Card>
  );
}
