import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Plus, Download, FileDown } from 'lucide-react';
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
          <span className="font-medium">{item.profile}</span>
        </div>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (item) => <StatusBadge status={item.status as any} />,
    },
    {
      key: 'file_url',
      header: 'Download',
      render: (item) =>
        item.file_url ? (
          <a
            href={item.file_url}
            download
            className="text-primary hover:underline flex items-center gap-1"
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
        <span className="text-muted-foreground">
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
          <Button onClick={() => navigate('/exports/new')}>
            <Plus className="w-4 h-4 mr-2" />
            New Export
          </Button>
        }
      />

      <DataTable
        columns={columns}
        data={data?.results || []}
        keyExtractor={(item) => item.id}
        isLoading={isLoading}
        error={error as Error}
        emptyTitle="No exports yet"
        emptyDescription="Create a new export job."
        sortable
      />
    </div>
  );
}
