import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { createPurchase } from "../../api/purchases";
import { createSupplier, listSuppliers } from "../../api/suppliers";
import { searchProducts } from "../../api/products";
import type { Product, PurchaseCartLine } from "../../types";

interface MismatchInfo {
  detail: string;
}

export function NewPurchase() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [supplierId, setSupplierId] = useState("");
  const [showNewSupplierForm, setShowNewSupplierForm] = useState(false);
  const [newSupplierName, setNewSupplierName] = useState("");
  const [newSupplierPhone, setNewSupplierPhone] = useState("");

  const [invoiceNumber, setInvoiceNumber] = useState("");
  const [invoiceDate, setInvoiceDate] = useState("");
  const [invoiceTotal, setInvoiceTotal] = useState("");
  const [notes, setNotes] = useState("");

  const [lines, setLines] = useState<PurchaseCartLine[]>([]);

  const [searchValue, setSearchValue] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const searchInputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [error, setError] = useState<string | null>(null);
  const [mismatch, setMismatch] = useState<MismatchInfo | null>(null);

  const { data: suppliers } = useQuery({ queryKey: ["suppliers"], queryFn: listSuppliers });

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => setDebouncedSearch(searchValue), 200);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [searchValue]);

  const { data: searchResults = [] } = useQuery({
    queryKey: ["product-search-purchase", debouncedSearch],
    queryFn: () => searchProducts(debouncedSearch),
    enabled: debouncedSearch.trim().length > 0,
  });

  const createSupplierMutation = useMutation({
    mutationFn: () => createSupplier({ name: newSupplierName, phone: newSupplierPhone || null }),
    onSuccess: (supplier) => {
      queryClient.invalidateQueries({ queryKey: ["suppliers"] });
      setSupplierId(supplier.id);
      setShowNewSupplierForm(false);
      setNewSupplierName("");
      setNewSupplierPhone("");
    },
  });

  const computedTotal = lines.reduce(
    (sum, l) => sum + parseFloat(l.quantity || "0") * parseFloat(l.unit_cost || "0"),
    0
  );

  function addProduct(product: Product) {
    if (lines.some((l) => l.product.id === product.id)) {
      setError(`'${product.name}' is already in this purchase. Adjust the quantity on that line instead.`);
      return;
    }
    setError(null);

    // Approved design: pre-fill supplier from the first product's
    // preferred_supplier_id if none is selected yet — still changeable.
    if (!supplierId && product.preferred_supplier_id) {
      setSupplierId(product.preferred_supplier_id);
    }

    setLines((prev) => [
      ...prev,
      {
        product,
        quantity: "1",
        unit_cost: product.last_purchase_cost ?? "",
      },
    ]);
    setSearchValue("");
    setDebouncedSearch("");
  }

  function updateLine(productId: string, field: "quantity" | "unit_cost", value: string) {
    setLines((prev) => prev.map((l) => (l.product.id === productId ? { ...l, [field]: value } : l)));
  }

  function removeLine(productId: string) {
    setLines((prev) => prev.filter((l) => l.product.id !== productId));
  }

  const purchaseMutation = useMutation({
    mutationFn: (mismatchAcknowledged: boolean) =>
      createPurchase({
        supplier_id: supplierId,
        items: lines.map((l) => ({
          product_id: l.product.id,
          quantity: l.quantity,
          unit_cost: l.unit_cost,
        })),
        invoice_number: invoiceNumber || null,
        invoice_date: invoiceDate || null,
        invoice_total: invoiceTotal || null,
        notes: notes || null,
        mismatch_acknowledged: mismatchAcknowledged,
      }),
    onSuccess: (purchase) => {
      navigate(`/purchases?highlight=${purchase.id}`);
    },
    onError: (err: unknown) => {
      const status = (err as { response?: { status?: number } })?.response?.status;
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Unable to save purchase.";
      if (status === 409) {
        setMismatch({ detail });
      } else {
        setError(detail);
        setMismatch(null);
      }
    },
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setMismatch(null);

    if (!supplierId) {
      setError("Select or add a supplier first.");
      return;
    }
    if (lines.length === 0) {
      setError("Add at least one product.");
      return;
    }
    purchaseMutation.mutate(false);
  }

  function handleAcknowledgeMismatch() {
    purchaseMutation.mutate(true);
  }

  return (
    <div className="p-8 max-w-4xl">
      <h2 className="text-lg font-semibold mb-4">New Purchase — Stock Receiving</h2>

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Supplier */}
        <div className="bg-white border border-gray-200 rounded-lg p-4 space-y-3">
          <div className="flex items-end gap-3">
            <div className="flex-1">
              <label className="block text-xs font-medium text-gray-600 mb-1">Supplier</label>
              <select
                value={supplierId}
                onChange={(e) => setSupplierId(e.target.value)}
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
              >
                <option value="">Select a supplier…</option>
                {suppliers?.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </div>
            <button
              type="button"
              onClick={() => setShowNewSupplierForm((v) => !v)}
              className="text-sm text-brand-600 hover:underline whitespace-nowrap pb-2"
            >
              {showNewSupplierForm ? "Cancel" : "+ New Supplier"}
            </button>
          </div>

          {showNewSupplierForm && (
            <div className="flex items-end gap-2 pt-2 border-t border-gray-100">
              <div className="flex-1">
                <label className="block text-xs font-medium text-gray-600 mb-1">Name</label>
                <input
                  value={newSupplierName}
                  onChange={(e) => setNewSupplierName(e.target.value)}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                />
              </div>
              <div className="flex-1">
                <label className="block text-xs font-medium text-gray-600 mb-1">Phone</label>
                <input
                  value={newSupplierPhone}
                  onChange={(e) => setNewSupplierPhone(e.target.value)}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                />
              </div>
              <button
                type="button"
                disabled={!newSupplierName || createSupplierMutation.isPending}
                onClick={() => createSupplierMutation.mutate()}
                className="bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white text-sm font-medium rounded-md px-4 py-2"
              >
                Save
              </button>
            </div>
          )}
        </div>

        {/* Invoice details */}
        <div className="bg-white border border-gray-200 rounded-lg p-4 grid grid-cols-3 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Invoice Number</label>
            <input
              value={invoiceNumber}
              onChange={(e) => setInvoiceNumber(e.target.value)}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Invoice Date</label>
            <input
              type="date"
              value={invoiceDate}
              onChange={(e) => setInvoiceDate(e.target.value)}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Invoice Total (optional)</label>
            <input
              type="number"
              step="0.01"
              min="0"
              value={invoiceTotal}
              onChange={(e) => setInvoiceTotal(e.target.value)}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
              placeholder="If shown on the supplier's invoice"
            />
          </div>
        </div>

        {/* Product entry */}
        <div className="bg-white border border-gray-200 rounded-lg p-4 space-y-3">
          <div className="relative">
            <input
              ref={searchInputRef}
              type="text"
              value={searchValue}
              onChange={(e) => setSearchValue(e.target.value)}
              placeholder="Scan barcode / enter code / search product…"
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
              autoComplete="off"
            />
            {searchResults.length > 0 && searchValue.trim().length > 0 && (
              <div className="absolute z-10 mt-1 w-full bg-white border border-gray-200 rounded-md shadow-lg max-h-60 overflow-auto">
                {searchResults.map((product) => (
                  <button
                    key={product.id}
                    type="button"
                    onClick={() => addProduct(product)}
                    className="w-full text-left px-3 py-2 text-sm border-b border-gray-100 last:border-b-0 hover:bg-gray-50 flex justify-between"
                  >
                    <span>{product.name}</span>
                    <span className="text-gray-400 text-xs">
                      {product.internal_code ?? product.barcode ?? "—"}
                      {product.last_purchase_cost && ` · last cost Rs.${product.last_purchase_cost}`}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {lines.length === 0 ? (
            <div className="text-sm text-gray-400 text-center py-6 border border-dashed border-gray-200 rounded-md">
              Search and add products received in this delivery.
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-600 text-left">
                <tr>
                  <th className="px-3 py-2">Product</th>
                  <th className="px-3 py-2 w-28">Qty</th>
                  <th className="px-3 py-2 w-32">Unit Cost</th>
                  <th className="px-3 py-2 text-right">Total</th>
                  <th className="px-2 py-2 w-8"></th>
                </tr>
              </thead>
              <tbody>
                {lines.map((line) => {
                  const lineTotal = (
                    parseFloat(line.quantity || "0") * parseFloat(line.unit_cost || "0")
                  ).toFixed(2);
                  return (
                    <tr key={line.product.id} className="border-t border-gray-100">
                      <td className="px-3 py-2 font-medium">{line.product.name}</td>
                      <td className="px-3 py-2">
                        <input
                          type="number"
                          min="0"
                          step={line.product.unit === "pcs" ? "1" : "0.01"}
                          value={line.quantity}
                          onChange={(e) => updateLine(line.product.id, "quantity", e.target.value)}
                          className="w-24 border border-gray-300 rounded-md px-2 py-1 text-sm"
                        />
                      </td>
                      <td className="px-3 py-2">
                        <input
                          type="number"
                          min="0"
                          step="0.01"
                          value={line.unit_cost}
                          onChange={(e) => updateLine(line.product.id, "unit_cost", e.target.value)}
                          className="w-28 border border-gray-300 rounded-md px-2 py-1 text-sm"
                        />
                      </td>
                      <td className="px-3 py-2 text-right font-medium">Rs. {lineTotal}</td>
                      <td className="px-2 py-2 text-center">
                        <button
                          type="button"
                          onClick={() => removeLine(line.product.id)}
                          className="text-gray-400 hover:text-danger"
                        >
                          ✕
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}

          <div className="flex justify-between text-lg font-bold border-t border-gray-200 pt-3">
            <span>TOTAL</span>
            <span>Rs. {computedTotal.toFixed(2)}</span>
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Notes (optional)</label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={2}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
          />
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-danger text-sm rounded-md p-3">{error}</div>
        )}

        {mismatch && (
          <div className="bg-amber-50 border border-amber-300 rounded-md p-4 text-sm space-y-3">
            <div className="font-medium text-amber-800">{mismatch.detail}</div>
            <button
              type="button"
              onClick={handleAcknowledgeMismatch}
              disabled={purchaseMutation.isPending}
              className="bg-amber-600 hover:bg-amber-700 disabled:opacity-60 text-white text-sm font-medium rounded-md px-4 py-2"
            >
              Acknowledge Discrepancy &amp; Save Anyway
            </button>
          </div>
        )}

        <button
          type="submit"
          disabled={purchaseMutation.isPending}
          className="w-full bg-success hover:opacity-90 disabled:opacity-40 text-white font-semibold rounded-md py-3"
        >
          {purchaseMutation.isPending ? "Saving…" : "SAVE PURCHASE"}
        </button>
      </form>
    </div>
  );
}
