import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Plus, Search, Target } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { PageHeader } from '@/components/PageHeader';
import { DataTable, Column } from '@/components/DataTable';
import { StatusBadge } from '@/components/StatusBadge';
import { Button } from '@/components/ui/button';
import { getPlannerRuns, PlannerRun } from '@/lib/api';

export default function KeywordsList() {
  const navigate = useNavigate();

  const { data, isLoading, error } = useQuery({
    queryKey: ['planner-runs'],
    queryFn: () => getPlannerRuns({ page: 1, page_size: 50 }),
  });

  const columns: Column<PlannerRun>[] = [
    {
      key: 'product_type',
      header: 'Product Type',
      render: (item) => (
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-muted">
            <Target className="w-4 h-4 text-muted-foreground" />
          </div>
          <span className="font-medium">{item.product_type}</span>
        </div>
      ),
    },
    {
      key: 'locale',
      header: 'Locale',
      render: (item) => (
        <span className="uppercase font-mono text-sm">{item.locale}</span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (item) => <StatusBadge status={item.status} />,
    },
    {
      key: 'keyword_count',
      header: 'Keywords',
      render: (item) => (
        <span className="font-mono text-sm">{item.keyword_count.toLocaleString()}</span>
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
        title="Keyword Planner"
        description="Manage keyword research and planning runs"
        breadcrumbs={[{ label: 'Dashboard', href: '/' }, { label: 'Keywords' }]}
        actions={
          <Button onClick={() => navigate('/keywords/new')}>
            <Plus className="w-4 h-4 mr-2" />
            New Run
          </Button>
        }
      />

      <DataTable
        columns={columns}
        data={data?.results || []}
        keyExtractor={(item) => item.id}
        isLoading={isLoading}
        error={error as Error}
        emptyTitle="No keyword runs"
        emptyDescription="Start a new keyword planner run."
        onRowClick={(item) => navigate(`/keywords/${item.id}`)}
        sortable
      />
    </div>
  );
}
