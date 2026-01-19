import { ReactNode, useState } from 'react';
import { cn } from '@/lib/utils';
import { ChevronUp, ChevronDown, ChevronsUpDown, Inbox, AlertCircle, Loader2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export interface Column<T> {
  key: string;
  header: string;
  render?: (item: T, index: number) => ReactNode;
  sortable?: boolean;
  className?: string;
  headerClassName?: string;
}

export interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  keyExtractor: (item: T) => string | number;
  isLoading?: boolean;
  error?: Error | null;
  emptyTitle?: string;
  emptyDescription?: string;
  onRowClick?: (item: T) => void;
  sortable?: boolean;
  className?: string;
}

type SortDirection = 'asc' | 'desc' | null;

export function DataTable<T>({
  columns,
  data,
  keyExtractor,
  isLoading = false,
  error = null,
  emptyTitle = 'No data',
  emptyDescription = 'There are no items to display.',
  onRowClick,
  sortable = false,
  className,
}: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>(null);

  const handleSort = (key: string) => {
    if (!sortable) return;
    if (sortKey === key) {
      if (sortDirection === 'asc') {
        setSortDirection('desc');
      } else if (sortDirection === 'desc') {
        setSortKey(null);
        setSortDirection(null);
      } else {
        setSortDirection('asc');
      }
    } else {
      setSortKey(key);
      setSortDirection('asc');
    }
  };

  const sortedData = [...data].sort((a, b) => {
    if (!sortKey || !sortDirection) return 0;
    const aVal = (a as Record<string, unknown>)[sortKey];
    const bVal = (b as Record<string, unknown>)[sortKey];
    if (aVal === bVal) return 0;
    if (aVal === null || aVal === undefined) return 1;
    if (bVal === null || bVal === undefined) return -1;
    const comparison = aVal < bVal ? -1 : 1;
    return sortDirection === 'asc' ? comparison : -comparison;
  });

  const SortIcon = ({ columnKey }: { columnKey: string }) => {
    if (sortKey !== columnKey) return <ChevronsUpDown className="h-4 w-4 text-muted-foreground/50" />;
    if (sortDirection === 'asc') return <ChevronUp className="h-4 w-4" />;
    if (sortDirection === 'desc') return <ChevronDown className="h-4 w-4" />;
    return <ChevronsUpDown className="h-4 w-4 text-muted-foreground/50" />;
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-16">
        <Loader2 className="h-8 w-8 animate-spin text-primary mb-4" />
        <p className="text-sm text-muted-foreground">Loading data...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <AlertCircle className="h-12 w-12 text-status-error mb-4" />
        <h3 className="text-lg font-medium text-foreground mb-1 font-display">Error loading data</h3>
        <p className="text-sm text-muted-foreground max-w-md">{error.message}</p>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="empty-state">
        <Inbox className="empty-state-icon" />
        <h3 className="empty-state-title">{emptyTitle}</h3>
        <p className="empty-state-description">{emptyDescription}</p>
      </div>
    );
  }

  return (
    <div className={cn('overflow-x-auto rounded-lg border border-border', className)}>
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((column) => (
              <th
                key={column.key}
                className={cn(
                  column.headerClassName,
                  (sortable || column.sortable) && 'cursor-pointer select-none hover:bg-muted'
                )}
                onClick={() => (sortable || column.sortable) && handleSort(column.key)}
              >
                <div className="flex items-center gap-2">
                  {column.header}
                  {(sortable || column.sortable) && <SortIcon columnKey={column.key} />}
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          <AnimatePresence>
            {sortedData.map((item, index) => (
              <motion.tr
                key={keyExtractor(item)}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ delay: index * 0.02, duration: 0.2 }}
                onClick={() => onRowClick?.(item)}
                className={cn(onRowClick && 'cursor-pointer')}
              >
                {columns.map((column) => (
                  <td key={column.key} className={column.className}>
                    {column.render
                      ? column.render(item, index)
                      : String(item[column.key] ?? '')}
                  </td>
                ))}
              </motion.tr>
            ))}
          </AnimatePresence>
        </tbody>
      </table>
    </div>
  );
}
