import { useQuery } from '@tanstack/react-query';
import { useNavigate, Link } from 'react-router-dom';
import { Plus, FileSpreadsheet } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { PageHeader } from '@/components/PageHeader';
import { DataTable, Column } from '@/components/DataTable';
import { StatusBadge } from '@/components/StatusBadge';
import { Button } from '@/components/ui/button';
import { getImports, Import } from '@/lib/api';

export default function ImportsList() {
  const navigate = useNavigate();

  const { data, isLoading, error } = useQuery({
    queryKey: ['imports'],
    queryFn: () => getImports({ page: 1, page_size: 50 }),
  });

  const columns: Column<Import>[] = [
    {
      key: 'original_filename',
      header: 'Filename',
      render: (item) => (
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-muted">
            <FileSpreadsheet className="w-4 h-4 text-muted-foreground" />
          </div>
          <span className="font-medium">{item.original_filename}</span>
        </div>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (item) => <StatusBadge status={item.status} />,
    },
    {
      key: 'row_count',
      header: 'Rows',
      render: (item) => (
        <span className="font-mono text-sm">{item.row_count.toLocaleString()}</span>
      ),
    },
    {
      key: 'error_count',
      header: 'Errors',
      render: (item) => (
        <span
          className={`font-mono text-sm ${
            item.error_count > 0 ? 'text-status-error font-medium' : 'text-muted-foreground'
          }`}
        >
          {item.error_count}
        </span>
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
        title="Imports"
        description="Manage product data imports from CSV and XLSX files"
        breadcrumbs={[{ label: 'Dashboard', href: '/' }, { label: 'Imports' }]}
        actions={
          <Button onClick={() => navigate('/imports/new')}>
            <Plus className="w-4 h-4 mr-2" />
            New Import
          </Button>
        }
      />

      <DataTable
        columns={columns}
        data={data?.results || []}
        keyExtractor={(item) => item.id}
        isLoading={isLoading}
        error={error as Error}
        emptyTitle="No imports yet"
        emptyDescription="Upload your first CSV or XLSX file to get started."
        onRowClick={(item) => navigate(`/imports/${item.id}`)}
        sortable
      />
    </div>
  );
}
