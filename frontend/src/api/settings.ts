import { apiClient } from "./client";
import type { StoreSettings } from "../types";

export async function fetchSettings(): Promise<StoreSettings> {
  const res = await apiClient.get<StoreSettings>("/api/settings");
  return res.data;
}
