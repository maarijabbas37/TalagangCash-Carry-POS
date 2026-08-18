import type { CartLine } from "../../types";

interface CartProps {
  lines: CartLine[];
  onUpdateQuantity: (productId: string, quantity: string) => void;
  onRemove: (productId: string) => void;
}

export function Cart({ lines, onUpdateQuantity, onRemove }: CartProps) {
  if (lines.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-gray-400 text-sm border border-dashed border-gray-200 rounded-md">
        Scan or search a product to start the bill.
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-auto border border-gray-200 rounded-md">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 text-gray-600 text-left sticky top-0">
          <tr>
            <th className="px-3 py-2">Product</th>
            <th className="px-3 py-2 w-24">Qty</th>
            <th className="px-3 py-2 text-right">Price</th>
            <th className="px-3 py-2 text-right">Total</th>
            <th className="px-2 py-2 w-8"></th>
          </tr>
        </thead>
        <tbody>
          {lines.map((line) => {
            const qty = parseFloat(line.quantity || "0");
            const price = parseFloat(line.product.sale_price);
            const lineTotal = (qty * price).toFixed(2);
            const stock = parseFloat(line.product.current_stock);
            const exceedsStock = qty > stock;

            return (
              <tr key={line.product.id} className="border-t border-gray-100">
                <td className="px-3 py-2">
                  <div className="font-medium">{line.product.name}</div>
                  {exceedsStock && (
                    <div className="text-xs text-danger">Only {stock} available</div>
                  )}
                </td>
                <td className="px-3 py-2">
                  <input
                    type="number"
                    min="0"
                    step={line.product.unit === "pcs" ? "1" : "0.01"}
                    value={line.quantity}
                    onChange={(e) => onUpdateQuantity(line.product.id, e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        (e.target as HTMLInputElement).blur();
                      }
                    }}
                    className={`w-20 border rounded-md px-2 py-1 text-sm ${
                      exceedsStock ? "border-danger" : "border-gray-300"
                    }`}
                  />
                </td>
                <td className="px-3 py-2 text-right text-gray-500">Rs. {line.product.sale_price}</td>
                <td className="px-3 py-2 text-right font-medium">Rs. {lineTotal}</td>
                <td className="px-2 py-2 text-center">
                  <button
                    type="button"
                    onClick={() => onRemove(line.product.id)}
                    className="text-gray-400 hover:text-danger"
                    aria-label={`Remove ${line.product.name}`}
                  >
                    ✕
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
