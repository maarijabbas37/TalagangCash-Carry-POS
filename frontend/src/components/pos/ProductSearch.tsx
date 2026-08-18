import { useEffect, useRef, useState, forwardRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { searchProducts } from "../../api/products";
import type { Product } from "../../types";

interface ProductSearchProps {
  onAdd: (product: Product) => void;
  /** Current quantity already in the cart for a product, so we can warn
   * before pushing an addition past available stock. */
  cartQuantityFor: (productId: string) => number;
}

/**
 * One input handles barcode scanning, internal-code entry, and manual
 * search (spec section 7) — all three feed the same onAdd callback.
 *
 * Debounced live suggestions are a visual aid only. On Enter, we always
 * run an immediate (non-debounced) fetch against the exact current input
 * so a fast barcode scanner + Enter can never race the debounce timer.
 */
export const ProductSearch = forwardRef<HTMLInputElement, ProductSearchProps>(function ProductSearch(
  { onAdd, cartQuantityFor },
  ref
) {
  const [value, setValue] = useState("");
  const [highlighted, setHighlighted] = useState(0);
  const [warning, setWarning] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [debouncedValue, setDebouncedValue] = useState("");

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => setDebouncedValue(value), 200);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [value]);

  const { data: results = [] } = useQuery({
    queryKey: ["product-search", debouncedValue],
    queryFn: () => searchProducts(debouncedValue),
    enabled: debouncedValue.trim().length > 0,
  });

  useEffect(() => {
    setHighlighted(0);
  }, [results]);

  function tryAdd(product: Product) {
    const inCart = cartQuantityFor(product.id);
    const available = parseFloat(product.current_stock);

    if (available <= 0) {
      setWarning(`'${product.name}' is out of stock.`);
      return;
    }
    if (inCart + 1 > available) {
      setWarning(`Only ${available} of '${product.name}' in stock (${inCart} already in cart).`);
      return;
    }
    setWarning(null);
    onAdd(product);
    setValue("");
    setDebouncedValue("");
  }

  async function handleEnter() {
    const trimmed = value.trim();
    if (!trimmed) return;

    // Exact code match wins immediately — this is the barcode-scanner path.
    const exactMatch = results.find((p) => p.barcode === trimmed || p.internal_code === trimmed);
    if (exactMatch) {
      tryAdd(exactMatch);
      return;
    }

    // Not yet resolved by the debounced query (scanner faster than 200ms) —
    // fetch immediately rather than waiting on the debounce.
    const fresh = await searchProducts(trimmed);
    const freshExact = fresh.find((p) => p.barcode === trimmed || p.internal_code === trimmed);
    if (freshExact) {
      tryAdd(freshExact);
      return;
    }

    if (fresh.length > 0) {
      tryAdd(fresh[highlighted] ?? fresh[0]);
    } else {
      setWarning(`No product found for '${trimmed}'.`);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      e.preventDefault();
      handleEnter();
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlighted((h) => Math.min(h + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlighted((h) => Math.max(h - 1, 0));
    } else if (e.key === "Escape") {
      setValue("");
      setDebouncedValue("");
      setWarning(null);
    }
  }

  return (
    <div className="relative">
      <input
        ref={ref}
        type="text"
        value={value}
        onChange={(e) => {
          setValue(e.target.value);
          setWarning(null);
        }}
        onKeyDown={handleKeyDown}
        placeholder="Scan barcode / enter code / search product…  (F2)"
        className="w-full border border-gray-300 rounded-md px-3 py-3 text-base focus:outline-none focus:ring-2 focus:ring-brand-600"
        autoComplete="off"
      />

      {warning && <div className="mt-1 text-sm text-danger">{warning}</div>}

      {results.length > 0 && value.trim().length > 0 && (
        <div className="absolute z-10 mt-1 w-full bg-white border border-gray-200 rounded-md shadow-lg max-h-72 overflow-auto">
          {results.map((product, i) => {
            const stock = parseFloat(product.current_stock);
            const outOfStock = stock <= 0;
            return (
              <button
                key={product.id}
                type="button"
                disabled={outOfStock}
                onClick={() => tryAdd(product)}
                className={`w-full text-left px-3 py-2 flex items-center justify-between text-sm border-b border-gray-100 last:border-b-0 ${
                  i === highlighted ? "bg-brand-50" : "hover:bg-gray-50"
                } ${outOfStock ? "opacity-50 cursor-not-allowed" : ""}`}
              >
                <div>
                  <div className="font-medium">{product.name}</div>
                  <div className="text-gray-400 text-xs">
                    {product.internal_code ?? product.barcode ?? "—"} · {product.unit}
                  </div>
                </div>
                <div className="text-right">
                  <div className="font-medium">Rs. {product.sale_price}</div>
                  {outOfStock ? (
                    <div className="text-xs text-danger font-semibold">OUT OF STOCK</div>
                  ) : (
                    <div className="text-xs text-gray-400">{stock} in stock</div>
                  )}
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
});
