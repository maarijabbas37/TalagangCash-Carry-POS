import { useCallback, useMemo, useState } from "react";
import type { CartLine, Product } from "../types";

/**
 * Client-side cart state. All totals computed here are a PREVIEW only —
 * the backend recomputes everything from the current DB price at
 * checkout (Phase 2 sale_service.py snapshots sale_price server-side).
 * Plain JS number math is fine for a preview; it is never sent as a
 * price to the API — only product_id + quantity are sent.
 */
export function usePosCart() {
  const [lines, setLines] = useState<CartLine[]>([]);
  const [discountAmount, setDiscountAmount] = useState<string>("0.00");

  const addProduct = useCallback((product: Product, quantityToAdd = 1) => {
    setLines((prev) => {
      const existingIndex = prev.findIndex((l) => l.product.id === product.id);
      if (existingIndex >= 0) {
        // Repeated scan merges into the existing line (spec section 7) —
        // also required by the backend, which rejects duplicate
        // product_id entries in POST /api/sales.
        const updated = [...prev];
        const newQty = (parseFloat(updated[existingIndex].quantity) + quantityToAdd).toString();
        updated[existingIndex] = { ...updated[existingIndex], quantity: newQty };
        return updated;
      }
      return [
        ...prev,
        { product, quantity: quantityToAdd.toString(), priceWhenAdded: product.sale_price },
      ];
    });
  }, []);

  const updateQuantity = useCallback((productId: string, quantity: string) => {
    setLines((prev) => prev.map((l) => (l.product.id === productId ? { ...l, quantity } : l)));
  }, []);

  const removeLine = useCallback((productId: string) => {
    setLines((prev) => prev.filter((l) => l.product.id !== productId));
  }, []);

  const clear = useCallback(() => {
    setLines([]);
    setDiscountAmount("0.00");
  }, []);

  /** Applies a fresher price fetched right before checkout (price-freshness check). */
  const applyRefreshedPrice = useCallback((productId: string, newPrice: string) => {
    setLines((prev) =>
      prev.map((l) => (l.product.id === productId ? { ...l, priceWhenAdded: newPrice, product: { ...l.product, sale_price: newPrice } } : l))
    );
  }, []);

  const subtotal = useMemo(
    () => lines.reduce((sum, l) => sum + parseFloat(l.product.sale_price) * parseFloat(l.quantity || "0"), 0),
    [lines]
  );

  const discount = useMemo(() => parseFloat(discountAmount || "0"), [discountAmount]);
  const netTotal = useMemo(() => Math.max(subtotal - discount, 0), [subtotal, discount]);

  const isEmpty = lines.length === 0;

  return {
    lines,
    discountAmount,
    setDiscountAmount,
    addProduct,
    updateQuantity,
    removeLine,
    clear,
    applyRefreshedPrice,
    subtotal,
    discount,
    netTotal,
    isEmpty,
  };
}
export type PosCart = ReturnType<typeof usePosCart>;
