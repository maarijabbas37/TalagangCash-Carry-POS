import type { SaleOut, StoreSettings } from "../../types";

interface ReceiptProps {
  sale: SaleOut;
  settings: StoreSettings;
  counterName: string;
  onPrint?: () => void;
  onClose?: () => void;
}

/**
 * The SAME component renders: the receipt immediately after checkout,
 * a historical sale, and a reprint — identical data, identical markup,
 * by construction. No code path here can create or modify a sale; it
 * only ever displays the SaleOut it's given.
 */
export function Receipt({ sale, settings, counterName, onPrint, onClose }: ReceiptProps) {
  const payment = sale.payments[0];
  const billNumberDisplay = String(sale.bill_number).padStart(7, "0");
  const dateObj = new Date(sale.created_at);

  return (
    <div>
      <div id="receipt-print-area" className="bg-white mx-auto" style={{ width: "300px", fontFamily: "monospace" }}>
        <div className="text-center text-xs leading-tight p-3 border-b border-dashed border-gray-400">
          <div className="font-bold text-sm">{settings.store_name}</div>
          <div>{settings.store_address}</div>
          <div>Phone: {settings.store_phone}</div>
        </div>

        <div className="text-xs p-3 border-b border-dashed border-gray-400 space-y-0.5">
          <div className="flex justify-between">
            <span>Bill No:</span>
            <span>{billNumberDisplay}</span>
          </div>
          <div className="flex justify-between">
            <span>Date:</span>
            <span>{dateObj.toLocaleDateString()}</span>
          </div>
          <div className="flex justify-between">
            <span>Time:</span>
            <span>{dateObj.toLocaleTimeString()}</span>
          </div>
          <div className="flex justify-between">
            <span>Counter:</span>
            <span>{counterName}</span>
          </div>
          <div className="flex justify-between">
            <span>Cashier:</span>
            <span>{sale.cashier_name}</span>
          </div>
        </div>

        <div className="text-xs p-3 border-b border-dashed border-gray-400">
          <div className="flex justify-between font-semibold mb-1">
            <span>ITEM</span>
            <span>QTY&nbsp;&nbsp;TOTAL</span>
          </div>
          {sale.items.map((item) => (
            <div key={item.id} className="flex justify-between">
              <span className="truncate pr-2">{item.product_name}</span>
              <span>
                {item.quantity}&nbsp;&nbsp;{item.line_total}
              </span>
            </div>
          ))}
        </div>

        <div className="text-xs p-3 border-b border-dashed border-gray-400 space-y-0.5">
          <div className="flex justify-between">
            <span>Subtotal</span>
            <span>{sale.subtotal}</span>
          </div>
          {parseFloat(sale.discount_amount) > 0 && (
            <div className="flex justify-between">
              <span>Discount</span>
              <span>{sale.discount_amount}</span>
            </div>
          )}
          <div className="flex justify-between font-bold text-sm pt-1 border-t border-gray-300 mt-1">
            <span>TOTAL</span>
            <span>{sale.net_total}</span>
          </div>
        </div>

        {payment && (
          <div className="text-xs p-3 border-b border-dashed border-gray-400 space-y-0.5">
            <div className="flex justify-between">
              <span>Payment:</span>
              <span>{payment.payment_method}</span>
            </div>
            {payment.payment_method === "CASH" && (
              <>
                <div className="flex justify-between">
                  <span>Paid:</span>
                  <span>{payment.amount_received}</span>
                </div>
                <div className="flex justify-between">
                  <span>Change:</span>
                  <span>{payment.change_amount}</span>
                </div>
              </>
            )}
            {payment.payment_method === "QR" && payment.payment_reference && (
              <div className="flex justify-between">
                <span>Ref:</span>
                <span>{payment.payment_reference}</span>
              </div>
            )}
          </div>
        )}

        <div className="text-center text-xs p-3">
          <div className="font-semibold">THANK YOU!</div>
          <div>PLEASE VISIT AGAIN</div>
        </div>
      </div>

      <div className="flex gap-2 justify-center mt-4 print:hidden">
        {onPrint && (
          <button
            onClick={onPrint}
            className="bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium rounded-md px-4 py-2"
          >
            Print Receipt
          </button>
        )}
        {onClose && (
          <button
            onClick={onClose}
            className="bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm font-medium rounded-md px-4 py-2"
          >
            Close
          </button>
        )}
      </div>
    </div>
  );
}
