import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { MapPin, Loader2, CheckCircle2, XCircle, ArrowLeft, Trash2, Filter, Info, Type, Check, X, Pencil, Save, Unlink, AlertTriangle, ChevronUp, ChevronDown, ChevronsUpDown, ChevronRight } from 'lucide-react';
import { PageHeader } from '@/components/PageHeader';
import { DataTable, Column } from '@/components/DataTable';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  getPlannerRun,
  getPlannerRunMappings,
  updatePlannerRunMapping,
  bulkUpdatePlannerRunMappings,
  persistProductKeywordMaps,
  getMappingJobStatus,
  getProductKeywordMaps,
  deleteProductKeywordMap,
  clearAllProductKeywordMaps,
  clearAllAttributeMaps,
  getSuggestedTerms,
  getHeadTerms,
  getHookTerms,
  addHeadTerm,
  addHookTerm,
  removeHeadTerm,
  removeHookTerm,
  getApiErrorMessage,
  type RunAttributeMap,
  type MappingJobStatus,
  type PersistProductKeywordMapsRequest,
  type ProductKeywordMap,
  type SuggestedTermsResponse,
  type SuggestedHeadTerm,
  type SuggestedHookTerm,
  type HeadTermItem,
  type HookTermItem,
} from '@/lib/api';
import { useToast } from '@/hooks/use-toast';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Checkbox } from '@/components/ui/checkbox';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';

type StatusFilter = 'all' | 'suggested' | 'approved' | 'rejected';
type ProductMapTab = 'attribute-maps' | 'product-maps';
type SortField = 'keyword' | 'attribute' | 'value' | 'confidence' | 'status';
type SortDir = 'asc' | 'desc';

const SOURCE_LABELS: Record<string, string> = {
  pav_text_llm: 'AI',
  enum_map: 'Rule-based',
  pav_text: 'Text match',
  pav_text_i18n: 'Text match (translated)',
  pav_numeric: 'Numeric match',
  attr_value_label: 'Attribute label',
  attr_value_code: 'Attribute code',
};

