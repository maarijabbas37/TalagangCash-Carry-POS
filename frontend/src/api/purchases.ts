import { apiClient } from "./client";
import type { PurchaseCreatePayload, PurchaseOut } from "../types";

export async function createPurchase(payload: PurchaseCreatePayload): Promise<PurchaseOut> {
  const res = await apiClient.post<PurchaseOut>("/api/purchases", payload);
  return res.data;
}

export async function getPurchase(id: string): Promise<PurchaseOut> {
  const res = await apiClient.get<PurchaseOut>(`/api/purchases/${id}`);
  return res.data;
}

export async function listPurchases(supplierId?: string, limit = 25): Promise<PurchaseOut[]> {
  const res = await apiClient.get<PurchaseOut[]>("/api/purchases", {
    params: { ...(supplierId ? { supplier_id: supplierId } : {}), limit },
  });
  return res.data;
}

export async function recordPurchasePayment(
  purchaseId: string,
  amount: string,
  notes?: string | null
): Promise<PurchaseOut> {
  await apiClient.post(`/api/purchases/${purchaseId}/payments`, { amount, notes: notes || null });
  return getPurchase(purchaseId);
}
