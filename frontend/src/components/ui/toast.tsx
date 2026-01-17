import * as React from "react";
import { cn } from "../../lib/utils";

export type ToastItem = {
  id: string;
  title: string;
  description?: string;
  variant?: "default" | "success" | "error";
};

const ToastContext = React.createContext<{
  toasts: ToastItem[];
  push: (toast: Omit<ToastItem, "id">) => void;
}>({
  toasts: [],
  push: () => undefined,
});

const variantClasses: Record<string, string> = {
  default: "border-ink-200",
  success: "border-emerald-200",
  error: "border-rose-200",
};

export const ToastProvider = ({ children }: { children: React.ReactNode }) => {
  const [toasts, setToasts] = React.useState<ToastItem[]>([]);

  const push = React.useCallback((toast: Omit<ToastItem, "id">) => {
    const id = `${Date.now()}-${Math.random()}`;
    setToasts((prev) => [...prev, { ...toast, id }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((item) => item.id !== id));
    }, 4000);
  }, []);

  return (
    <ToastContext.Provider value={{ toasts, push }}>
      {children}
      <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-3">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={cn(
              "rounded-lg border bg-white px-4 py-3 shadow-soft",
              variantClasses[toast.variant || "default"]
            )}
          >
            <p className="text-sm font-semibold text-ink-900">{toast.title}</p>
            {toast.description ? (
              <p className="text-xs text-ink-500">{toast.description}</p>
            ) : null}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
};

export const useToast = () => React.useContext(ToastContext);
