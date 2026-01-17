import * as React from "react";
import { cn } from "../../lib/utils";

export const Dialog = ({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
}) => {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink-900/40 p-6">
      <div className="w-full max-w-xl rounded-xl bg-white shadow-card">
        <div className="flex items-center justify-between border-b border-ink-100 px-6 py-4">
          <h3 className="text-lg font-semibold text-ink-900">{title}</h3>
          <button onClick={onClose} className="text-ink-500 hover:text-ink-800" type="button">
            ✕
          </button>
        </div>
        <div className={cn("px-6 py-5")}>{children}</div>
      </div>
    </div>
  );
};
