import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';
import { Loader2, CheckCircle2, XCircle, Clock, AlertCircle, PauseCircle } from 'lucide-react';

const statusBadgeVariants = cva(
  'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium transition-colors',
  {
    variants: {
      status: {
        pending: 'bg-status-pending-bg text-status-pending-foreground',
        uploaded: 'bg-status-pending-bg text-status-pending-foreground',
        processing: 'bg-status-processing-bg text-status-processing-foreground',
        parsed: 'bg-status-processing-bg text-status-processing-foreground',
        in_progress: 'bg-status-processing-bg text-status-processing-foreground',
        running: 'bg-status-processing-bg text-status-processing-foreground',
        completed: 'bg-status-completed-bg text-status-completed-foreground',
        committed: 'bg-status-completed-bg text-status-completed-foreground',
        approved: 'bg-status-success-bg text-status-success-foreground',
        success: 'bg-status-success-bg text-status-success-foreground',
        failed: 'bg-status-error-bg text-status-error-foreground',
        error: 'bg-status-error-bg text-status-error-foreground',
        awaiting_mapping: 'bg-status-warning-bg text-status-warning-foreground',
        mapped: 'bg-status-warning-bg text-status-warning-foreground',
        warning: 'bg-status-warning-bg text-status-warning-foreground',
      },
      size: {
        sm: 'text-xs px-2 py-0.5',
        md: 'text-xs px-2.5 py-1',
        lg: 'text-sm px-3 py-1.5',
      },
    },
    defaultVariants: {
      status: 'pending',
      size: 'md',
    },
  }
);

const statusIcons = {
  pending: Clock,
  uploaded: Clock,
  processing: Loader2,
  parsed: Loader2,
  in_progress: Loader2,
  running: Loader2,
  completed: CheckCircle2,
  committed: CheckCircle2,
  approved: CheckCircle2,
  success: CheckCircle2,
  failed: XCircle,
  error: XCircle,
  awaiting_mapping: AlertCircle,
  mapped: AlertCircle,
  warning: AlertCircle,
};

const statusLabels: Record<string, string> = {
  pending: 'Pending',
  uploaded: 'Uploaded',
  processing: 'Processing',
  parsed: 'Parsed',
  in_progress: 'In Progress',
  running: 'Running',
  completed: 'Completed',
  committed: 'Committed',
  approved: 'Approved',
  success: 'Success',
  failed: 'Failed',
  error: 'Error',
  awaiting_mapping: 'Awaiting Mapping',
  mapped: 'Mapped',
  warning: 'Warning',
};

export interface StatusBadgeProps extends VariantProps<typeof statusBadgeVariants> {
  status: keyof typeof statusIcons;
  label?: string;
  showIcon?: boolean;
  className?: string;
}

export function StatusBadge({
  status,
  label,
  showIcon = true,
  size,
  className,
}: StatusBadgeProps) {
  const Icon = statusIcons[status] || PauseCircle;
  const displayLabel = label || statusLabels[status] || status;
  const isAnimated = ['processing', 'parsed', 'in_progress', 'running'].includes(status);

  return (
    <span className={cn(statusBadgeVariants({ status, size }), className)}>
      {showIcon && (
        <Icon className={cn('h-3.5 w-3.5', isAnimated && 'animate-spin')} />
      )}
      {displayLabel}
    </span>
  );
}