export default function KeywordsMappings() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const runId = Number(id);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [sortBy, setSortBy] = useState<SortField>('keyword');
  const [sortDir, setSortDir] = useState<SortDir>('asc');
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [mappingJob, setMappingJob] = useState<MappingJobStatus | null>(null);
  const jobPollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [page, setPage] = useState(1);
  const pageSize = 50;
  const [activeTab, setActiveTab] = useState<ProductMapTab>('product-maps');
  const [showProductMappingDialog, setShowProductMappingDialog] = useState(false);
  const [productMapsPage, setProductMapsPage] = useState(1);
  const [productMapSourceFilter, setProductMapSourceFilter] = useState<string>('all');
  const [showAdvancedDialog, setShowAdvancedDialog] = useState(false);
  const [showGuide, setShowGuide] = useState(false);
  const [productMappingOptions, setProductMappingOptions] = useState<PersistProductKeywordMapsRequest>({
    use_llm: true,
    include_descriptions: false,
    max_description_chars: 2000,
    max_text_matches: 60,
    max_enum_maps: 120,
    llm_max_keywords: 80,
    focus_on: '',
    ignore: '',
    ignore_size_and_marketplace: true,
    focus_head_terms: false,
    focus_hook_terms: false,
    skip_enum_maps: true,
  });
  const [termsProductId, setTermsProductId] = useState<string>('');
  const [maxHeadTerms, setMaxHeadTerms] = useState<number>(10);
  const [maxHookTerms, setMaxHookTerms] = useState<number>(20);
  const [suggestedTerms, setSuggestedTerms] = useState<SuggestedTermsResponse | null>(null);
  const [headRemoved, setHeadRemoved] = useState<Set<string>>(new Set());
  const [hookRemoved, setHookRemoved] = useState<Set<string>>(new Set());
  const [customHeadTerm, setCustomHeadTerm] = useState('');
  const [editingHeadKeywordId, setEditingHeadKeywordId] = useState<number | null>(null);
  const [editingHeadValue, setEditingHeadValue] = useState('');
  const [editingHookKey, setEditingHookKey] = useState<string | null>(null);
  const [editingHookValue, setEditingHookValue] = useState('');

  const { data: detailData } = useQuery({
    queryKey: ['planner-run', runId],
    queryFn: () => getPlannerRun(runId),
    enabled: !!runId,
  });

  const { data: mappingsData, isLoading: mappingsLoading } = useQuery({
    queryKey: ['planner-run-mappings', runId, page, pageSize, statusFilter, sortBy, sortDir],
    queryFn: () => getPlannerRunMappings(runId, {
      page,
      page_size: pageSize,
      ...(statusFilter !== 'all' ? { status: statusFilter } : {}),
      sort_by: sortBy,
      sort_dir: sortDir,
    }),
    enabled: !!runId,
  });

  const { data: productMapsData, isLoading: productMapsLoading } = useQuery({
    queryKey: ['planner-run-product-maps', runId, productMapsPage, pageSize, productMapSourceFilter],
    queryFn: () =>
      getProductKeywordMaps(runId, {
        page: productMapsPage,
        page_size: pageSize,
        ...(productMapSourceFilter !== 'all' ? { source: productMapSourceFilter } : {}),
      }),
    enabled: !!runId,
  });

  const runProductTypeId = (detailData as { run?: { product_type_id?: number } })?.run?.product_type_id;
  const runLocaleId = (detailData as { run?: { locale_id?: number } })?.run?.locale_id;
  const runChannelId = (detailData as { run?: { channel_id?: number } })?.run?.channel_id ?? undefined;

  const { data: savedHeadData, refetch: refetchSavedHead } = useQuery({
    queryKey: ['head-terms', runProductTypeId, runLocaleId, runChannelId],
    queryFn: () =>
      getHeadTerms(runProductTypeId!, {
        locale_id: runLocaleId!,
        channel_id: runChannelId ?? null,
      }),
    enabled: !!runProductTypeId && !!runLocaleId,
  });

  const hookProductId = termsProductId.trim() ? parseInt(termsProductId, 10) : undefined;
  const { data: savedHookData, refetch: refetchSavedHook } = useQuery({
    queryKey: ['hook-terms', hookProductId, runLocaleId, runChannelId],
    queryFn: () =>
      getHookTerms(hookProductId!, {
        locale_id: runLocaleId!,
        channel_id: runChannelId ?? null,
      }),
    enabled: !!hookProductId && !!runLocaleId && !Number.isNaN(hookProductId),
  });

  const removeHeadTermMutation = useMutation({
    mutationFn: ({ synonymId }: { synonymId: number }) => removeHeadTerm(runProductTypeId!, synonymId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['head-terms', runProductTypeId, runLocaleId, runChannelId] });
      refetchSavedHead();
    },
    onError: (err) => toast({ title: 'Failed to remove head term', description: getApiErrorMessage(err), variant: 'destructive' }),
  });

  const removeHookTermMutation = useMutation({
    mutationFn: ({ productId, hookTermId }: { productId: number; hookTermId: number }) => removeHookTerm(productId, hookTermId),
    onSuccess: (_, { productId }) => {
      queryClient.invalidateQueries({ queryKey: ['hook-terms', productId, runLocaleId, runChannelId] });
      refetchSavedHook();
    },
    onError: (err) => toast({ title: 'Failed to remove hook term', description: getApiErrorMessage(err), variant: 'destructive' }),
  });

  const suggestedTermsMutation = useMutation({
    mutationFn: (params: { product_id?: number; locale_id: number; channel_id?: number }) =>
      getSuggestedTerms(runId, params),
    onSuccess: (data) => {
      setSuggestedTerms(data);
      setHeadRemoved(new Set());
      setHookRemoved(new Set());
    },
    onError: (err) => {
      toast({ title: 'Failed to extract terms', description: getApiErrorMessage(err), variant: 'destructive' });
    },
  });

  const addHeadTermMutation = useMutation({
    mutationFn: ({ term }: { term: string }) => {
      const ptId = (detailData as { run?: { product_type_id?: number } })?.run?.product_type_id;
      if (!ptId || !suggestedTerms) throw new Error('Missing product type or terms');
      return addHeadTerm(ptId, {
        locale_id: suggestedTerms.locale_id,
        channel_id: suggestedTerms.channel_id ?? undefined,
        term,
      });
    },
    onSuccess: (_, { term }) => {
      setHeadRemoved((prev) => new Set(prev).add(term));
      queryClient.invalidateQueries({ queryKey: ['head-terms', runProductTypeId, runLocaleId, runChannelId] });
      toast({ title: 'Head term saved', description: `"${term}" added for title generation.` });
    },
    onError: (err) => {
      toast({ title: 'Failed to save head term', description: getApiErrorMessage(err), variant: 'destructive' });
    },
  });

  const addHookTermMutation = useMutation({
    mutationFn: ({ term, productId }: { term: string; productId: number }) => {
      if (!suggestedTerms) throw new Error('Extract terms first');
      return addHookTerm(productId, {
        locale_id: suggestedTerms.locale_id,
        channel_id: suggestedTerms.channel_id ?? undefined,
        term,
      });
    },
    onSuccess: (_, { term, productId, keywordId }) => {
      if (keywordId != null) setHookRemoved((prev) => new Set(prev).add(`${keywordId}-${productId}`));
      queryClient.invalidateQueries({ queryKey: ['hook-terms', productId, runLocaleId, runChannelId] });
      toast({ title: 'Hook term saved', description: `"${term}" added for this product's titles.` });
    },
    onError: (err) => {
      toast({ title: 'Failed to save hook term', description: getApiErrorMessage(err), variant: 'destructive' });
    },
  });

  const productMappingMutation = useMutation({
    mutationFn: (options: PersistProductKeywordMapsRequest) =>
      persistProductKeywordMaps(runId, { ...options, async_job: true }),
    onSuccess: (data) => {
      setShowProductMappingDialog(false);
      if (data.job_status === 'running') {
        setMappingJob({ run_id: runId, job_status: 'running' });
        setActiveTab('product-maps');
      } else {
        setActiveTab('product-maps');
        toast({
          title: 'Product mapping completed',
          description: `Processed ${data.products_processed} products. Created ${data.maps_created} new mappings, updated ${data.maps_updated}.`,
        });
        queryClient.invalidateQueries({ queryKey: ['planner-run-product-maps', runId] });
      }
    },
    onError: (error: unknown) => {
      toast({
        title: 'Product mapping failed',
        description: getApiErrorMessage(error),
        variant: 'destructive',
      });
    },
  });

  const updateStatusMutation = useMutation({
    mutationFn: ({ id: mapId, status }: { id: number; status: 'approved' | 'rejected' }) =>
      updatePlannerRunMapping(mapId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['planner-run-mappings', runId] });
    },
  });

  const bulkUpdateMutation = useMutation({
    mutationFn: (data: Parameters<typeof bulkUpdatePlannerRunMappings>[1]) =>
      bulkUpdatePlannerRunMappings(runId, data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['planner-run-mappings', runId] });
      setSelectedIds(new Set());
      toast({ title: `${data.updated} mapping(s) ${data.action}d` });
    },
    onError: (err) => toast({ title: 'Bulk update failed', description: getApiErrorMessage(err), variant: 'destructive' }),
  });

  useEffect(() => {
    if (mappingJob?.job_status === 'running') {
      if (!jobPollRef.current) {
        jobPollRef.current = setInterval(async () => {
          try {
            const s = await getMappingJobStatus(runId);
            setMappingJob(s);
            if (s.job_status !== 'running') {
              clearInterval(jobPollRef.current!);
              jobPollRef.current = null;
              queryClient.invalidateQueries({ queryKey: ['planner-run-product-maps', runId] });
              if (s.job_status === 'done' && s.result) {
                toast({
                  title: 'AI mapping completed',
                  description: `${s.result.maps_created} new maps created across ${s.result.products_processed} products.`,
                });
              } else if (s.job_status === 'error') {
                toast({ title: 'AI mapping failed', description: s.error ?? 'Unknown error', variant: 'destructive' });
              }
            }
          } catch {/* ignore poll errors */}
        }, 2500);
      }
    }
    return () => {
      if (jobPollRef.current && mappingJob?.job_status !== 'running') {
        clearInterval(jobPollRef.current);
        jobPollRef.current = null;
      }
    };
  }, [mappingJob?.job_status, runId, queryClient, toast]);

  const deleteProductMapMutation = useMutation({
    mutationFn: (mapId: number) => deleteProductKeywordMap(runId, mapId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['planner-run-product-maps', runId] });
      toast({ title: 'Mapping removed' });
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to remove mapping',
        description: error.response?.data?.detail || error.message,
        variant: 'destructive',
      });
    },
  });

  const [showClearAllDialog, setShowClearAllDialog] = useState(false);
  const [showClearAttrMapsDialog, setShowClearAttrMapsDialog] = useState(false);

  const clearAllMutation = useMutation({
    mutationFn: () => clearAllProductKeywordMaps(runId),
    onSuccess: (data) => {
      toast({ title: 'All AI maps cleared', description: `${data.deleted} mapping(s) deleted.` });
      setShowClearAllDialog(false);
      queryClient.invalidateQueries({ queryKey: ['planner-run-product-maps', runId] });
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to clear mappings',
        description: error.response?.data?.detail || error.message,
        variant: 'destructive',
      });
    },
  });

  const clearAttrMapsMutation = useMutation({
    mutationFn: () => clearAllAttributeMaps(runId),
    onSuccess: (data) => {
      toast({ title: 'Attribute maps cleared', description: `${data.deleted} mapping(s) deleted.` });
      setShowClearAttrMapsDialog(false);
      queryClient.invalidateQueries({ queryKey: ['planner-run-mappings', runId] });
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to clear attribute maps',
        description: error.response?.data?.detail || error.message,
        variant: 'destructive',
      });
    },
  });

  const results = mappingsData?.results ?? [];
  const count = mappingsData?.count ?? 0;

  const keywordAttrCount = results.reduce<Record<number, number>>((acc, m) => {
    acc[m.keyword_id] = (acc[m.keyword_id] ?? 0) + 1;
    return acc;
  }, {});
  const seenKeywordIds = new Set<number>();

  const toggleSort = (field: SortField) => {
    if (sortBy === field) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortBy(field);
      setSortDir('asc');
    }
    setPage(1);
  };
  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortBy !== field) return <ChevronsUpDown className="w-3 h-3 ml-1 text-muted-foreground/50" />;
    return sortDir === 'asc'
      ? <ChevronUp className="w-3 h-3 ml-1" />
      : <ChevronDown className="w-3 h-3 ml-1" />;
  };

  const pageIds = results.map((m) => m.id);
  const allPageSelected = pageIds.length > 0 && pageIds.every((id) => selectedIds.has(id));

  const productMapsRaw = productMapsData?.results ?? [];
  const productMapsCount = productMapsData?.count ?? 0;

  const columns: Column<RunAttributeMap>[] = [
    {
      key: 'select',
      header: (
        <Checkbox
          checked={allPageSelected}
          onCheckedChange={(checked) => {
            const next = new Set(selectedIds);
            if (checked) pageIds.forEach((id) => next.add(id));
            else pageIds.forEach((id) => next.delete(id));
            setSelectedIds(next);
          }}
        />
      ),
      render: (item) => (
        <Checkbox
          checked={selectedIds.has(item.id)}
          onCheckedChange={(checked) => {
            const next = new Set(selectedIds);
            if (checked) next.add(item.id);
            else next.delete(item.id);
            setSelectedIds(next);
          }}
        />
      ),
    },
    {
      key: 'keyword_term',
      header: (
        <button className="flex items-center text-xs font-medium" onClick={() => toggleSort('keyword')}>
          Keyword <SortIcon field="keyword" />
        </button>
      ),
      render: (item) => {
        const isFirst = !seenKeywordIds.has(item.keyword_id);
        seenKeywordIds.add(item.keyword_id);
        const attrCount = keywordAttrCount[item.keyword_id] ?? 1;
        return (
          <div className="flex items-center gap-1.5">
            <span className="font-medium">{item.keyword_term}</span>
            {isFirst && attrCount > 1 && (
              <span className="text-xs bg-muted px-1.5 py-0.5 rounded-full text-muted-foreground" title={`Maps to ${attrCount} attributes`}>
                ×{attrCount}
              </span>
            )}
          </div>
        );
      },
    },
    {
      key: 'attribute_code',
      header: (
        <button className="flex items-center text-xs font-medium" onClick={() => toggleSort('attribute')}>
          Attribute <SortIcon field="attribute" />
        </button>
      ),
      render: (item) => (
        <span className="font-mono text-sm">{item.attribute_code}</span>
      ),
    },
    {
      key: 'attribute_value_code',
      header: (
        <button className="flex items-center text-xs font-medium" onClick={() => toggleSort('value')}>
          Value <SortIcon field="value" />
        </button>
      ),
      render: (item) => (
        <span className="text-muted-foreground">
          {item.attribute_value_code ?? '—'}
        </span>
      ),
    },
    {
      key: 'confidence',
      header: (
        <button className="flex items-center text-xs font-medium" onClick={() => toggleSort('confidence')}>
          Confidence <SortIcon field="confidence" />
        </button>
      ),
      render: (item) => {
        const ev = item.evidence as Record<string, string> | null;
        const tooltipLines = ev
          ? [
              ev.matched_phrase && `Phrase: "${ev.matched_phrase}"`,
              ev.lexicon_term && `Lexicon: "${ev.lexicon_term}"`,
              ev.source && `Source: ${ev.source}`,
            ].filter(Boolean)
          : [];
        const confLabel = item.confidence != null
          ? `${(Number(item.confidence) * 100).toFixed(0)}%`
          : '—';
        if (tooltipLines.length === 0) {
          return <span className="font-mono text-sm">{confLabel}</span>;
        }
        return (
          <Popover>
            <PopoverTrigger asChild>
              <button className="flex items-center gap-1 font-mono text-sm hover:underline underline-offset-2">
                {confLabel}
                <Info className="w-3 h-3 text-muted-foreground" />
              </button>
            </PopoverTrigger>
            <PopoverContent className="text-xs w-64 space-y-1">
              {tooltipLines.map((line, i) => (
                <p key={i}>{line}</p>
              ))}
              {item.reason_code && <p className="text-muted-foreground">Rule: {item.reason_code}</p>}
            </PopoverContent>
          </Popover>
        );
      },
    },
    {
      key: 'status',
      header: (
        <button className="flex items-center text-xs font-medium" onClick={() => toggleSort('status')}>
          Status <SortIcon field="status" />
        </button>
      ),
      render: (item) => (
        <span className="capitalize text-sm">{item.status}</span>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (item) => (
        <div className="flex items-center gap-1">
          {item.status !== 'approved' && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => updateStatusMutation.mutate({ id: item.id, status: 'approved' })}
              disabled={updateStatusMutation.isPending}
              title="Approve"
            >
              <CheckCircle2 className="w-4 h-4 text-green-600" />
            </Button>
          )}
          {item.status !== 'rejected' && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => updateStatusMutation.mutate({ id: item.id, status: 'rejected' })}
              disabled={updateStatusMutation.isPending}
              title="Reject"
            >
              <XCircle className="w-4 h-4 text-red-500" />
            </Button>
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="page-container">
      <PageHeader
        title="Keyword mappings"
        description={`Run #${runId} • ${count} attribute mapping(s)`}
        breadcrumbs={[
          { label: 'Dashboard', href: '/' },
          { label: 'Keywords', href: '/keywords' },
          { label: `Run #${id}`, href: `/keywords/${runId}` },
          { label: 'Mappings' },
        ]}
        actions={
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={() => navigate(`/keywords/${runId}`)}>
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to run
            </Button>
            <Button
              onClick={() => setShowProductMappingDialog(true)}
              disabled={productMappingMutation.isPending}
            >
              {productMappingMutation.isPending
                ? <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                : <MapPin className="w-4 h-4 mr-2" />
              }
              Build product maps
            </Button>
          </div>
        }
      />

      {/* AI mapping job banner */}
      {mappingJob && (mappingJob.job_status === 'running' || mappingJob.job_status === 'error') && (
        <Alert className={`mt-4 ${mappingJob.job_status === 'error' ? 'border-red-300 bg-red-50' : 'border-blue-300 bg-blue-50'}`}>
          <AlertDescription className="flex items-center gap-2 text-sm">
            {mappingJob.job_status === 'running' && <Loader2 className="w-4 h-4 animate-spin text-blue-600" />}
            {mappingJob.job_status === 'error' && <AlertTriangle className="w-4 h-4 text-red-600" />}
            {mappingJob.job_status === 'running'
              ? 'AI mapping running in the background — results will appear automatically.'
              : `AI mapping failed: ${mappingJob.error ?? 'Unknown error'}`}
            <Button size="sm" variant="ghost" className="ml-auto h-6 px-2 text-xs" onClick={() => setMappingJob(null)}>
              Dismiss
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {/* 3-step workflow strip */}
      <div className="mt-4 mb-2 flex flex-wrap gap-0 items-center rounded-lg border bg-muted/30 px-4 py-3">
        <p className="w-full text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">Keyword mapping workflow</p>
        {([
          { step: 1, label: 'Run AI mapping', desc: 'Click "Build product maps" to let the AI link keywords to your product attributes.', tab: 'product-maps' as ProductMapTab, done: productMapsCount > 0 },
          { step: 2, label: 'Extract terms', desc: 'Click "Extract terms" to get suggested head & hook terms from the mapped keywords.', tab: 'product-maps' as ProductMapTab, done: false },
          { step: 3, label: 'Save terms', desc: 'Approve suggestions to save them for title generation.', tab: 'product-maps' as ProductMapTab, done: false },
        ] as const).map((s, i, arr) => (
          <div key={s.step} className="flex items-center">
            <div
              className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium cursor-default ${s.done ? 'bg-green-100 text-green-700' : 'text-muted-foreground'}`}
              title={s.desc}
            >
              <span className={`w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${s.done ? 'bg-green-200' : 'bg-muted'}`}>
                {s.step}
              </span>
              {s.label}
              {s.done && <CheckCircle2 className="w-3.5 h-3.5 ml-0.5 text-green-600" />}
            </div>
            {i < arr.length - 1 && <ChevronRight className="w-4 h-4 mx-1 text-muted-foreground/40 shrink-0" />}
          </div>
        ))}
      </div>

      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as ProductMapTab)} className="mt-4">
        <TabsList className="mb-4">
          <TabsTrigger value="product-maps">
            AI mapping &amp; terms {productMapsCount > 0 ? `(${productMapsCount})` : ''}
          </TabsTrigger>
          <TabsTrigger value="attribute-maps">
            Rule-based maps {count > 0 ? `(${count})` : ''}
          </TabsTrigger>
        </TabsList>

        {/* ─── Tab 1: Attribute maps ─── */}
        <TabsContent value="attribute-maps">
          <Card>
            <CardContent className="pt-4">
              <div className="flex flex-wrap items-center gap-3 mb-4">
                <Filter className="w-4 h-4 text-muted-foreground shrink-0" />
                <Select
                  value={statusFilter}
                  onValueChange={(v) => { setStatusFilter(v as StatusFilter); setPage(1); setSelectedIds(new Set()); }}
                >
                  <SelectTrigger className="w-[140px]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All</SelectItem>
                    <SelectItem value="suggested">Suggested</SelectItem>
                    <SelectItem value="approved">Approved</SelectItem>
                    <SelectItem value="rejected">Rejected</SelectItem>
                  </SelectContent>
                </Select>

                {selectedIds.size > 0 ? (
                  <>
                    <span className="text-sm text-muted-foreground">{selectedIds.size} selected</span>
                    <Button
                      size="sm" variant="outline" className="text-green-700 border-green-300"
                      disabled={bulkUpdateMutation.isPending}
                      onClick={() => bulkUpdateMutation.mutate({ action: 'approve', ids: Array.from(selectedIds) })}
                    >
                      <CheckCircle2 className="w-3.5 h-3.5 mr-1" /> Approve selected
                    </Button>
                    <Button
                      size="sm" variant="outline" className="text-red-700 border-red-300"
                      disabled={bulkUpdateMutation.isPending}
                      onClick={() => bulkUpdateMutation.mutate({ action: 'reject', ids: Array.from(selectedIds) })}
                    >
                      <XCircle className="w-3.5 h-3.5 mr-1" /> Reject selected
                    </Button>
                  </>
                ) : (
                  <>
                    <Button
                      size="sm" variant="outline" className="text-green-700 border-green-300"
                      disabled={bulkUpdateMutation.isPending || count === 0}
                      onClick={() => bulkUpdateMutation.mutate({
                        action: 'approve',
                        ...(statusFilter !== 'all' ? { status: statusFilter } : {}),
                      })}
                    >
                      <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
                      {statusFilter !== 'all' ? `Approve all ${statusFilter}` : 'Approve all'}
                    </Button>
                    <Button
                      size="sm" variant="outline" className="text-red-700 border-red-300"
                      disabled={bulkUpdateMutation.isPending || count === 0}
                      onClick={() => bulkUpdateMutation.mutate({
                        action: 'reject',
                        ...(statusFilter !== 'all' ? { status: statusFilter } : {}),
                      })}
                    >
                      <XCircle className="w-3.5 h-3.5 mr-1" />
                      {statusFilter !== 'all' ? `Reject all ${statusFilter}` : 'Reject all'}
                    </Button>
                    {count > 0 && (
                      <Button
                        size="sm" variant="outline"
                        className="text-destructive border-destructive/40 ml-auto"
                        disabled={clearAttrMapsMutation.isPending}
                        onClick={() => setShowClearAttrMapsDialog(true)}
                      >
                        <Trash2 className="w-3.5 h-3.5 mr-1" />
                        Clear all ({count})
                      </Button>
                    )}
                  </>
                )}
              </div>

              <DataTable
                columns={columns}
                data={results}
                keyExtractor={(item) => String(item.id)}
                isLoading={mappingsLoading}
                emptyTitle="No attribute maps"
                emptyDescription='These are generated by the rule-based mapper (optional). Use "AI mapping &amp; terms" tab for AI-driven results.'
              />
              {count > pageSize && (
                <div className="mt-4 flex justify-end gap-2">
                  <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => Math.max(1, p - 1))}>Previous</Button>
                  <span className="flex items-center px-2 text-sm text-muted-foreground">
                    Page {page} ({(page - 1) * pageSize + 1}–{Math.min(page * pageSize, count)} of {count})
                  </span>
                  <Button variant="outline" size="sm" disabled={page * pageSize >= count} onClick={() => setPage((p) => p + 1)}>Next</Button>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ─── Tab: AI product maps + head/hook terms ─── */}
        <TabsContent value="product-maps">

          {/* Step 1 CTA when no maps exist yet */}
          {productMapsCount === 0 && !mappingJob && (
            <div className="mb-6 rounded-lg border-2 border-dashed border-primary/30 bg-primary/5 px-6 py-5 flex flex-col sm:flex-row items-start sm:items-center gap-4">
              <div className="flex-1">
                <p className="font-semibold text-sm mb-0.5">Step 1 — Run AI mapping</p>
                <p className="text-sm text-muted-foreground">
                  Click <strong>Build product maps</strong> (top right) to let the AI match each keyword to the right product attribute. This usually takes 30–90 seconds.
                </p>
              </div>
              <Button onClick={() => setShowProductMappingDialog(true)} disabled={productMappingMutation.isPending}>
                <MapPin className="w-4 h-4 mr-2" />
                Build product maps
              </Button>
            </div>
          )}

          {/* Step 2 CTA when maps exist but no terms extracted yet */}
          {productMapsCount > 0 && !suggestedTerms && (
            <div className="mb-6 rounded-lg border bg-muted/40 px-5 py-4 flex flex-col sm:flex-row items-start sm:items-center gap-4">
              <div className="flex-1">
                <p className="font-semibold text-sm mb-0.5">Step 2 — Extract head &amp; hook terms</p>
                <p className="text-sm text-muted-foreground">
                  AI mapping done ({productMapsCount} matches). Now scroll down and click <strong>Extract terms</strong> to get suggested head &amp; hook terms for your titles.
                </p>
              </div>
              <CheckCircle2 className="w-5 h-5 text-green-600 shrink-0" />
            </div>
          )}

          {/* Head & hook terms card */}
          <Card className="mb-6">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Type className="w-5 h-5 text-muted-foreground" />
                  <h3 className="font-semibold">Head & hook terms for titles</h3>
                </div>
                <button
                  className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
                  onClick={() => setShowGuide((v) => !v)}
                >
                  {showGuide ? 'Hide guide' : 'How it works'}
                  <ChevronRight className={`w-3.5 h-3.5 transition-transform ${showGuide ? 'rotate-90' : ''}`} />
                </button>
              </div>

              {showGuide && (
                <div className="mb-5 space-y-3 p-4 rounded-lg border bg-muted/30 text-sm">
                  <div className="grid md:grid-cols-2 gap-4">
                    <div>
                      <p className="font-medium mb-1">Head terms</p>
                      <p className="text-muted-foreground text-xs">General product-type synonyms — the category word in your language (e.g. <em>Duschwanne</em>, <em>shower tray</em>). They go at the start of a generated title.</p>
                      <p className="text-xs mt-1 text-foreground/70">→ Only approve general category words. Reject colours, materials, sizes.</p>
                    </div>
                    <div>
                      <p className="font-medium mb-1">Hook terms</p>
                      <p className="text-muted-foreground text-xs">Product-specific differentiators: material, colour, shape, finish (e.g. <em>Mineralguss</em>, <em>Acryl</em>, <em>weiß</em>). Each product shows only its own hooks.</p>
                      <p className="text-xs mt-1 text-foreground/70">→ Approve terms that match this product. Deny anything that doesn't fit.</p>
                    </div>
                  </div>
                  <p className="text-xs text-muted-foreground border-t pt-3">
                    <strong>Steps:</strong> Build product maps → Extract terms → Approve/deny → saved terms feed into Content → Generate titles.
                    Sizes, warranty and stock attributes are automatically excluded.
                  </p>
                </div>
              )}

              {/* Controls */}
              <div className="flex flex-wrap items-end gap-3 mb-5">
                <div className="flex flex-col gap-1">
                  <Label className="text-xs text-muted-foreground">Product ID <span className="font-normal">(optional)</span></Label>
                  <Input
                    type="number"
                    placeholder="All products"
                    className="w-32 h-8"
                    value={termsProductId}
                    onChange={(e) => setTermsProductId(e.target.value)}
                  />
                </div>
                <div className="flex flex-col gap-1">
                  <Label className="text-xs text-muted-foreground">Max head terms</Label>
                  <Input
                    type="number" min={1} max={100} className="w-20 h-8"
                    value={maxHeadTerms}
                    onChange={(e) => setMaxHeadTerms(Math.max(1, Math.min(100, parseInt(e.target.value, 10) || 10)))}
                  />
                </div>
                <div className="flex flex-col gap-1">
                  <Label className="text-xs text-muted-foreground">Max hook terms</Label>
                  <Input
                    type="number" min={1} max={200} className="w-20 h-8"
                    value={maxHookTerms}
                    onChange={(e) => setMaxHookTerms(Math.max(1, Math.min(200, parseInt(e.target.value, 10) || 20)))}
                  />
                </div>
                <Button
                  className="h-8"
                  onClick={() => {
                    const runData = detailData as { run?: { locale_id?: number; channel_id?: number } };
                    const localeId = runData?.run?.locale_id;
                    if (localeId == null) {
                      toast({ title: 'Run has no locale', variant: 'destructive' });
                      return;
                    }
                    suggestedTermsMutation.mutate({
                      product_id: termsProductId ? Number(termsProductId) : undefined,
                      locale_id: localeId,
                      channel_id: runData?.run?.channel_id ?? undefined,
                      max_head_terms: maxHeadTerms,
                      max_hook_terms: maxHookTerms,
                      use_ai_reason: true,
                    });
                  }}
                  disabled={suggestedTermsMutation.isPending}
                >
                  {suggestedTermsMutation.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                  Extract terms
                </Button>
              </div>

              {/* Saved terms panels */}
              {(runProductTypeId && runLocaleId) && (
                <div className="grid gap-4 md:grid-cols-2 mb-5">
                  <div className="rounded-lg border bg-muted/20 p-3">
                    <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">Saved head terms</h4>
                    {savedHeadData?.terms && savedHeadData.terms.length > 0 ? (
                      <ul className="space-y-1.5 text-sm">
                        {savedHeadData.terms.map((item: HeadTermItem) => (
                          <li key={item.id ?? item.term} className="flex items-center justify-between gap-2">
                            <span className="font-medium">{item.term}</span>
                            {item.source === 'synonym' && item.id != null ? (
                              <Button
                                variant="ghost" size="sm"
                                className="h-6 w-6 p-0 text-muted-foreground hover:text-destructive"
                                title="Remove"
                                onClick={() => removeHeadTermMutation.mutate({ synonymId: item.id })}
                                disabled={removeHeadTermMutation.isPending}
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </Button>
                            ) : (
                              <span className="text-xs text-muted-foreground">label</span>
                            )}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-sm text-muted-foreground">No saved head terms yet — approve suggestions below to save.</p>
                    )}
                  </div>
                  <div className="rounded-lg border bg-muted/20 p-3">
                    <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
                      Saved hook terms {hookProductId ? `· product ${hookProductId}` : ''}
                    </h4>
                    {!hookProductId ? (
                      <p className="text-sm text-muted-foreground">Enter a product ID above to see its saved hook terms.</p>
                    ) : savedHookData?.terms && savedHookData.terms.length > 0 ? (
                      <ul className="space-y-1.5 text-sm">
                        {savedHookData.terms.map((item: HookTermItem) => (
                          <li key={item.id} className="flex items-center justify-between gap-2">
                            <span className="font-medium">{item.term}</span>
                            <Button
                              variant="ghost" size="sm"
                              className="h-6 w-6 p-0 text-muted-foreground hover:text-destructive"
                              title="Remove"
                              onClick={() => removeHookTermMutation.mutate({ productId: hookProductId, hookTermId: item.id })}
                              disabled={removeHookTermMutation.isPending}
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </Button>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-sm text-muted-foreground">No saved hook terms yet — approve suggestions below to save.</p>
                    )}
                  </div>
                </div>
              )}

              {/* Suggestions */}
              {suggestedTerms && (
                <div className="grid gap-6 md:grid-cols-2">
                  {/* Head terms */}
                  <div>
                    <h4 className="text-sm font-medium mb-0.5">
                      Head terms
                      {suggestedTerms.product_type_default_label && (
                        <span className="text-muted-foreground font-normal ml-1.5 text-xs">
                          — {suggestedTerms.product_type_default_label}
                        </span>
                      )}
                    </h4>
                    <p className="text-xs text-muted-foreground mb-3">
                      General category words only. Edit a suggestion before saving if needed.
                    </p>
                    <div className="flex gap-2 mb-3">
                      <Input
                        placeholder="Add your own head term…"
                        value={customHeadTerm}
                        onChange={(e) => setCustomHeadTerm(e.target.value)}
                        className="flex-1 text-sm h-8"
                      />
                      <Button
                        size="sm" variant="secondary" className="h-8"
                        onClick={() => {
                          const t = customHeadTerm.trim();
                          if (t) { addHeadTermMutation.mutate({ term: t }); setCustomHeadTerm(''); }
                        }}
                        disabled={addHeadTermMutation.isPending || !customHeadTerm.trim()}
                      >
                        <Save className="w-3.5 h-3.5 mr-1" /> Add
                      </Button>
                    </div>
                    <ul className="space-y-1.5 border rounded-lg p-2 max-h-72 overflow-auto bg-card">
                      {(suggestedTerms.suggested_head_terms || [])
                        .filter((h) => !headRemoved.has(h.term))
                        .map((h: SuggestedHeadTerm) => (
                          <li key={h.keyword_id} className="rounded-md bg-muted/30 px-3 py-2">
                            {editingHeadKeywordId === h.keyword_id ? (
                              <div className="flex gap-2 items-center">
                                <Input
                                  value={editingHeadValue}
                                  onChange={(e) => setEditingHeadValue(e.target.value)}
                                  className="flex-1 h-8 text-sm"
                                  placeholder="Edit term"
                                />
                                <Button size="sm" className="h-8 px-2 text-green-600" variant="ghost"
                                  onClick={() => {
                                    const t = editingHeadValue.trim();
                                    if (t) {
                                      addHeadTermMutation.mutate({ term: t });
                                      setHeadRemoved((prev) => new Set(prev).add(h.term));
                                      setEditingHeadKeywordId(null);
                                      setEditingHeadValue('');
                                    }
                                  }}
                                  disabled={addHeadTermMutation.isPending || !editingHeadValue.trim()}
                                >
                                  <Save className="w-4 h-4" />
                                </Button>
                                <Button size="sm" variant="ghost" className="h-8 px-2"
                                  onClick={() => { setEditingHeadKeywordId(null); setEditingHeadValue(''); }}
                                >
                                  Cancel
                                </Button>
                              </div>
                            ) : (
                              <div className="flex items-center justify-between gap-2">
                                <div>
                                  <div className="flex items-center gap-2">
                                    <span className="font-medium text-sm">{h.term}</span>
                                    <span className="text-xs text-muted-foreground">{h.avg_searches > 0 ? `${h.avg_searches} vol` : ''}</span>
                                  </div>
                                  {h.reason && (
                                    <p className="text-xs text-muted-foreground italic mt-0.5">{h.reason}</p>
                                  )}
                                </div>
                                <div className="flex items-center gap-0.5 shrink-0">
                                  <Button variant="ghost" size="sm" className="h-7 w-7 p-0 text-green-600 hover:text-green-700"
                                    title="Approve" onClick={() => addHeadTermMutation.mutate({ term: h.term })}
                                    disabled={addHeadTermMutation.isPending}
                                  >
                                    <Check className="w-4 h-4" />
                                  </Button>
                                  <Button variant="ghost" size="sm" className="h-7 w-7 p-0 text-muted-foreground"
                                    title="Edit before saving"
                                    onClick={() => { setEditingHeadKeywordId(h.keyword_id); setEditingHeadValue(h.term); }}
                                    disabled={addHeadTermMutation.isPending}
                                  >
                                    <Pencil className="w-3.5 h-3.5" />
                                  </Button>
                                  <Button variant="ghost" size="sm" className="h-7 w-7 p-0 text-muted-foreground"
                                    title="Dismiss"
                                    onClick={() => setHeadRemoved((prev) => new Set(prev).add(h.term))}
                                  >
                                    <X className="w-4 h-4" />
                                  </Button>
                                </div>
                              </div>
                            )}
                          </li>
                        ))}
                      {(!suggestedTerms.suggested_head_terms?.length || suggestedTerms.suggested_head_terms.every((h) => headRemoved.has(h.term))) && !customHeadTerm && (
                        <li className="text-sm text-muted-foreground py-2 px-2">No head terms found. Add your own above or run Extract terms again.</li>
                      )}
                    </ul>
                  </div>

                  {/* Hook terms */}
                  <div>
                    <h4 className="text-sm font-medium mb-0.5">Hook terms by product</h4>
                    <p className="text-xs text-muted-foreground mb-3">
                      Material, colour, shape, etc. Only keywords matched to an attribute this product actually has.
                    </p>
                    <div className="space-y-4 max-h-[560px] overflow-auto pr-1">
                      {(() => {
                        const hookTerms = (suggestedTerms.suggested_hook_terms || []).filter(
                          (h) => !hookRemoved.has(`${h.keyword_id}-${h.product_id}`)
                        );
                        const byProduct = hookTerms.reduce<Record<number, SuggestedHookTerm[]>>((acc, h) => {
                          if (!acc[h.product_id]) acc[h.product_id] = [];
                          acc[h.product_id].push(h);
                          return acc;
                        }, {});
                        const productIds = Object.keys(byProduct).map(Number).sort((a, b) => a - b);
                        const productVariants = suggestedTerms.product_variants || {};
                        if (productIds.length === 0) {
                          return (
                            <p className="text-sm text-muted-foreground py-2">
                              No hook term suggestions yet. Extract terms to see results.
                            </p>
                          );
                        }
                        return productIds.map((productId) => {
                          const terms = byProduct[productId];
                          const first = terms[0];
                          const disp = first?.product_display || {};
                          const productLabel =
                            (disp.default_label && String(disp.default_label).trim()) ||
                            (disp.variant_source_title && String(disp.variant_source_title).trim()) ||
                            `Product ${productId}`;
                          const variants = productVariants[String(productId)] || [];
                          return (
                            <div key={productId} className="border rounded-lg overflow-hidden bg-card">
                              <div className="px-4 py-2.5 bg-muted/40 border-b flex items-center justify-between">
                                <span className="font-medium text-sm">#{productId} · {productLabel}</span>
                                {variants.length > 0 && (
                                  <span className="text-xs px-2 py-0.5 rounded-full bg-background border text-muted-foreground">
                                    {variants.length} variant{variants.length !== 1 ? 's' : ''}
                                  </span>
                                )}
                              </div>
                              <div className="px-4 py-3">
                                <table className="w-full text-sm">
                                  <thead>
                                    <tr className="text-left text-xs text-muted-foreground border-b">
                                      <th className="pb-2 font-medium">Keyword</th>
                                      <th className="pb-2 font-medium w-28">Attribute</th>
                                      <th className="pb-2 font-medium w-14 text-right">Vol</th>
                                      <th className="w-20" />
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {terms.map((h: SuggestedHookTerm) => {
                                      const attrLabel = (h.attribute_label && String(h.attribute_label).trim()) || h.attribute_code || h.match_kind;
                                      const hookKey = `${h.keyword_id}-${h.product_id}`;
                                      return (
                                        <tr key={hookKey} className="border-b last:border-0 hover:bg-muted/20">
                                          {editingHookKey === hookKey ? (
                                            <>
                                              <td className="py-2 pr-3" colSpan={2}>
                                                <Input
                                                  value={editingHookValue}
                                                  onChange={(e) => setEditingHookValue(e.target.value)}
                                                  className="h-8 text-sm w-full"
                                                  placeholder="Edit hook term"
                                                />
                                              </td>
                                              <td className="py-2 text-right text-muted-foreground tabular-nums text-xs">
                                                {h.avg_searches > 0 ? h.avg_searches : '—'}
                                              </td>
                                              <td className="py-2 pl-2">
                                                <div className="flex items-center gap-0.5 justify-end">
                                                  <Button variant="ghost" size="sm" className="h-7 w-7 p-0 text-green-600 hover:text-green-700"
                                                    onClick={() => {
                                                      const t = editingHookValue.trim();
                                                      if (!t) return;
                                                      addHookTermMutation.mutate({ term: t, productId: h.product_id, keywordId: h.keyword_id });
                                                      setHookRemoved((prev) => new Set(prev).add(hookKey));
                                                      setEditingHookKey(null);
                                                      setEditingHookValue('');
                                                    }}
                                                    disabled={addHookTermMutation.isPending || !editingHookValue.trim()}
                                                    title="Save"
                                                  >
                                                    <Save className="w-4 h-4" />
                                                  </Button>
                                                  <Button variant="ghost" size="sm" className="h-7 w-7 p-0 text-muted-foreground"
                                                    onClick={() => { setEditingHookKey(null); setEditingHookValue(''); }}
                                                    title="Cancel"
                                                  >
                                                    <X className="w-4 h-4" />
                                                  </Button>
                                                </div>
                                              </td>
                                            </>
                                          ) : (
                                            <>
                                              <td className="py-2 pr-3 font-medium">{h.term}</td>
                                              <td className="py-2 pr-2">
                                                <span className="inline-block px-2 py-0.5 rounded text-xs bg-muted text-muted-foreground" title={attrLabel || undefined}>
                                                  {attrLabel}
                                                </span>
                                                {h.reason && (
                                                  <p className="text-xs text-muted-foreground mt-0.5 italic">{h.reason}</p>
                                                )}
                                              </td>
                                              <td className="py-2 text-right text-muted-foreground tabular-nums text-xs">
                                                {h.avg_searches > 0 ? h.avg_searches : '—'}
                                              </td>
                                              <td className="py-2 pl-2">
                                                <div className="flex items-center gap-0.5 justify-end">
                                                  <Button variant="ghost" size="sm" className="h-7 w-7 p-0 text-green-600 hover:text-green-700"
                                                    onClick={() => addHookTermMutation.mutate({ term: h.term, productId: h.product_id, keywordId: h.keyword_id })}
                                                    disabled={addHookTermMutation.isPending} title="Approve"
                                                  >
                                                    <Check className="w-4 h-4" />
                                                  </Button>
                                                  <Button variant="ghost" size="sm" className="h-7 w-7 p-0 text-muted-foreground"
                                                    onClick={() => { setEditingHookKey(hookKey); setEditingHookValue(h.term); }}
                                                    title="Edit before saving"
                                                  >
                                                    <Pencil className="w-3.5 h-3.5" />
                                                  </Button>
                                                  <Button variant="ghost" size="sm" className="h-7 w-7 p-0 text-muted-foreground"
                                                    onClick={() => setHookRemoved((prev) => new Set(prev).add(hookKey))}
                                                    title="Dismiss"
                                                  >
                                                    <X className="w-4 h-4" />
                                                  </Button>
                                                </div>
                                              </td>
                                            </>
                                          )}
                                        </tr>
                                      );
                                    })}
                                  </tbody>
                                </table>
                              </div>
                            </div>
                          );
                        });
                      })()}
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* AI product maps table */}
          <Card>
            <CardContent className="pt-6">
              <div className="flex flex-wrap items-center gap-3 mb-4">
                <Filter className="w-4 h-4 text-muted-foreground shrink-0" />
                <Select
                  value={productMapSourceFilter}
                  onValueChange={(v) => { setProductMapSourceFilter(v); setProductMapsPage(1); }}
                >
                  <SelectTrigger className="w-[180px]">
                    <SelectValue placeholder="All sources" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All sources</SelectItem>
                    <SelectItem value="pav_text_llm">AI matched</SelectItem>
                    <SelectItem value="enum_map">Rule-based</SelectItem>
                    <SelectItem value="pav_text">Text match</SelectItem>
                    <SelectItem value="pav_text_i18n">Text match (translated)</SelectItem>
                    <SelectItem value="attr_value_label">Attribute label</SelectItem>
                    <SelectItem value="pav_numeric">Numeric match</SelectItem>
                    <SelectItem value="attr_value_code">Attribute code</SelectItem>
                  </SelectContent>
                </Select>

                {productMapsCount > 0 && (
                  <Button
                    variant="outline" size="sm"
                    className="text-destructive border-destructive/40 ml-auto"
                    onClick={() => setShowClearAllDialog(true)}
                  >
                    <Unlink className="w-4 h-4 mr-1.5" />
                    Clear all ({productMapsCount})
                  </Button>
                )}
              </div>

              <DataTable
                columns={[
                  {
                    key: 'product_id',
                    header: 'Product',
                    render: (item: ProductKeywordMap) => (
                      <span className="font-mono text-sm text-muted-foreground">{item.product_id}</span>
                    ),
                  },
                  {
                    key: 'keyword_term',
                    header: 'Keyword',
                    render: (item: ProductKeywordMap) => (
                      <span className="font-medium text-sm">{item.keyword_term}</span>
                    ),
                  },
                  {
                    key: 'matched_to',
                    header: 'Matched to',
                    render: (item: ProductKeywordMap) => {
                      const attr = item.attribute_code || item.attribute_name;
                      const val = item.attribute_value_label || item.attribute_value_code;
                      if (!attr) return <span className="text-muted-foreground text-sm">—</span>;
                      return (
                        <span className="text-sm font-mono">
                          {attr}{val ? <span className="text-muted-foreground"> → {val}</span> : ''}
                        </span>
                      );
                    },
                  },
                  {
                    key: 'how',
                    header: 'How',
                    render: (item: ProductKeywordMap) => {
                      const label = SOURCE_LABELS[item.source] || item.source;
                      const isAI = item.source === 'pav_text_llm';
                      return (
                        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${isAI ? 'bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-300' : 'bg-muted text-muted-foreground'}`}>
                          {label}
                        </span>
                      );
                    },
                  },
                  {
                    key: 'reason',
                    header: 'Reason',
                    render: (item: ProductKeywordMap) => {
                      const ev = item.evidence && typeof item.evidence === 'object' ? item.evidence as Record<string, unknown> : {};
                      const phrase = ev.matched_phrase != null ? String(ev.matched_phrase) : item.matched_text || null;
                      const display = phrase && phrase.length > 60 ? `${phrase.slice(0, 60)}…` : phrase;
                      return (
                        <span className="text-sm text-muted-foreground italic" title={phrase || undefined}>
                          {display || '—'}
                        </span>
                      );
                    },
                  },
                  {
                    key: 'details',
                    header: '',
                    render: (item: ProductKeywordMap) => {
                      const ev = item.evidence && typeof item.evidence === 'object' ? item.evidence as Record<string, unknown> : {};
                      const model = ev.model != null ? String(ev.model) : null;
                      const variantId = ev.variant_id != null ? String(ev.variant_id) : null;
                      const created = item.created_at
                        ? new Date(item.created_at).toLocaleString(undefined, { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
                        : null;
                      return (
                        <Popover>
                          <PopoverTrigger asChild>
                            <Button variant="ghost" size="sm" className="h-7 w-7 p-0" title="Details">
                              <Info className="h-3.5 w-3.5 text-muted-foreground" />
                            </Button>
                          </PopoverTrigger>
                          <PopoverContent className="w-72" align="end">
                            <div className="space-y-1.5 text-sm">
                              <p><span className="text-muted-foreground">Source:</span> {SOURCE_LABELS[item.source] || item.source}</p>
                              {item.attribute_code && <p><span className="text-muted-foreground">Attribute:</span> <span className="font-mono">{item.attribute_code}</span></p>}
                              {(item.attribute_value_label || item.attribute_value_code) && (
                                <p><span className="text-muted-foreground">Value:</span> {item.attribute_value_label || item.attribute_value_code}</p>
                              )}
                              {item.matched_text && <p><span className="text-muted-foreground">AI reason:</span> {item.matched_text}</p>}
                              {item.confidence != null && <p><span className="text-muted-foreground">Confidence:</span> {(Number(item.confidence) * 100).toFixed(1)}%</p>}
                              {item.num_value != null && <p><span className="text-muted-foreground">Numeric:</span> {item.num_value}{item.num_unit ? ` ${item.num_unit}` : ''}</p>}
                              {model && <p><span className="text-muted-foreground">Model:</span> {model}</p>}
                              {variantId && <p><span className="text-muted-foreground">Variant:</span> {variantId}</p>}
                              {created && <p><span className="text-muted-foreground">Created:</span> {created}</p>}
                            </div>
                          </PopoverContent>
                        </Popover>
                      );
                    },
                  },
                  {
                    key: 'actions',
                    header: '',
                    render: (item: ProductKeywordMap) => (
                      <Button
                        variant="ghost" size="sm"
                        onClick={() => deleteProductMapMutation.mutate(item.id)}
                        disabled={deleteProductMapMutation.isPending}
                        className="h-7 w-7 p-0 text-muted-foreground hover:text-destructive"
                        title="Remove"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </Button>
                    ),
                  },
                ]}
                data={productMapsRaw}
                keyExtractor={(item: ProductKeywordMap) => String(item.id)}
                isLoading={productMapsLoading}
                emptyTitle="No AI product maps"
                emptyDescription='Click "Build product maps" above to run the AI mapping.'
              />

              {productMapsCount > pageSize && (
                <div className="mt-4 flex justify-end gap-2">
                  <Button variant="outline" size="sm" disabled={productMapsPage <= 1} onClick={() => setProductMapsPage((p) => Math.max(1, p - 1))}>Previous</Button>
                  <span className="flex items-center px-2 text-sm text-muted-foreground">
                    Page {productMapsPage} ({(productMapsPage - 1) * pageSize + 1}–{Math.min(productMapsPage * pageSize, productMapsCount)} of {productMapsCount})
                  </span>
                  <Button variant="outline" size="sm" disabled={productMapsPage * pageSize >= productMapsCount} onClick={() => setProductMapsPage((p) => p + 1)}>Next</Button>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* ─── Build product maps dialog ─── */}
      <Dialog open={showProductMappingDialog} onOpenChange={setShowProductMappingDialog}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Build product maps</DialogTitle>
            <DialogDescription>
              The AI reads each keyword and matches it to products based on their attributes. Results feed directly into head & hook term suggestions.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="use_llm">Use AI (recommended)</Label>
                <p className="text-xs text-muted-foreground">
                  Understands meaning across languages — e.g. "Mineralguss" → material
                </p>
              </div>
              <Switch
                id="use_llm"
                checked={productMappingOptions.use_llm || false}
                onCheckedChange={(checked) => setProductMappingOptions({ ...productMappingOptions, use_llm: checked })}
              />
            </div>

            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="skip_enum_maps">AI only — skip rule-based maps</Label>
                <p className="text-xs text-muted-foreground">
                  Gives cleaner results. Turn off only if you want to combine rule-based + AI maps.
                </p>
              </div>
              <Switch
                id="skip_enum_maps"
                checked={productMappingOptions.skip_enum_maps || false}
                onCheckedChange={(checked) => setProductMappingOptions({ ...productMappingOptions, skip_enum_maps: checked })}
              />
            </div>

            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="ignore_size">Ignore sizes & marketplace names</Label>
                <p className="text-xs text-muted-foreground">
                  Skip keywords that are only dimensions (80x90 cm) or marketplace names.
                </p>
              </div>
              <Switch
                id="ignore_size"
                checked={productMappingOptions.ignore_size_and_marketplace || false}
                onCheckedChange={(checked) => setProductMappingOptions({ ...productMappingOptions, ignore_size_and_marketplace: checked })}
              />
            </div>

            {productMappingOptions.use_llm && (
              <div className="space-y-3 rounded-lg border p-3 bg-muted/20">
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">AI instructions (optional)</p>
                <div className="space-y-1.5">
                  <Label htmlFor="focus_on" className="text-sm">Focus on</Label>
                  <Textarea
                    id="focus_on"
                    className="min-h-[50px] text-sm"
                    placeholder="e.g. material, installation, colour"
                    value={productMappingOptions.focus_on ?? ''}
                    onChange={(e) => setProductMappingOptions({ ...productMappingOptions, focus_on: e.target.value })}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="ignore" className="text-sm">Ignore</Label>
                  <Textarea
                    id="ignore"
                    className="min-h-[50px] text-sm"
                    placeholder="e.g. comparison words, connector words"
                    value={productMappingOptions.ignore ?? ''}
                    onChange={(e) => setProductMappingOptions({ ...productMappingOptions, ignore: e.target.value })}
                  />
                </div>
              </div>
            )}

            {/* Advanced */}
            <button
              className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
              onClick={() => setShowAdvancedDialog((v) => !v)}
            >
              <ChevronRight className={`w-3.5 h-3.5 transition-transform ${showAdvancedDialog ? 'rotate-90' : ''}`} />
              Advanced settings
            </button>
            {showAdvancedDialog && (
              <div className="grid grid-cols-2 gap-3 pt-1">
                <div className="space-y-1.5">
                  <Label className="text-xs">AI max keywords per product</Label>
                  <Input type="number" value={productMappingOptions.llm_max_keywords || 80}
                    onChange={(e) => setProductMappingOptions({ ...productMappingOptions, llm_max_keywords: parseInt(e.target.value) })}
                    disabled={!productMappingOptions.use_llm} className="h-8" />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs">Max text matches per product</Label>
                  <Input type="number" value={productMappingOptions.max_text_matches || 60}
                    onChange={(e) => setProductMappingOptions({ ...productMappingOptions, max_text_matches: parseInt(e.target.value) })}
                    className="h-8" />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs">Limit products (blank = all)</Label>
                  <Input type="number" placeholder="All" value={productMappingOptions.limit || ''}
                    onChange={(e) => setProductMappingOptions({ ...productMappingOptions, limit: e.target.value ? parseInt(e.target.value) : undefined })}
                    className="h-8" />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs">Product ID (blank = all)</Label>
                  <Input type="number" placeholder="All" value={productMappingOptions.product_id || ''}
                    onChange={(e) => setProductMappingOptions({ ...productMappingOptions, product_id: e.target.value ? parseInt(e.target.value) : undefined })}
                    className="h-8" />
                </div>
                <div className="col-span-2 flex items-center gap-2">
                  <Switch
                    id="include_descriptions"
                    checked={productMappingOptions.include_descriptions || false}
                    onCheckedChange={(checked) => setProductMappingOptions({ ...productMappingOptions, include_descriptions: checked })}
                  />
                  <Label htmlFor="include_descriptions" className="text-xs">Include product descriptions in matching</Label>
                </div>
              </div>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowProductMappingDialog(false)}>Cancel</Button>
            <Button onClick={() => productMappingMutation.mutate(productMappingOptions)} disabled={productMappingMutation.isPending}>
              {productMappingMutation.isPending ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Running…</> : 'Run mapping'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Clear all AI maps dialog */}
      <Dialog open={showClearAllDialog} onOpenChange={setShowClearAllDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-destructive">
              <Unlink className="w-5 h-5" /> Clear all AI product maps
            </DialogTitle>
            <DialogDescription>
              This will permanently delete all {productMapsCount} product map(s). Re-run "Build product maps" to recreate them.
            </DialogDescription>
          </DialogHeader>
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>
              <strong>{productMapsCount} map{productMapsCount !== 1 ? 's' : ''}</strong> will be deleted. This cannot be undone.
            </AlertDescription>
          </Alert>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowClearAllDialog(false)} disabled={clearAllMutation.isPending}>Cancel</Button>
            <Button variant="destructive" onClick={() => clearAllMutation.mutate()} disabled={clearAllMutation.isPending}>
              {clearAllMutation.isPending ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Unlink className="w-4 h-4 mr-2" />}
              Delete all {productMapsCount}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Clear all attribute maps dialog */}
      <Dialog open={showClearAttrMapsDialog} onOpenChange={setShowClearAttrMapsDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-destructive">
              <Trash2 className="w-5 h-5" /> Clear all attribute maps
            </DialogTitle>
            <DialogDescription>
              This will permanently delete all {count} attribute mapping(s). Re-run "Map keywords" to recreate them.
            </DialogDescription>
          </DialogHeader>
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>
              <strong>{count} mapping{count !== 1 ? 's' : ''}</strong> will be deleted. This cannot be undone.
            </AlertDescription>
          </Alert>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowClearAttrMapsDialog(false)} disabled={clearAttrMapsMutation.isPending}>Cancel</Button>
            <Button variant="destructive" onClick={() => clearAttrMapsMutation.mutate()} disabled={clearAttrMapsMutation.isPending}>
              {clearAttrMapsMutation.isPending ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Trash2 className="w-4 h-4 mr-2" />}
              Delete all {count}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
