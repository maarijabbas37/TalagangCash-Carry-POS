import { forwardRef } from "react";
import type { PaymentMethod } from "../../types";

interface PaymentPanelProps {
  netTotal: number;
  paymentMethod: PaymentMethod | null;
  onSelectMethod: (method: PaymentMethod) => void;
  amountReceived: string;
  onAmountReceivedChange: (value: string) => void;
  qrConfirmed: boolean;
  onQrConfirmedChange: (value: boolean) => void;
  paymentReference: string;
  onPaymentReferenceChange: (value: string) => void;
  /** Enter is context-dependent (Phase 2 POS review amendment 5) — this
   * fires only when focus is within this panel AND payment is valid. */
  onCompleteViaEnter: () => void;
}

export const PaymentPanel = forwardRef<HTMLInputElement, PaymentPanelProps>(function PaymentPanel(
  {
    netTotal,
    paymentMethod,
    onSelectMethod,
    amountReceived,
    onAmountReceivedChange,
    qrConfirmed,
    onQrConfirmedChange,
    paymentReference,
    onPaymentReferenceChange,
    onCompleteViaEnter,
  },
  amountReceivedRef
) {
  const received = parseFloat(amountReceived || "0");
  const change = received - netTotal;
  const cashValid = received >= netTotal;

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-2">
        <button
          type="button"
          onClick={() => onSelectMethod("CASH")}
          className={`py-3 rounded-md font-medium text-sm border ${
            paymentMethod === "CASH"
              ? "bg-brand-600 text-white border-brand-600"
              : "bg-white text-gray-700 border-gray-300 hover:bg-gray-50"
          }`}
        >
          💵 CASH <span className="opacity-60 font-normal">(F8)</span>
        </button>
        <button
          type="button"
          onClick={() => onSelectMethod("QR")}
          className={`py-3 rounded-md font-medium text-sm border ${
            paymentMethod === "QR"
              ? "bg-brand-600 text-white border-brand-600"
              : "bg-white text-gray-700 border-gray-300 hover:bg-gray-50"
          }`}
        >
          📱 QR / ONLINE <span className="opacity-60 font-normal">(F9)</span>
        </button>
      </div>

      {paymentMethod === "CASH" && (
        <div className="bg-gray-50 border border-gray-200 rounded-md p-3 space-y-2">
          <label className="block text-xs font-medium text-gray-600">Amount Received</label>
          <input
            ref={amountReceivedRef}
            type="number"
            step="0.01"
            min="0"
            value={amountReceived}
            onChange={(e) => onAmountReceivedChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && cashValid) {
                e.preventDefault();
                onCompleteViaEnter();
              }
            }}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-lg font-medium"
            placeholder="0.00"
          />
          <div className="flex justify-between text-sm">
            <span className="text-gray-500">Change</span>
            <span className={`font-semibold ${change < 0 ? "text-danger" : "text-success"}`}>
              Rs. {received > 0 ? Math.max(change, 0).toFixed(2) : "0.00"}
            </span>
          </div>
          {received > 0 && change < 0 && (
            <div className="text-xs text-danger">Amount received is less than the total due.</div>
          )}
        </div>
      )}

      {paymentMethod === "QR" && (
        <div
          className="bg-gray-50 border border-gray-200 rounded-md p-3 space-y-3"
          onKeyDown={(e) => {
            if (e.key === "Enter" && qrConfirmed) {
              e.preventDefault();
              onCompleteViaEnter();
            }
          }}
        >
          <div className="text-sm text-gray-600">
            Total: <span className="font-semibold text-gray-900">Rs. {netTotal.toFixed(2)}</span>
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={qrConfirmed}
              onChange={(e) => onQrConfirmedChange(e.target.checked)}
              className="h-4 w-4"
            />
            I have confirmed the QR payment was received
          </label>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Reference (optional)
            </label>
            <input
              type="text"
              value={paymentReference}
              onChange={(e) => onPaymentReferenceChange(e.target.value)}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
            />
          </div>
        </div>
      )}
    </div>
  );
});
