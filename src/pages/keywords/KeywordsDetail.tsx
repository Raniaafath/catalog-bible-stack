import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Search, Loader2, CheckCircle2, TrendingUp, BarChart3 } from 'lucide-react';
import { PageHeader } from '@/components/PageHeader';
import { StatusBadge } from '@/components/StatusBadge';
import { DataTable, Column } from '@/components/DataTable';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { getPlannerRun, getPlannerKeywords, approvePlannerRun, PlannerKeyword } from '@/lib/api';

export default function KeywordsDetail() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const runId = Number(id);

  const [selectedKeywords, setSelectedKeywords] = useState<Set<number>>(new Set());

  const { data: run, isLoading: runLoading } = useQuery({
    queryKey: ['planner-run', runId],
    queryFn: () => getPlannerRun(runId),
    enabled: !!runId,
    refetchInterval: (data) =>
      data?.state.data?.status === 'running' ? 5000 : false,
  });

  const { data: keywords, isLoading: keywordsLoading } = useQuery({
    queryKey: ['planner-keywords', runId],
    queryFn: () => getPlannerKeywords(runId),
    enabled: !!runId && run?.status !== 'running' && run?.status !== 'pending',
  });

  const approveMutation = useMutation({
    mutationFn: (ids: number[]) => approvePlannerRun(runId, ids),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['planner-run', runId] });
    },
  });

  const toggleKeyword = (id: number) => {
    const newSelected = new Set(selectedKeywords);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedKeywords(newSelected);
  };

  const selectAll = () => {
    if (keywords?.results) {
      setSelectedKeywords(new Set(keywords.results.map((k) => k.id)));
    }
  };

  const handleApprove = () => {
    approveMutation.mutate(Array.from(selectedKeywords));
  };

  const isLoading = runLoading || keywordsLoading;

  if (isLoading && !run) {
    return (
      <div className="page-container flex items-center justify-center min-h-[50vh]">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  const columns: Column<PlannerKeyword>[] = [
    {
      key: 'select',
      header: '',
      render: (item) => (
        <Checkbox
          checked={selectedKeywords.has(item.id)}
          onCheckedChange={() => toggleKeyword(item.id)}
        />
      ),
      className: 'w-12',
    },
    {
      key: 'keyword',
      header: 'Keyword',
      render: (item) => (
        <div className="flex items-center gap-3">
          <Search className="w-4 h-4 text-muted-foreground" />
          <span className="font-medium">{item.keyword}</span>
        </div>
      ),
    },
    {
      key: 'search_volume',
      header: 'Search Volume',
      render: (item) => (
        <div className="flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-muted-foreground" />
          <span className="font-mono">{item.search_volume.toLocaleString()}</span>
        </div>
      ),
    },
    {
      key: 'competition',
      header: 'Competition',
      render: (item) => {
        const colors: Record<string, string> = {
          low: 'text-status-success',
          medium: 'text-status-warning',
          high: 'text-status-error',
        };
        return (
          <span className={`font-medium capitalize ${colors[item.competition] || ''}`}>
            {item.competition}
          </span>
        );
      },
    },
    {
      key: 'approved',
      header: 'Status',
      render: (item) =>
        item.approved ? (
          <span className="flex items-center gap-1 text-status-success text-sm">
            <CheckCircle2 className="w-4 h-4" />
            Approved
          </span>
        ) : null,
    },
  ];

  return (
    <div className="page-container">
      <PageHeader
        title={`Keywords: ${run?.product_type || 'Run'}`}
        description={`Locale: ${run?.locale.toUpperCase()} • ${run?.keyword_count || 0} keywords`}
        breadcrumbs={[
          { label: 'Dashboard', href: '/' },
          { label: 'Keywords', href: '/keywords' },
          { label: run?.product_type || `Run #${id}` },
        ]}
        actions={
          run?.status === 'completed' && selectedKeywords.size > 0 && (
            <Button onClick={handleApprove} disabled={approveMutation.isPending}>
              {approveMutation.isPending ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <CheckCircle2 className="w-4 h-4 mr-2" />
              )}
              Approve {selectedKeywords.size} Keywords
            </Button>
          )
        }
      />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Status</p>
                <div className="mt-1">
                  <StatusBadge status={run?.status || 'pending'} size="lg" />
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <p className="text-sm text-muted-foreground">Keywords Found</p>
            <p className="text-2xl font-bold font-display">
              {run?.keyword_count.toLocaleString() ?? 0}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <p className="text-sm text-muted-foreground">Selected</p>
            <p className="text-2xl font-bold font-display">
              {selectedKeywords.size}
            </p>
          </CardContent>
        </Card>
      </div>

      {run?.status === 'running' && (
        <Card className="mb-6">
          <CardContent className="py-8 text-center">
            <Loader2 className="w-10 h-10 animate-spin text-primary mx-auto mb-4" />
            <p className="font-medium">Keyword research in progress...</p>
            <p className="text-sm text-muted-foreground mt-1">
              This may take a few minutes
            </p>
          </CardContent>
        </Card>
      )}

      {keywords && keywords.results.length > 0 && (
        <>
          <div className="flex justify-end mb-4">
            <Button variant="outline" size="sm" onClick={selectAll}>
              Select All
            </Button>
          </div>
          <DataTable
            columns={columns}
            data={keywords.results}
            keyExtractor={(item) => item.id}
            isLoading={keywordsLoading}
            emptyTitle="No keywords found"
            emptyDescription="The planner run didn't return any keywords."
            sortable
          />
        </>
      )}
    </div>
  );
}
