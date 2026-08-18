interface ConfirmClearBillModalProps {
  onCancel: () => void;
  onConfirm: () => void;
}

/** Esc on a non-empty bill opens this instead of clearing immediately
 * (Phase 2 POS review amendment 4) — cancel is the default/safe action. */
export function ConfirmClearBillModal({ onCancel, onConfirm }: ConfirmClearBillModalProps) {
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-sm">
        <h3 className="font-semibold text-gray-900 mb-2">Clear current bill?</h3>
        <p className="text-sm text-gray-500 mb-5">
          This will remove all items from the current bill. This cannot be undone.
        </p>
        <div className="flex justify-end gap-2">
          <button
            onClick={onCancel}
            autoFocus
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="px-4 py-2 text-sm font-medium text-white bg-danger hover:opacity-90 rounded-md"
          >
            Clear Bill
          </button>
        </div>
      </div>
    </div>
  );
}
