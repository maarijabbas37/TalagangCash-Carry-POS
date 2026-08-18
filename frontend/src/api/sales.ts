import { apiClient } from "./client";
import type { SaleCreatePayload, SaleOut } from "../types";

export async function createSale(payload: SaleCreatePayload): Promise<SaleOut> {
  const res = await apiClient.post<SaleOut>("/api/sales", payload);
  return res.data;
}

export async function getSale(id: string): Promise<SaleOut> {
  const res = await apiClient.get<SaleOut>(`/api/sales/${id}`);
  return res.data;
}

export async function getSaleByBillNumber(billNumber: number): Promise<SaleOut> {
  const res = await apiClient.get<SaleOut>(`/api/sales/by-bill-number/${billNumber}`);
  return res.data;
}

export async function listSales(limit = 25): Promise<SaleOut[]> {
  const res = await apiClient.get<SaleOut[]>("/api/sales", { params: { limit } });
  return res.data;
}
