import * as React from "react";
import { cn } from "../../lib/utils";

export const Dropdown = ({
  label,
  children,
  className,
}: {
  label: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) => {
  const [open, setOpen] = React.useState(false);
  return (
    <div className={cn("relative", className)}>
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="inline-flex items-center gap-2 rounded-md border border-ink-200 bg-white px-3 py-2 text-sm"
      >
        {label}
        <span className="text-ink-400">▾</span>
      </button>
      {open ? (
        <div className="absolute right-0 z-20 mt-2 min-w-[180px] rounded-md border border-ink-100 bg-white shadow-soft">
          <div className="p-2" onMouseLeave={() => setOpen(false)}>
            {children}
          </div>
        </div>
      ) : null}
    </div>
  );
};

export const DropdownItem = ({
  children,
  onClick,
}: {
  children: React.ReactNode;
  onClick?: () => void;
}) => (
  <button
    type="button"
    onClick={onClick}
    className="flex w-full items-center rounded-md px-3 py-2 text-left text-sm text-ink-700 hover:bg-ink-50"
  >
    {children}
  </button>
);
