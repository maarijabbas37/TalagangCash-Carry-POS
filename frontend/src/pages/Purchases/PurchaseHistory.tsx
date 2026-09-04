import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { listPurchases, recordPurchasePayment } from "../../api/purchases";
import { listSuppliers } from "../../api/suppliers";
import { useAuth } from "../../hooks/useAuth";
import type { PurchaseOut } from "../../types";

export function PurchaseHistory() {
  const { user } = useAuth();
  const queryClient = useQueryClient();

  const [selectedPurchase, setSelectedPurchase] = useState<PurchaseOut | null>(null);
  const [paymentAmount, setPaymentAmount] = useState("");
  const [paymentNotes, setPaymentNotes] = useState("");
  const [paymentError, setPaymentError] = useState<string | null>(null);

  const { data: purchases, isLoading } = useQuery({
    queryKey: ["purchases"],
    queryFn: () => listPurchases(),
  });
  const { data: suppliers } = useQuery({ queryKey: ["suppliers"], queryFn: listSuppliers });

  function supplierName(supplierId: string): string {
    return suppliers?.find((s) => s.id === supplierId)?.name ?? "—";
  }

  const paymentMutation = useMutation({
    mutationFn: () => {
      if (!selectedPurchase) throw new Error("No purchase selected.");
      return recordPurchasePayment(selectedPurchase.id, paymentAmount, paymentNotes || null);
    },
    onSuccess: (updatedPurchase) => {
      setSelectedPurchase(updatedPurchase);
      queryClient.invalidateQueries({ queryKey: ["purchases"] });
      setPaymentAmount("");
      setPaymentNotes("");
      setPaymentError(null);
    },
    onError: (err: unknown) => {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Unable to record payment.";
      setPaymentError(detail);
    },
  });

  function handleRecordPayment(e: React.FormEvent) {
    e.preventDefault();
    setPaymentError(null);
    paymentMutation.mutate();
  }

  // --- Detail view ---
  if (selectedPurchase) {
    const p = selectedPurchase;
    const hasMismatch = p.invoice_total !== null && p.invoice_total !== p.computed_total;
    const outstandingAmount = parseFloat(p.outstanding);

    return (
      <div className="p-8 max-w-3xl">
        <button
          onClick={() => setSelectedPurchase(null)}
          className="text-sm text-brand-600 hover:underline mb-4"
        >
          ← Back to Purchase History
        </button>

        <div className="bg-white border border-gray-200 rounded-lg p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-gray-100 pb-3">
            <div>
              <h2 className="text-lg font-semibold">{supplierName(p.supplier_id)}</h2>
              <p className="text-sm text-gray-500">
                {p.invoice_number ? `Invoice #${p.invoice_number}` : "No invoice number"}
                {p.invoice_date && ` · ${p.invoice_date}`}
              </p>
            </div>
            <div className="text-xs text-gray-400">
              {new Date(p.created_at).toLocaleString()}
            </div>
          </div>

          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-600 text-left">
              <tr>
                <th className="px-3 py-2">Product</th>
                <th className="px-3 py-2 text-right">Qty</th>
                <th className="px-3 py-2 text-right">Unit Cost</th>
                <th className="px-3 py-2 text-right">Total</th>
              </tr>
            </thead>
            <tbody>
              {p.items.map((item) => (
                <tr key={item.id} className="border-t border-gray-100">
                  <td className="px-3 py-2">{item.product_name}</td>
                  <td className="px-3 py-2 text-right">{item.quantity}</td>
                  <td className="px-3 py-2 text-right">Rs. {item.unit_cost}</td>
                  <td className="px-3 py-2 text-right font-medium">Rs. {item.line_total}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="space-y-1 text-sm border-t border-gray-100 pt-3">
            <div className="flex justify-between">
              <span className="text-gray-500">Computed Total</span>
              <span className="font-medium">Rs. {p.computed_total}</span>
            </div>
            {p.invoice_total !== null && (
              <div className="flex justify-between">
                <span className="text-gray-500">Invoice Total</span>
                <span className="font-medium">Rs. {p.invoice_total}</span>
              </div>
            )}
            {hasMismatch && (
              <div className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-md px-3 py-2 mt-1">
                This purchase had a discrepancy between the computed total and the supplier's
                invoice total, and was saved with that discrepancy acknowledged.
              </div>
            )}
            {p.notes && <div className="text-gray-500 pt-1">Notes: {p.notes}</div>}
          </div>

          <div className="border-t border-gray-100 pt-3 space-y-1 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-500">Amount Paid</span>
              <span className="font-medium">Rs. {p.amount_paid}</span>
            </div>
            <div className="flex justify-between text-base font-bold">
              <span>Outstanding</span>
              <span className={outstandingAmount > 0 ? "text-danger" : "text-success"}>
                Rs. {p.outstanding}
              </span>
            </div>
          </div>

          {p.payments.length > 0 && (
            <div className="border-t border-gray-100 pt-3">
              <h3 className="text-xs font-medium text-gray-500 mb-2">Payment History</h3>
              <div className="space-y-1 text-sm">
                {p.payments.map((payment) => (
                  <div key={payment.id} className="flex justify-between text-gray-600">
                    <span>{new Date(payment.paid_at).toLocaleString()}</span>
                    <span className="font-medium">Rs. {payment.amount}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Owner-only: record a supplier cash payment (approved decision 1) */}
          {user?.role === "OWNER" && outstandingAmount > 0 && (
            <form onSubmit={handleRecordPayment} className="border-t border-gray-100 pt-4 space-y-2">
              <h3 className="text-xs font-medium text-gray-500">Record Supplier Payment</h3>
              <div className="flex gap-2">
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  value={paymentAmount}
                  onChange={(e) => setPaymentAmount(e.target.value)}
                  placeholder="Amount"
                  required
                  className="flex-1 border border-gray-300 rounded-md px-3 py-2 text-sm"
                />
                <input
                  type="text"
                  value={paymentNotes}
                  onChange={(e) => setPaymentNotes(e.target.value)}
                  placeholder="Notes (optional)"
                  className="flex-1 border border-gray-300 rounded-md px-3 py-2 text-sm"
                />
                <button
                  type="submit"
                  disabled={paymentMutation.isPending}
                  className="bg-brand-600 hover:bg-brand-700 disabled:opacity-60 text-white text-sm font-medium rounded-md px-4 py-2 whitespace-nowrap"
                >
                  {paymentMutation.isPending ? "Saving…" : "Record Payment"}
                </button>
              </div>
              {paymentError && <div className="text-sm text-danger">{paymentError}</div>}
            </form>
          )}

          {user?.role !== "OWNER" && outstandingAmount > 0 && (
            <p className="text-xs text-gray-400 border-t border-gray-100 pt-3">
              Only the owner can record supplier payments.
            </p>
          )}
        </div>
      </div>
    );
  }

  // --- List view ---
  return (
    <div className="p-8 max-w-4xl">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">Purchases</h2>
        <Link
          to="/purchases/new"
          className="bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium rounded-md px-4 py-2"
        >
          + New Purchase
        </Link>
      </div>

      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-600 text-left">
            <tr>
              <th className="px-4 py-2">Date</th>
              <th className="px-4 py-2">Supplier</th>
              <th className="px-4 py-2">Invoice #</th>
              <th className="px-4 py-2 text-right">Total</th>
              <th className="px-4 py-2 text-right">Outstanding</th>
              <th className="px-4 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-gray-400">
                  Loading…
                </td>
              </tr>
            )}
            {!isLoading && purchases?.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-gray-400">
                  No purchases recorded yet.
                </td>
              </tr>
            )}
            {purchases?.map((p) => (
              <tr key={p.id} className="border-t border-gray-100">
                <td className="px-4 py-2 text-gray-500">{new Date(p.created_at).toLocaleDateString()}</td>
                <td className="px-4 py-2">{supplierName(p.supplier_id)}</td>
                <td className="px-4 py-2 text-gray-500">{p.invoice_number ?? "—"}</td>
                <td className="px-4 py-2 text-right font-medium">Rs. {p.computed_total}</td>
                <td className="px-4 py-2 text-right">
                  <span className={parseFloat(p.outstanding) > 0 ? "text-danger" : "text-success"}>
                    Rs. {p.outstanding}
                  </span>
                </td>
                <td className="px-4 py-2 text-right">
                  <button
                    onClick={() => setSelectedPurchase(p)}
                    className="text-brand-600 hover:underline text-xs font-medium"
                  >
                    View
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
