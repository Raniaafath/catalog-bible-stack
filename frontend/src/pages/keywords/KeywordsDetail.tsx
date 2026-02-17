import { useState, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Search, Loader2, CheckCircle2, TrendingUp, MapPin } from 'lucide-react';
import { PageHeader } from '@/components/PageHeader';
import { StatusBadge } from '@/components/StatusBadge';
import { DataTable, Column } from '@/components/DataTable';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { getPlannerRun, approvePlannerRun, mapPlannerRunKeywords, PlannerKeyword } from '@/lib/api';

type KeywordSortOrder = 'default' | 'volume_desc' | 'volume_asc';

export default function KeywordsDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const runId = Number(id);

  const [selectedKeywords, setSelectedKeywords] = useState<Set<number>>(new Set());
  const [sortOrder, setSortOrder] = useState<KeywordSortOrder>('default');

  const { data: detailData, isLoading: runLoading } = useQuery({
    queryKey: ['planner-run', runId],
    queryFn: () => getPlannerRun(runId),
    enabled: !!runId,
    refetchInterval: (query) =>
      (query?.state?.data as { run?: { status?: string } })?.run?.status === 'running' ? 5000 : false,
  });

  const run = (detailData as { run?: { status?: string; locale_code?: string; locale?: string; keyword_count?: number; product_type_id?: number } })?.run;
  const keywordsList = (detailData as { keywords?: unknown[] })?.keywords ?? [];
  const keywordsLoading = false;

  const displayedKeywords = useMemo(() => {
    const list = [...(keywordsList as PlannerKeyword[])];
    if (sortOrder === 'default') return list;
    const vol = (item: PlannerKeyword) => item.search_volume ?? item.avg_searches ?? 0;
    if (sortOrder === 'volume_desc') return list.sort((a, b) => vol(b) - vol(a));
    return list.sort((a, b) => vol(a) - vol(b));
  }, [keywordsList, sortOrder]);

  const approveMutation = useMutation({
    mutationFn: (ids: number[]) => approvePlannerRun(runId, ids),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['planner-run', runId] });
    },
  });

  const mapMutation = useMutation({
    mutationFn: () => mapPlannerRunKeywords(runId),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['planner-run', runId] });
      queryClient.invalidateQueries({ queryKey: ['planner-run-mappings', runId] });
      if (data.mapped > 0) navigate(`/keywords/${runId}/mappings`);
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
    if (displayedKeywords.length > 0) {
      setSelectedKeywords(new Set(displayedKeywords.map((k) => k.id)));
    }
  };

  const handleApprove = () => {
    approveMutation.mutate(Array.from(selectedKeywords));
  };

  const isLoading = runLoading;

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
          <span className="font-mono">{(item.search_volume ?? 0).toLocaleString()}</span>
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
        description={`Locale: ${(run?.locale_code ?? run?.locale ?? '').toUpperCase()} • ${run?.keyword_count ?? 0} keywords`}
        breadcrumbs={[
          { label: 'Dashboard', href: '/' },
          { label: 'Keywords', href: '/keywords' },
          { label: run?.product_type_id ? `Run #${id}` : `Run #${id}` },
        ]}
        actions={
          <div className="flex items-center gap-2">
            {keywordsList.length > 0 && (
              <Button
                variant="outline"
                onClick={() => mapMutation.mutate()}
                disabled={mapMutation.isPending}
              >
                {mapMutation.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                <MapPin className="w-4 h-4 mr-2" />
                Map keywords
              </Button>
            )}
            <Button
              variant="outline"
              onClick={() => navigate(`/keywords/${runId}/mappings`)}
            >
              View mappings
            </Button>
            {(run?.status === 'success' || run?.status === 'completed') && selectedKeywords.size > 0 && (
              <Button onClick={handleApprove} disabled={approveMutation.isPending}>
                {approveMutation.isPending ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <CheckCircle2 className="w-4 h-4 mr-2" />
                )}
                Approve {selectedKeywords.size} Keywords
              </Button>
            )}
          </div>
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
              {(run?.keyword_count ?? 0).toLocaleString()}
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

      {keywordsList.length > 0 && (
        <>
          <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
            <div className="flex items-center gap-2">
              <Label htmlFor="keyword-sort" className="text-sm whitespace-nowrap">Order by</Label>
              <Select value={sortOrder} onValueChange={(v) => setSortOrder(v as KeywordSortOrder)}>
                <SelectTrigger id="keyword-sort" className="w-[220px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="default">Default</SelectItem>
                  <SelectItem value="volume_desc">Searches/month (high first)</SelectItem>
                  <SelectItem value="volume_asc">Searches/month (low first)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <Button variant="outline" size="sm" onClick={selectAll}>
              Select All
            </Button>
          </div>
          <DataTable
            columns={columns}
            data={displayedKeywords}
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
