import * as React from "react";
import { cn } from "../lib/utils";

export const FileUpload = ({
  label,
  onFile,
}: {
  label?: string;
  onFile: (file: File) => void;
}) => {
  const [dragOver, setDragOver] = React.useState(false);

  return (
    <label
      className={cn(
        "flex cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed",
        "border-ink-200 bg-ink-50/60 px-6 py-10 text-center",
        dragOver ? "border-ink-400 bg-ink-100/60" : ""
      )}
      onDragOver={(event) => {
        event.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(event) => {
        event.preventDefault();
        setDragOver(false);
        const file = event.dataTransfer.files?.[0];
        if (file) onFile(file);
      }}
    >
      <div className="text-sm font-semibold text-ink-700">{label || "Drop file here"}</div>
      <div className="text-xs text-ink-500">CSV or XLSX up to 50MB</div>
      <input
        type="file"
        className="hidden"
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) onFile(file);
        }}
      />
    </label>
  );
};
