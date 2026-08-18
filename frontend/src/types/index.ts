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
  current_stock: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface StoreSettings {
  store_name: string;
  store_address: string;
  store_phone: string;
}

// --- Sales / POS ---

export type PaymentMethod = "CASH" | "QR";

export interface SaleItemIn {
  product_id: string;
  quantity: string;
}

export interface SaleCreatePayload {
  items: SaleItemIn[];
  discount_amount: string;
  payment_method: PaymentMethod;
  amount_received?: string | null;
  payment_reference?: string | null;
  // counter_id is intentionally never sent from the frontend — the
  // backend defaults to the cashier's default_counter_id. Arbitrary
  // counter selection from the client is not permitted (Phase 2 POS
  // review amendment 3).
}

export interface SaleItemOut {
  id: string;
  product_id: string;
  product_name: string;
  unit_price: string;
  quantity: string;
  line_total: string;
}

export interface PaymentOut {
  id: string;
  payment_method: PaymentMethod;
  amount: string;
  amount_received: string | null;
  change_amount: string;
  payment_reference: string | null;
  user_id: string;
  counter_id: string;
  created_at: string;
}

export interface SaleOut {
  id: string;
  bill_number: number;
  counter_id: string;
  cashier_id: string;
  cashier_name: string;
  subtotal: string;
  discount_amount: string;
  discount_user_id: string | null;
  net_total: string;
  items: SaleItemOut[];
  payments: PaymentOut[];
  created_at: string;
}

// --- POS cart (client-side only, before checkout) ---

export interface CartLine {
  product: Product;
  quantity: string;
  /** sale_price captured when the product was added to the cart — used
   * to detect a mismatch against the price the backend actually charges
   * (see price-freshness check before checkout). */
  priceWhenAdded: string;
}
