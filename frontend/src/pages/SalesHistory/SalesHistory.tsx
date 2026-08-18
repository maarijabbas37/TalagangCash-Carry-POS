import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../../api/client";
import { getSaleByBillNumber, listSales } from "../../api/sales";
import { fetchSettings } from "../../api/settings";
import { Receipt } from "../../components/pos/Receipt";
import type { Counter, SaleOut } from "../../types";

export function SalesHistory() {
  const [billNumberQuery, setBillNumberQuery] = useState("");
  const [selectedSale, setSelectedSale] = useState<SaleOut | null>(null);
  const [searchError, setSearchError] = useState<string | null>(null);

  const { data: settings } = useQuery({ queryKey: ["settings"], queryFn: fetchSettings });
  const { data: recentSales, isLoading } = useQuery({ queryKey: ["sales", "recent"], queryFn: () => listSales(25) });
  const { data: counters } = useQuery({
    queryKey: ["counters"],
    queryFn: async () => (await apiClient.get<Counter[]>("/api/counters")).data,
  });

  function counterName(counterId: string): string {
    return counters?.find((c) => c.id === counterId)?.name ?? "—";
  }

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    setSearchError(null);
    const num = parseInt(billNumberQuery, 10);
    if (Number.isNaN(num)) {
      setSearchError("Enter a valid bill number.");
      return;
    }
    try {
      const sale = await getSaleByBillNumber(num);
      setSelectedSale(sale);
    } catch {
      setSearchError(`Bill #${billNumberQuery} not found.`);
    }
  }

  if (selectedSale && settings) {
    return (
      <div className="p-8 bg-gray-100 min-h-full flex items-start justify-center">
        <div className="bg-white rounded-lg shadow-md p-6">
          <Receipt
            sale={selectedSale}
            settings={settings}
            counterName={counterName(selectedSale.counter_id)}
            onPrint={() => window.print()}
            onClose={() => setSelectedSale(null)}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-3xl">
      <h2 className="text-lg font-semibold mb-4">Sales History</h2>

      <form onSubmit={handleSearch} className="flex gap-2 mb-6">
        <input
          type="text"
          inputMode="numeric"
          value={billNumberQuery}
          onChange={(e) => setBillNumberQuery(e.target.value)}
          placeholder="Enter bill number…"
          className="flex-1 border border-gray-300 rounded-md px-3 py-2 text-sm"
        />
        <button
          type="submit"
          className="bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium rounded-md px-4 py-2"
        >
          Find
        </button>
      </form>
      {searchError && <div className="text-sm text-danger mb-4">{searchError}</div>}

      <h3 className="text-sm font-medium text-gray-500 mb-2">Recent Sales</h3>
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-600 text-left">
            <tr>
              <th className="px-4 py-2">Bill No.</th>
              <th className="px-4 py-2">Date</th>
              <th className="px-4 py-2">Counter</th>
              <th className="px-4 py-2 text-right">Total</th>
              <th className="px-4 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-gray-400">
                  Loading…
                </td>
              </tr>
            )}
            {recentSales?.map((sale) => (
              <tr key={sale.id} className="border-t border-gray-100">
                <td className="px-4 py-2 font-mono">{String(sale.bill_number).padStart(7, "0")}</td>
                <td className="px-4 py-2 text-gray-500">{new Date(sale.created_at).toLocaleString()}</td>
                <td className="px-4 py-2 text-gray-500">{counterName(sale.counter_id)}</td>
                <td className="px-4 py-2 text-right font-medium">Rs. {sale.net_total}</td>
                <td className="px-4 py-2 text-right">
                  <button
                    onClick={() => setSelectedSale(sale)}
                    className="text-brand-600 hover:underline text-xs font-medium"
                  >
                    View / Reprint
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
