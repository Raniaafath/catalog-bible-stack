import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Plus, Sparkles, FileText } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { PageHeader } from '@/components/PageHeader';
import { DataTable, Column } from '@/components/DataTable';
import { StatusBadge } from '@/components/StatusBadge';
import { Button } from '@/components/ui/button';
import { getGenerationBatches, GenerationBatch } from '@/lib/api';

export default function ContentList() {
  const navigate = useNavigate();

  const { data, isLoading, error } = useQuery({
    queryKey: ['generation-batches'],
    queryFn: () => getGenerationBatches({ page: 1, page_size: 50 }),
  });

  const columns: Column<GenerationBatch>[] = [
    {
      key: 'name',
      header: 'Batch Name',
      render: (item) => (
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-muted">
            <Sparkles className="w-4 h-4 text-muted-foreground" />
          </div>
          <span className="font-medium">{item.name}</span>
        </div>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (item) => <StatusBadge status={item.status as any} />,
    },
    {
      key: 'variant_count',
      header: 'Variants',
      render: (item) => (
        <span className="font-mono text-sm">{item.variant_count.toLocaleString()}</span>
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
        title="Content Generation"
        description="Generate titles and content for product variants"
        breadcrumbs={[{ label: 'Dashboard', href: '/' }, { label: 'Content' }]}
        actions={
          <Button onClick={() => navigate('/content/new')}>
            <Plus className="w-4 h-4 mr-2" />
            New Batch
          </Button>
        }
      />

      <DataTable
        columns={columns}
        data={data?.results || []}
        keyExtractor={(item) => item.id}
        isLoading={isLoading}
        error={error as Error}
        emptyTitle="No generation batches"
        emptyDescription="Create a new batch to start generating content."
        onRowClick={(item) => navigate(`/content/${item.id}`)}
        sortable
      />
    </div>
  );
}
