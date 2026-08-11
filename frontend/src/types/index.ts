export type RoleName = "OWNER" | "EMPLOYEE";

export interface Counter {
  id: string;
  name: string;
  code: string;
}

export interface CurrentUser {
  id: string;
  username: string;
  full_name: string;
  role: RoleName;
  default_counter: Counter | null;
}

export interface Product {
  id: string;
  name: string;
  barcode: string | null;
  internal_code: string | null;
  unit: string;
  sale_price: string;
  reorder_level: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}
