import * as React from "react";
import { cn } from "../../lib/utils";

export type TabItem = {
  value: string;
  label: string;
};

export const Tabs = ({
  items,
  value,
  onChange,
  className,
}: {
  items: TabItem[];
  value: string;
  onChange: (value: string) => void;
  className?: string;
}) => (
  <div className={cn("flex flex-wrap gap-2", className)}>
    {items.map((item) => (
      <button
        key={item.value}
        onClick={() => onChange(item.value)}
        className={cn(
          "rounded-full px-4 py-2 text-sm font-medium",
          value === item.value
            ? "bg-ink-900 text-white"
            : "bg-white text-ink-700 border border-ink-200 hover:bg-ink-50"
        )}
        type="button"
      >
        {item.label}
      </button>
    ))}
  </div>
);
