import { apiClient } from "./client";
import type { Supplier, SupplierCreatePayload } from "../types";

export async function listSuppliers(): Promise<Supplier[]> {
  const res = await apiClient.get<Supplier[]>("/api/suppliers");
  return res.data;
}

export async function createSupplier(payload: SupplierCreatePayload): Promise<Supplier> {
  const res = await apiClient.post<Supplier>("/api/suppliers", payload);
  return res.data;
}

export async function getSupplier(id: string): Promise<Supplier> {
  const res = await apiClient.get<Supplier>(`/api/suppliers/${id}`);
  return res.data;
}
