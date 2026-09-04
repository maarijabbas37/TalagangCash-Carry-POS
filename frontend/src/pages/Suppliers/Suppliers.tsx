import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createSupplier, listSuppliers } from "../../api/suppliers";

export function Suppliers() {
  const queryClient = useQueryClient();
  const [showAddForm, setShowAddForm] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [addressNotes, setAddressNotes] = useState("");

  const { data: suppliers, isLoading } = useQuery({
    queryKey: ["suppliers"],
    queryFn: listSuppliers,
  });

  const createMutation = useMutation({
    mutationFn: () =>
      createSupplier({
        name,
        phone: phone || null,
        address_notes: addressNotes || null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["suppliers"] });
      setShowAddForm(false);
      setName("");
      setPhone("");
      setAddressNotes("");
      setError(null);
    },
    onError: (err: unknown) => {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Unable to save supplier.";
      setError(detail);
    },
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    createMutation.mutate();
  }

  return (
    <div className="p-8 max-w-3xl">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">Suppliers</h2>
        <button
          onClick={() => setShowAddForm((v) => !v)}
          className="bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium rounded-md px-4 py-2"
        >
          {showAddForm ? "Cancel" : "+ Add Supplier"}
        </button>
      </div>

      {showAddForm && (
        <form
          onSubmit={handleSubmit}
          className="bg-white border border-gray-200 rounded-lg p-4 mb-6 space-y-3"
        >
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Supplier Name</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Phone</label>
            <input
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Address / Notes</label>
            <textarea
              value={addressNotes}
              onChange={(e) => setAddressNotes(e.target.value)}
              rows={2}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
            />
          </div>

          {error && (
            <div className="text-sm text-danger bg-red-50 border border-red-200 rounded-md px-3 py-2">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={createMutation.isPending}
            className="bg-brand-600 hover:bg-brand-700 disabled:opacity-60 text-white text-sm font-medium rounded-md px-4 py-2"
          >
            {createMutation.isPending ? "Saving…" : "SAVE SUPPLIER"}
          </button>
        </form>
      )}

      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-600 text-left">
            <tr>
              <th className="px-4 py-2">Name</th>
              <th className="px-4 py-2">Phone</th>
              <th className="px-4 py-2">Notes</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr>
                <td colSpan={3} className="px-4 py-6 text-center text-gray-400">
                  Loading…
                </td>
              </tr>
            )}
            {!isLoading && suppliers?.length === 0 && (
              <tr>
                <td colSpan={3} className="px-4 py-6 text-center text-gray-400">
                  No suppliers yet.
                </td>
              </tr>
            )}
            {suppliers?.map((s) => (
              <tr key={s.id} className="border-t border-gray-100">
                <td className="px-4 py-2 font-medium">{s.name}</td>
                <td className="px-4 py-2 text-gray-500">{s.phone ?? "—"}</td>
                <td className="px-4 py-2 text-gray-500">{s.address_notes ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
