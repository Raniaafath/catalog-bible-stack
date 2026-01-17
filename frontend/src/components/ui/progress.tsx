import * as React from "react";
import { cn } from "../../lib/utils";

export const Progress = ({ value, className }: { value: number; className?: string }) => (
  <div className={cn("h-2 w-full rounded-full bg-ink-100", className)}>
    <div
      className="h-2 rounded-full bg-ink-900 transition-all"
      style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
    />
  </div>
);
