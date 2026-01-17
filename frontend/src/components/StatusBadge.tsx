import { Badge } from "./ui/badge";

const map: Record<string, { label: string; variant: "default" | "success" | "warning" | "danger" | "neutral" }> = {
  UPLOADED: { label: "UPLOADED", variant: "neutral" },
  PARSED: { label: "PARSED", variant: "default" },
  MAPPED: { label: "MAPPED", variant: "default" },
  COMMITTED: { label: "COMMITTED", variant: "success" },
  FAILED: { label: "FAILED", variant: "danger" },
  READY: { label: "READY", variant: "default" },
  ATTR_MAPPED: { label: "ATTR_MAPPED", variant: "default" },
  TRANSLATED: { label: "TRANSLATED", variant: "default" },
  KEYWORDS_FETCHED: { label: "KEYWORDS_FETCHED", variant: "default" },
  KW_MAPPED: { label: "KW_MAPPED", variant: "default" },
  CANDIDATES_READY: { label: "CANDIDATES_READY", variant: "default" },
  TEMPLATE_READY: { label: "TEMPLATE_READY", variant: "default" },
  GENERATED: { label: "GENERATED", variant: "success" },
  EXPORTED: { label: "EXPORTED", variant: "success" },
};

export const StatusBadge = ({ status }: { status: string }) => {
  const entry = map[status] || { label: status, variant: "default" as const };
  return <Badge variant={entry.variant}>{entry.label}</Badge>;
};
