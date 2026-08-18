import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useAuth } from "../../hooks/useAuth";
import { usePosCart } from "../../hooks/usePosCart";
import { fetchSettings } from "../../api/settings";
import { getProduct } from "../../api/products";
import { createSale } from "../../api/sales";
import { ProductSearch } from "../../components/pos/ProductSearch";
import { Cart } from "../../components/pos/Cart";
import { PaymentPanel } from "../../components/pos/PaymentPanel";
import { Receipt } from "../../components/pos/Receipt";
import { ConfirmClearBillModal } from "../../components/pos/ConfirmClearBillModal";
import type { PaymentMethod, Product, SaleOut } from "../../types";

interface PriceMismatch {
  productId: string;
  productName: string;
  oldPrice: string;
  newPrice: string;
}

export function POS() {
  const { user } = useAuth();
  const cart = usePosCart();

  const searchInputRef = useRef<HTMLInputElement>(null);
  const discountInputRef = useRef<HTMLInputElement>(null);
  const cashAmountRef = useRef<HTMLInputElement>(null);

  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod | null>(null);
  const [amountReceived, setAmountReceived] = useState("");
  const [qrConfirmed, setQrConfirmed] = useState(false);
  const [paymentReference, setPaymentReference] = useState("");

  const [showClearConfirm, setShowClearConfirm] = useState(false);
  const [priceMismatches, setPriceMismatches] = useState<PriceMismatch[]>([]);
  const [checkoutError, setCheckoutError] = useState<string | null>(null);
  const [completedSale, setCompletedSale] = useState<SaleOut | null>(null);
  const [isCheckingPrices, setIsCheckingPrices] = useState(false);

  const { data: settings } = useQuery({ queryKey: ["settings"], queryFn: fetchSettings });

  const checkoutMutation = useMutation({
    mutationFn: createSale,
    onSuccess: (sale) => {
      setCompletedSale(sale);
      cart.clear();
      resetPaymentState();
      setCheckoutError(null);
    },
    onError: (err: unknown) => {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Unable to complete sale. Please try again.";
      setCheckoutError(detail);
    },
  });

  function resetPaymentState() {
    setPaymentMethod(null);
    setAmountReceived("");
    setQrConfirmed(false);
    setPaymentReference("");
    setPriceMismatches([]);
  }

  function cartQuantityFor(productId: string): number {
    const line = cart.lines.find((l) => l.product.id === productId);
    return line ? parseFloat(line.quantity || "0") : 0;
  }

  function handleAddProduct(product: Product) {
    cart.addProduct(product, 1);
    setCheckoutError(null);
  }

  const isPaymentValid =
    paymentMethod === "CASH"
      ? parseFloat(amountReceived || "0") >= cart.netTotal
      : paymentMethod === "QR"
        ? qrConfirmed
        : false;

  const canAttemptCheckout = !cart.isEmpty && isPaymentValid && priceMismatches.length === 0;

  /**
   * Price-freshness check (Phase 2 POS review amendment 6): re-fetches
   * each cart product's CURRENT price right before submission. The
   * backend is always authoritative regardless — this exists purely so
   * the cashier is never surprised by a total that silently changed
   * between adding an item and completing the sale. Uses the existing
   * GET /api/products/{id} endpoint; no backend change needed.
   */
  async function checkPricesAreFresh(): Promise<boolean> {
    setIsCheckingPrices(true);
    try {
      const mismatches: PriceMismatch[] = [];
      for (const line of cart.lines) {
        const fresh = await getProduct(line.product.id);
        if (fresh.sale_price !== line.product.sale_price) {
          mismatches.push({
            productId: line.product.id,
            productName: line.product.name,
            oldPrice: line.product.sale_price,
            newPrice: fresh.sale_price,
          });
        }
      }
      setPriceMismatches(mismatches);
      return mismatches.length === 0;
    } finally {
      setIsCheckingPrices(false);
    }
  }

  function acceptPriceUpdate(mismatch: PriceMismatch) {
    cart.applyRefreshedPrice(mismatch.productId, mismatch.newPrice);
    setPriceMismatches((prev) => prev.filter((m) => m.productId !== mismatch.productId));
  }

  async function handleCompleteSale() {
    if (!paymentMethod || !isPaymentValid) return;

    const pricesFresh = await checkPricesAreFresh();
    if (!pricesFresh) return; // cashier must review/accept updated prices first

    checkoutMutation.mutate({
      items: cart.lines.map((l) => ({ product_id: l.product.id, quantity: l.quantity })),
      discount_amount: cart.discountAmount || "0.00",
      payment_method: paymentMethod,
      amount_received: paymentMethod === "CASH" ? amountReceived : null,
      payment_reference: paymentMethod === "QR" && paymentReference ? paymentReference : null,
    });
  }

  function handleClearBillRequest() {
    if (cart.isEmpty) return;
    setShowClearConfirm(true);
  }

  function confirmClearBill() {
    cart.clear();
    resetPaymentState();
    setCheckoutError(null);
    setShowClearConfirm(false);
  }

  // Focus the cash amount input the moment the Cash panel opens.
  useEffect(() => {
    if (paymentMethod === "CASH") {
      cashAmountRef.current?.focus();
    }
  }, [paymentMethod]);

  // Global keyboard shortcuts (spec section 8; Phase 2 POS review 4/5/8/9).
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (completedSale || showClearConfirm) {
        if (e.key === "Escape") {
          e.preventDefault();
          if (completedSale) setCompletedSale(null);
          if (showClearConfirm) setShowClearConfirm(false);
        }
        return;
      }

      if (e.key === "F2") {
        e.preventDefault();
        searchInputRef.current?.focus();
      } else if (e.key === "F4") {
        e.preventDefault();
        discountInputRef.current?.focus();
      } else if (e.key === "F8") {
        e.preventDefault();
        setPaymentMethod("CASH");
      } else if (e.key === "F9") {
        e.preventDefault();
        setPaymentMethod("QR");
      } else if (e.key === "Escape") {
        if (document.activeElement === searchInputRef.current) {
          return; // ProductSearch's own handler already cleared it
        }
        e.preventDefault();
        handleClearBillRequest();
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [completedSale, showClearConfirm, cart.isEmpty]);

  if (completedSale && settings && user) {
    return (
      <div className="p-8 bg-gray-100 min-h-full flex items-start justify-center">
        <div className="bg-white rounded-lg shadow-md p-6">
          <Receipt
            sale={completedSale}
            settings={settings}
            counterName={user.default_counter?.name ?? "—"}
            onPrint={() => window.print()}
            onClose={() => setCompletedSale(null)}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 flex flex-col h-full gap-4">
      <div className="flex items-center justify-between border-b border-gray-200 pb-3">
        <h1 className="text-lg font-semibold">POS</h1>
        <div className="text-sm text-gray-500">
          {user?.default_counter?.name ?? "No counter assigned"} · {user?.full_name}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 flex-1 min-h-0">
        {/* Left: search + results */}
        <div className="flex flex-col gap-3">
          <ProductSearch ref={searchInputRef} onAdd={handleAddProduct} cartQuantityFor={cartQuantityFor} />
        </div>

        {/* Right: cart + totals + payment */}
        <div className="flex flex-col gap-3 min-h-0">
          <Cart lines={cart.lines} onUpdateQuantity={cart.updateQuantity} onRemove={cart.removeLine} />

          <div className="border-t border-gray-200 pt-3 space-y-2">
            <div className="flex justify-between text-sm text-gray-500">
              <span>Subtotal</span>
              <span>Rs. {cart.subtotal.toFixed(2)}</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <label htmlFor="discount" className="text-gray-500">
                Discount <span className="text-gray-400">(F4)</span>
              </label>
              <input
                id="discount"
                ref={discountInputRef}
                type="number"
                min="0"
                step="0.01"
                value={cart.discountAmount}
                onChange={(e) => cart.setDiscountAmount(e.target.value)}
                className="w-28 border border-gray-300 rounded-md px-2 py-1 text-right"
                placeholder="0.00"
              />
            </div>
            <div className="flex justify-between text-lg font-bold border-t border-gray-200 pt-2">
              <span>TOTAL</span>
              <span>Rs. {cart.netTotal.toFixed(2)}</span>
            </div>
          </div>

          {priceMismatches.length > 0 && (
            <div className="bg-amber-50 border border-amber-300 rounded-md p-3 text-sm space-y-2">
              <div className="font-medium text-amber-800">
                Prices have changed since these items were added — review before completing:
              </div>
              {priceMismatches.map((m) => (
                <div key={m.productId} className="flex items-center justify-between">
                  <span>
                    {m.productName}: <span className="line-through text-gray-400">Rs. {m.oldPrice}</span>{" "}
                    → <span className="font-semibold">Rs. {m.newPrice}</span>
                  </span>
                  <button
                    onClick={() => acceptPriceUpdate(m)}
                    className="text-xs bg-amber-600 hover:bg-amber-700 text-white rounded px-2 py-1"
                  >
                    Update Price
                  </button>
                </div>
              ))}
            </div>
          )}

          {checkoutError && (
            <div className="bg-red-50 border border-red-200 text-danger text-sm rounded-md p-3">
              {checkoutError}
            </div>
          )}

          <PaymentPanel
            ref={cashAmountRef}
            netTotal={cart.netTotal}
            paymentMethod={paymentMethod}
            onSelectMethod={setPaymentMethod}
            amountReceived={amountReceived}
            onAmountReceivedChange={setAmountReceived}
            qrConfirmed={qrConfirmed}
            onQrConfirmedChange={setQrConfirmed}
            paymentReference={paymentReference}
            onPaymentReferenceChange={setPaymentReference}
            onCompleteViaEnter={handleCompleteSale}
          />

          <button
            onClick={handleCompleteSale}
            disabled={!canAttemptCheckout || checkoutMutation.isPending || isCheckingPrices}
            className="w-full bg-success hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold rounded-md py-3"
          >
            {checkoutMutation.isPending || isCheckingPrices ? "Processing…" : "COMPLETE SALE (Enter)"}
          </button>
        </div>
      </div>

      {showClearConfirm && (
        <ConfirmClearBillModal onCancel={() => setShowClearConfirm(false)} onConfirm={confirmClearBill} />
      )}
    </div>
  );
}
