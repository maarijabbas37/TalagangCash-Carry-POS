import { apiClient } from "./client";
import type { Product } from "../types";

export async function searchProducts(q: string): Promise<Product[]> {
  const res = await apiClient.get<Product[]>("/api/products", { params: q ? { q } : {} });
  return res.data;
}

export async function getProduct(id: string): Promise<Product> {
  const res = await apiClient.get<Product>(`/api/products/${id}`);
  return res.data;
}
