import { useQuery } from '@tanstack/react-query';
import { useNavigate, Link } from 'react-router-dom';
import { Plus, Languages, Globe } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { PageHeader } from '@/components/PageHeader';
import { DataTable, Column } from '@/components/DataTable';
import { StatusBadge } from '@/components/StatusBadge';
import { Button } from '@/components/ui/button';
import { getTranslationTasks, TranslationTask } from '@/lib/api';

export default function TranslationsList() {
  const navigate = useNavigate();

  const { data, isLoading, error } = useQuery({
    queryKey: ['translation-tasks'],
    queryFn: () => getTranslationTasks({ page: 1, page_size: 50 }),
  });

  const columns: Column<TranslationTask>[] = [
    {
      key: 'locale',
      header: 'Locale',
      render: (item) => (
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-muted">
            <Globe className="w-4 h-4 text-muted-foreground" />
          </div>
          <span className="font-medium uppercase">{item.locale}</span>
        </div>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (item) => <StatusBadge status={item.status} />,
    },
    {
      key: 'product_count',
      header: 'Products',
      render: (item) => (
        <span className="font-mono text-sm">{item.product_count.toLocaleString()}</span>
      ),
    },
    {
      key: 'translated_count',
      header: 'Translated',
      render: (item) => {
        const pct = item.product_count > 0 
          ? Math.round((item.translated_count / item.product_count) * 100) 
          : 0;
        return (
          <div className="flex items-center gap-2">
            <div className="w-16 h-2 bg-muted rounded-full overflow-hidden">
              <div 
                className="h-full bg-primary rounded-full transition-all"
                style={{ width: `${pct}%` }}
              />
            </div>
            <span className="text-sm text-muted-foreground">{pct}%</span>
          </div>
        );
      },
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
        title="Translations"
        description="Manage product translations across locales"
        breadcrumbs={[{ label: 'Dashboard', href: '/' }, { label: 'Translations' }]}
        actions={
          <Button onClick={() => navigate('/translations/new')}>
            <Plus className="w-4 h-4 mr-2" />
            New Task
          </Button>
        }
      />

      <DataTable
        columns={columns}
        data={data?.results || []}
        keyExtractor={(item) => item.id}
        isLoading={isLoading}
        error={error as Error}
        emptyTitle="No translation tasks"
        emptyDescription="Create a translation task to get started."
        onRowClick={(item) => navigate(`/translations/${item.id}`)}
        sortable
      />
    </div>
  );
}
