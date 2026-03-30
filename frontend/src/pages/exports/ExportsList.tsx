import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Plus, Download, FileDown, AlertCircle, FileText } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { PageHeader } from '@/components/PageHeader';
import { DataTable, Column } from '@/components/DataTable';
import { StatusBadge } from '@/components/StatusBadge';
import { Button } from '@/components/ui/button';
import { getExportJobs, ExportJob } from '@/lib/api';

export default function ExportsList() {
  const navigate = useNavigate();

  const { data, isLoading, error } = useQuery({
    queryKey: ['export-jobs'],
    queryFn: () => getExportJobs({ page: 1, page_size: 50 }),
  });

  const columns: Column<ExportJob>[] = [
    {
      key: 'profile',
      header: 'Profile',
      render: (item) => (
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-muted">
            <FileDown className="w-4 h-4 text-muted-foreground" />
          </div>
          <div>
            <span className="font-medium">{item.profile || `Profile #${item.profile_id}`}</span>
            {item.batch_id && (
              <p className="text-xs text-muted-foreground">Batch #{item.batch_id}</p>
            )}
          </div>
        </div>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (item) => (
        <div className="flex flex-col gap-1">
          <StatusBadge status={item.status as any} />
          {item.status === 'failed' && item.error_message && (
            <div className="flex items-center gap-1 text-xs text-destructive">
              <AlertCircle className="w-3 h-3" />
              <span className="truncate max-w-[200px]">{item.error_message}</span>
            </div>
          )}
        </div>
      ),
    },
    {
      key: 'stats_json',
      header: 'Rows',
      render: (item) =>
        item.stats_json?.rows != null ? (
          <div className="text-sm font-mono">
            <span>{item.stats_json.rows.toLocaleString()} rows</span>
            {(item.stats_json.errors ?? 0) > 0 && (
              <span className="ml-2 text-status-error">
                {item.stats_json.errors} errors
              </span>
            )}
          </div>
        ) : (
          <span className="text-muted-foreground text-sm">—</span>
        ),
    },
    {
      key: 'file_url',
      header: 'Download',
      render: (item) =>
        item.file_url ? (
          <a
            href={item.file_url}
            download
            className="inline-flex items-center gap-1.5 text-sm text-primary hover:underline font-medium"
            onClick={(e) => e.stopPropagation()}
          >
            <Download className="w-4 h-4" />
            Download
          </a>
        ) : (
          <span className="text-muted-foreground text-sm">—</span>
        ),
    },
    {
      key: 'created_at',
      header: 'Created',
      render: (item) => (
        <span className="text-muted-foreground text-sm">
          {formatDistanceToNow(new Date(item.created_at), { addSuffix: true })}
        </span>
      ),
    },
  ];

  return (
    <div className="page-container">
      <PageHeader
        title="Exports"
        description="Manage product data exports"
        breadcrumbs={[{ label: 'Dashboard', href: '/' }, { label: 'Exports' }]}
        actions={
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => navigate('/exports/csv')}>
              <FileText className="w-4 h-4 mr-2" />
              Export CSV
            </Button>
            <Button onClick={() => navigate('/exports/new')}>
              <Plus className="w-4 h-4 mr-2" />
              New Export
            </Button>
          </div>
        }
      />

      <DataTable
        columns={columns}
        data={data?.results || []}
        keyExtractor={(item) => item.id}
        isLoading={isLoading}
        error={error as Error}
        emptyTitle="No exports yet"
        emptyDescription="Create a new export job to download your product data."
        sortable
      />
    </div>
  );
}
