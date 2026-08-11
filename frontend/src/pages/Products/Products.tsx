import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "../../api/client";
import { useAuth } from "../../hooks/useAuth";
import type { Product } from "../../types";

export function Products() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [showAddForm, setShowAddForm] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [barcode, setBarcode] = useState("");
  const [internalCode, setInternalCode] = useState("");
  const [unit, setUnit] = useState("pcs");
  const [salePrice, setSalePrice] = useState("");

  const { data: products, isLoading } = useQuery({
    queryKey: ["products", search],
    queryFn: async () => {
      const res = await apiClient.get<Product[]>("/api/products", {
        params: search ? { q: search } : {},
      });
      return res.data;
    },
  });

  const createProduct = useMutation({
    mutationFn: async () => {
      await apiClient.post("/api/products", {
        name,
        barcode: barcode || null,
        internal_code: internalCode || null,
        unit,
        sale_price: salePrice,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["products"] });
      setShowAddForm(false);
      setName("");
      setBarcode("");
      setInternalCode("");
      setSalePrice("");
      setError(null);
    },
    onError: (err: unknown) => {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Unable to save product.";
      setError(detail);
    },
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    createProduct.mutate();
  }

  return (
    <div className="p-8 max-w-4xl">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">Products</h2>
        <button
          onClick={() => setShowAddForm((v) => !v)}
          className="bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium rounded-md px-4 py-2"
        >
          {showAddForm ? "Cancel" : "+ Add Product"}
        </button>
      </div>

      {showAddForm && (
        <form
          onSubmit={handleSubmit}
          className="bg-white border border-gray-200 rounded-lg p-4 mb-6 space-y-3"
        >
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Product Name</label>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Unit</label>
              <select
                value={unit}
                onChange={(e) => setUnit(e.target.value)}
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
              >
                <option value="pcs">pcs</option>
                <option value="kg">kg</option>
                <option value="litre">litre</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Barcode</label>
              <input
                value={barcode}
                onChange={(e) => setBarcode(e.target.value)}
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Internal Code</label>
              <input
                value={internalCode}
                onChange={(e) => setInternalCode(e.target.value)}
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Sale Price</label>
              <input
                type="number"
                step="0.01"
                min="0.01"
                value={salePrice}
                onChange={(e) => setSalePrice(e.target.value)}
                required
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
              />
            </div>
          </div>

          {error && (
            <div className="text-sm text-danger bg-red-50 border border-red-200 rounded-md px-3 py-2">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={createProduct.isPending}
            className="bg-brand-600 hover:bg-brand-700 disabled:opacity-60 text-white text-sm font-medium rounded-md px-4 py-2"
          >
            {createProduct.isPending ? "Saving…" : "SAVE PRODUCT"}
          </button>
        </form>
      )}

      <input
        type="text"
        placeholder="Search by name, barcode, or code…"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm mb-4"
      />

      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-600 text-left">
            <tr>
              <th className="px-4 py-2">Code</th>
              <th className="px-4 py-2">Barcode</th>
              <th className="px-4 py-2">Product</th>
              <th className="px-4 py-2 text-right">Price</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-gray-400">
                  Loading…
                </td>
              </tr>
            )}
            {!isLoading && products?.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-gray-400">
                  No products found.
                </td>
              </tr>
            )}
            {products?.map((p) => (
              <tr key={p.id} className="border-t border-gray-100">
                <td className="px-4 py-2 text-gray-500">{p.internal_code ?? "—"}</td>
                <td className="px-4 py-2 text-gray-500">{p.barcode ?? "—"}</td>
                <td className="px-4 py-2">{p.name}</td>
                <td className="px-4 py-2 text-right font-medium">Rs. {p.sale_price}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {user?.role !== "OWNER" && (
        <p className="text-xs text-gray-400 mt-3">
          Price changes require owner approval and are made from the Owner account.
        </p>
      )}
    </div>
  );
}
