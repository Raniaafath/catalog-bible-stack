import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Plus, Target, Globe, Hash } from 'lucide-react';
import { formatDistanceToNow, differenceInSeconds, formatDuration, intervalToDuration } from 'date-fns';
import { PageHeader } from '@/components/PageHeader';
import { DataTable, Column } from '@/components/DataTable';
import { StatusBadge } from '@/components/StatusBadge';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { getPlannerRuns, PlannerRun } from '@/lib/api';

function formatRunDuration(startedAt: string | null, finishedAt: string | null): string | null {
  if (!startedAt || !finishedAt) return null;
  const secs = differenceInSeconds(new Date(finishedAt), new Date(startedAt));
  if (secs < 60) return `${secs}s`;
  return formatDuration(intervalToDuration({ start: new Date(startedAt), end: new Date(finishedAt) }), {
    format: ['minutes', 'seconds'],
    zero: false,
  });
}

export default function KeywordsList() {
  const navigate = useNavigate();

  const { data, isLoading, error } = useQuery({
    queryKey: ['planner-runs'],
    queryFn: () => getPlannerRuns({ page: 1, page_size: 50 }),
  });

  const columns: Column<PlannerRun>[] = [
    {
      key: 'product_type_code',
      header: 'Product Type',
      render: (item) => (
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-muted shrink-0">
            <Target className="w-4 h-4 text-muted-foreground" />
          </div>
          <div className="flex flex-col min-w-0">
            <span className="font-medium text-sm truncate">
              {item.product_type_code ?? <span className="text-muted-foreground italic">All types</span>}
            </span>
            <span className="text-xs text-muted-foreground font-mono">
              #{item.id}
            </span>
          </div>
        </div>
      ),
    },
    {
      key: 'locale_code',
      header: 'Locale',
      render: (item) => (
        <div className="flex flex-col gap-1">
          <Badge variant="secondary" className="w-fit font-mono uppercase text-xs">
            <Globe className="w-3 h-3 mr-1" />
            {item.locale_code}
          </Badge>
          {item.geo_target && (
            <span className="text-xs text-muted-foreground truncate max-w-[140px]" title={item.geo_target}>
              {item.geo_target}
            </span>
          )}
        </div>
      ),
    },
    {
      key: 'source_code',
      header: 'Source',
      render: (item) => (
        <Badge variant="outline" className="font-mono text-xs">
          {item.source_code}
        </Badge>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (item) => (
        <div className="flex flex-col gap-1">
          <StatusBadge status={item.status} />
          {item.status === 'success' && item.started_at && item.finished_at && (
            <span className="text-xs text-muted-foreground">
              {formatRunDuration(item.started_at, item.finished_at)}
            </span>
          )}
          {item.status === 'failed' && item.error_json && (
            <span className="text-xs text-destructive truncate max-w-[160px]" title={JSON.stringify(item.error_json)}>
              {String((item.error_json as Record<string, unknown>).detail ?? 'Error')}
            </span>
          )}
        </div>
      ),
    },
    {
      key: 'keyword_count',
      header: 'Keywords',
      render: (item) => (
        <div className="flex items-center gap-1.5">
          <Hash className="w-3.5 h-3.5 text-muted-foreground" />
          <span className="font-mono text-sm font-medium">{item.keyword_count.toLocaleString()}</span>
        </div>
      ),
    },
    {
      key: 'created_at',
      header: 'Created',
      render: (item) => (
        <span className="text-sm text-muted-foreground">
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
        emptyDescription="Start a new keyword planner run to discover search terms for your product types."
        onRowClick={(item) => navigate(`/keywords/${item.id}`)}
        sortable
      />
    </div>
  );
}
