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
  last_purchase_cost: string | null;
  preferred_supplier_id: string | null;
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
  priceWhenAdded: string;
}

// --- Phase 3: Suppliers ---

export interface Supplier {
  id: string;
  name: string;
  phone: string | null;
  address_notes: string | null;
  is_active: boolean;
  created_at: string;
}

export interface SupplierCreatePayload {
  name: string;
  phone?: string | null;
  address_notes?: string | null;
}

// --- Phase 3: Purchases (stock receiving) ---

export interface PurchaseItemIn {
  product_id: string;
  quantity: string;
  unit_cost: string;
}

export interface PurchaseCreatePayload {
  supplier_id: string;
  items: PurchaseItemIn[];
  invoice_number?: string | null;
  invoice_date?: string | null;
  invoice_total?: string | null;
  notes?: string | null;
  mismatch_acknowledged?: boolean;
}

export interface PurchaseItemOut {
  id: string;
  product_id: string;
  product_name: string;
  quantity: string;
  unit_cost: string;
  line_total: string;
}

export interface PurchasePaymentOut {
  id: string;
  amount: string;
  user_id: string;
  paid_at: string;
  notes: string | null;
}

export interface PurchaseOut {
  id: string;
  supplier_id: string;
  invoice_number: string | null;
  invoice_date: string | null;
  invoice_total: string | null;
  computed_total: string;
  mismatch_acknowledged: boolean;
  received_by_user_id: string;
  notes: string | null;
  items: PurchaseItemOut[];
  payments: PurchasePaymentOut[];
  amount_paid: string;
  outstanding: string;
  created_at: string;
}

export interface PurchaseCartLine {
  product: Product;
  quantity: string;
  unit_cost: string;
}
