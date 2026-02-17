import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { MapPin, Loader2, CheckCircle2, XCircle, Upload, ArrowLeft, Trash2, Filter, Info, Type, Check, X, Pencil, Save } from 'lucide-react';
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
  persistPlannerRunMappings,
  persistProductKeywordMaps,
  getProductKeywordMaps,
  deleteProductKeywordMap,
  getSuggestedTerms,
  getHeadTerms,
  getHookTerms,
  addHeadTerm,
  addHookTerm,
  removeHeadTerm,
  removeHookTerm,
  getApiErrorMessage,
  type RunAttributeMap,
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
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Checkbox } from '@/components/ui/checkbox';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';

type StatusFilter = 'all' | 'suggested' | 'approved' | 'rejected';
type ProductMapTab = 'attribute-maps' | 'product-maps';
type DetectedFilter = 'all' | 'size' | 'marketplace' | 'other';

/** Detect if keyword term looks like size or marketplace (for filtering/organizing). */
function detectKeywordSignal(term: string): 'size' | 'marketplace' | null {
  if (!term || typeof term !== 'string') return null;
  const t = term.toLowerCase().trim();
  const sizePattern = /\b(xxs?|s|m|l|xl|xxl|xxxl)\b|\d+\s*(cm|mm|m|in|inch|ft)\b|\d+x\d+/i;
  if (sizePattern.test(t)) return 'size';
  const marketplaces = ['amazon', 'ebay', 'alibaba', 'walmart', 'etsy', 'aliexpress', 'wish', 'target', 'best buy', 'newegg', 'aliexpress'];
  if (marketplaces.some((m) => t.includes(m))) return 'marketplace';
  return null;
}

export default function KeywordsMappings() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const runId = Number(id);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [page, setPage] = useState(1);
  const pageSize = 50;
  const [activeTab, setActiveTab] = useState<ProductMapTab>('attribute-maps');
  const [showProductMappingDialog, setShowProductMappingDialog] = useState(false);
  const [productMapsPage, setProductMapsPage] = useState(1);
  const [productMapSourceFilter, setProductMapSourceFilter] = useState<string>('all');
  const [productMapDetectedFilter, setProductMapDetectedFilter] = useState<DetectedFilter>('all');
  const [showMoreDetails, setShowMoreDetails] = useState(false);
  const [productMappingOptions, setProductMappingOptions] = useState<PersistProductKeywordMapsRequest>({
    use_llm: false,
    include_descriptions: false,
    max_description_chars: 2000,
    max_text_matches: 60,
    max_enum_maps: 120,
    llm_max_keywords: 80,
    focus_on: '',
    ignore: '',
    ignore_size_and_marketplace: false,
    focus_head_terms: false,
    focus_hook_terms: false,
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
  const [useAiMeaning, setUseAiMeaning] = useState(false);

  const { data: detailData } = useQuery({
    queryKey: ['planner-run', runId],
    queryFn: () => getPlannerRun(runId),
    enabled: !!runId,
  });
  const run = (detailData as { run?: { keyword_count?: number } })?.run;

  const { data: mappingsData, isLoading: mappingsLoading } = useQuery({
    queryKey: ['planner-run-mappings', runId, page, pageSize],
    queryFn: () => getPlannerRunMappings(runId, { page, page_size: pageSize }),
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

  const persistMutation = useMutation({
    mutationFn: () => persistPlannerRunMappings(runId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['planner-run-mappings', runId] });
    },
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
      persistProductKeywordMaps(runId, options),
    onSuccess: (data) => {
      setShowProductMappingDialog(false);
      setActiveTab('product-maps');
      toast({
        title: 'Product mapping completed',
        description: `Processed ${data.products_processed} products. Created ${data.maps_created} new mappings, updated ${data.maps_updated}.`,
      });
      queryClient.invalidateQueries({ queryKey: ['planner-run-mappings', runId] });
      queryClient.invalidateQueries({ queryKey: ['planner-run-product-maps', runId] });
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

  const results = mappingsData?.results ?? [];
  const filtered =
    statusFilter === 'all'
      ? results
      : results.filter((m) => m.status === statusFilter);
  const count = mappingsData?.count ?? 0;

  const productMapsRaw = productMapsData?.results ?? [];
  const productMapsFiltered =
    productMapDetectedFilter === 'all'
      ? productMapsRaw
      : productMapsRaw.filter((m) => {
          const sig = detectKeywordSignal(m.keyword_term);
          if (productMapDetectedFilter === 'size') return sig === 'size';
          if (productMapDetectedFilter === 'marketplace') return sig === 'marketplace';
          return sig === null;
        });
  const productMapsCount = productMapsData?.count ?? 0;

  const columns: Column<RunAttributeMap>[] = [
    {
      key: 'keyword_term',
      header: 'Keyword',
      render: (item) => (
        <span className="font-medium">{item.keyword_term}</span>
      ),
    },
    {
      key: 'attribute_code',
      header: 'Attribute',
      render: (item) => (
        <span className="font-mono text-sm">{item.attribute_code}</span>
      ),
    },
    {
      key: 'attribute_value_code',
      header: 'Value',
      render: (item) => (
        <span className="text-muted-foreground">
          {item.attribute_value_code ?? '—'}
        </span>
      ),
    },
    {
      key: 'confidence',
      header: 'Confidence',
      render: (item) =>
        item.confidence != null ? (
          <span className="font-mono text-sm">
            {(Number(item.confidence) * 100).toFixed(0)}%
          </span>
        ) : (
          '—'
        ),
    },
    {
      key: 'status',
      header: 'Status',
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
              onClick={() =>
                updateStatusMutation.mutate({ id: item.id, status: 'approved' })
              }
              disabled={updateStatusMutation.isPending}
            >
              <CheckCircle2 className="w-4 h-4 text-status-success" />
            </Button>
          )}
          {item.status !== 'rejected' && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() =>
                updateStatusMutation.mutate({ id: item.id, status: 'rejected' })
              }
              disabled={updateStatusMutation.isPending}
            >
              <XCircle className="w-4 h-4 text-status-error" />
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
        description={`Run #${runId} • ${count} mapping(s)`}
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
              onClick={() => persistMutation.mutate()}
              disabled={persistMutation.isPending || count === 0}
            >
              {persistMutation.isPending && (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              )}
              <Upload className="w-4 h-4 mr-2" />
              Apply to products
            </Button>
            <Button
              onClick={() => setShowProductMappingDialog(true)}
              disabled={productMappingMutation.isPending}
              variant="secondary"
            >
              {productMappingMutation.isPending && (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              )}
              <MapPin className="w-4 h-4 mr-2" />
              Map to Products (AI)
            </Button>
          </div>
        }
      />

      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as ProductMapTab)} className="mt-4">
        <TabsList className="mb-4">
          <TabsTrigger value="attribute-maps">
            Attribute mappings ({count})
          </TabsTrigger>
          <TabsTrigger value="product-maps">
            Product maps / AI ({productMapsCount})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="attribute-maps">
          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-4 mb-4">
                <Filter className="w-4 h-4 text-muted-foreground" />
                <label className="text-sm font-medium">Filter by status</label>
                <Select
                  value={statusFilter}
                  onValueChange={(v) => setStatusFilter(v as StatusFilter)}
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
              </div>
              <DataTable
                columns={columns}
                data={filtered}
                keyExtractor={(item) => String(item.id)}
                isLoading={mappingsLoading}
                emptyTitle="No mappings"
                emptyDescription={
                  count === 0
                    ? 'Run "Map keywords" on the run detail page to generate mappings.'
                    : `No mappings with status "${statusFilter}".`
                }
              />
              {count > pageSize && (
                <div className="mt-4 flex justify-end gap-2">
                  <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => Math.max(1, p - 1))}>
                    Previous
                  </Button>
                  <span className="flex items-center px-2 text-sm text-muted-foreground">
                    Page {page} ({(page - 1) * pageSize + 1}–{Math.min(page * pageSize, count)} of {count})
                  </span>
                  <Button variant="outline" size="sm" disabled={page * pageSize >= count} onClick={() => setPage((p) => p + 1)}>
                    Next
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="product-maps">
          <Card className="mb-6">
            <CardContent className="pt-6">
              <div className="flex items-center gap-2 mb-4">
                <Type className="w-5 h-5 text-muted-foreground" />
                <h3 className="font-semibold">Head & hook terms for titles</h3>
              </div>
              <div className="rounded-md border bg-muted/40 p-4 mb-4 space-y-3 text-sm text-muted-foreground">
                <p className="font-medium text-foreground">What are head terms and hook terms?</p>
                <p className="text-xs text-muted-foreground italic">
                  Same rules in every language: head = general product type; hook = product-specific (e.g. colour, material). Terms are in your run&apos;s locale.
                </p>
                <ul className="space-y-3 list-none pl-0">
                  <li>
                    <strong className="text-foreground">Head terms</strong> — General product-type synonyms only (category words in your language). They appear at the start of a generated title. Do not use colours, materials, sizes, or other variant attributes here; those belong in hook terms.
                    <br />
                    <span className="text-xs mt-1 inline-block">→ Approve only general category terms. Deny any term that looks like a colour, material, shape, or size—in any language.</span>
                  </li>
                  <li>
                    <strong className="text-foreground">Hook terms</strong> — Product-specific words: shape, material, colour, finish, etc. (in your locale). Each product (variant group) has its own hook terms. Terms are matched to your product attributes so only relevant suggestions are shown.
                    <br />
                    <span className="text-xs mt-1 inline-block">→ Approve only terms that match this product; deny terms that don&apos;t fit (e.g. wrong colour or material).</span>
                  </li>
                </ul>
                <p className="pt-1 border-t mt-3">
                  Suggestions come from your keyword mappings and search volume. Choose how many terms to extract, then use the green check to approve and save a term for title generation, or the X to skip it.
                </p>
                <p className="text-xs border-t pt-3 mt-3 text-foreground/90">
                  <strong>Where to find saved terms:</strong> Open <strong>Keywords → Saved terms</strong> to see all head and hook terms by language and marketplace. You can also view and remove them below; hook terms appear on each product page (Products → product → Saved hook terms).
                </p>
              </div>
                <div className="flex flex-wrap items-center gap-4 mb-4">
                <div className="flex items-center gap-2">
                  <Checkbox
                    id="use-ai-meaning"
                    checked={useAiMeaning}
                    onCheckedChange={(c) => setUseAiMeaning(!!c)}
                  />
                  <Label htmlFor="use-ai-meaning" className="text-sm cursor-pointer">
                    Generate English meanings (AI)
                  </Label>
                </div>
                <div className="flex items-center gap-2">
                  <Label className="text-sm whitespace-nowrap">Max head terms</Label>
                  <Input
                    type="number"
                    min={1}
                    max={100}
                    className="w-20"
                    value={maxHeadTerms}
                    onChange={(e) => setMaxHeadTerms(Math.max(1, Math.min(100, parseInt(e.target.value, 10) || 10)))}
                  />
                </div>
                <div className="flex items-center gap-2">
                  <Label className="text-sm whitespace-nowrap">Max hook terms</Label>
                  <Input
                    type="number"
                    min={1}
                    max={200}
                    className="w-20"
                    value={maxHookTerms}
                    onChange={(e) => setMaxHookTerms(Math.max(1, Math.min(200, parseInt(e.target.value, 10) || 20)))}
                  />
                </div>
                <div className="flex items-center gap-2">
                  <Label className="text-sm whitespace-nowrap">Product (optional)</Label>
                  <Input
                    type="number"
                    placeholder="All products"
                    className="w-28"
                    value={termsProductId}
                    onChange={(e) => setTermsProductId(e.target.value)}
                  />
                </div>
                <Button
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
                      use_ai_meaning: useAiMeaning,
                    });
                  }}
                  disabled={suggestedTermsMutation.isPending}
                >
                  {suggestedTermsMutation.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                  Extract terms
                </Button>
              </div>

              {/* Saved terms: where to find head/hook terms after saving */}
              {(runProductTypeId && runLocaleId) && (
                <div className="grid gap-4 md:grid-cols-2 mb-4">
                  <div className="rounded-md border bg-muted/30 p-3">
                    <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
                      Saved head terms (product type)
                    </h4>
                    {savedHeadData?.terms && savedHeadData.terms.length > 0 ? (
                      <ul className="space-y-1.5 text-sm">
                        {savedHeadData.terms.map((item: HeadTermItem) => (
                          <li key={item.id ?? item.term} className="flex items-center justify-between gap-2">
                            <span className="font-medium">{item.term}</span>
                            {item.source === 'synonym' && item.id != null ? (
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-6 w-6 p-0 text-muted-foreground hover:text-destructive"
                                title="Remove head term"
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
                      <p className="text-sm text-muted-foreground">No saved head terms for this product type and locale yet. Approve terms above to save.</p>
                    )}
                  </div>
                  <div className="rounded-md border bg-muted/30 p-3">
                    <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
                      Saved hook terms {hookProductId ? `(product ${hookProductId})` : ''}
                    </h4>
                    {!hookProductId ? (
                      <p className="text-sm text-muted-foreground">Enter a product ID above and click Extract terms (or open Products → product) to see saved hook terms.</p>
                    ) : savedHookData?.terms && savedHookData.terms.length > 0 ? (
                      <ul className="space-y-1.5 text-sm">
                        {savedHookData.terms.map((item: HookTermItem) => (
                          <li key={item.id} className="flex items-center justify-between gap-2">
                            <span className="font-medium">{item.term}</span>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-6 w-6 p-0 text-muted-foreground hover:text-destructive"
                              title="Remove hook term"
                              onClick={() => removeHookTermMutation.mutate({ productId: hookProductId, hookTermId: item.id })}
                              disabled={removeHookTermMutation.isPending}
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </Button>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-sm text-muted-foreground">No saved hook terms for this product and locale yet. Approve terms below to save.</p>
                    )}
                  </div>
                </div>
              )}

              {suggestedTerms && (
                <div className="grid gap-6 md:grid-cols-2">
                  <div>
                    <h4 className="text-sm font-medium mb-1">
                      Head terms · product type{suggestedTerms.product_type_code ? ` ${suggestedTerms.product_type_code}` : ''}
                      {(suggestedTerms.product_type_default_label || suggestedTerms.product_type_main_category) && (
                        <span className="text-muted-foreground font-normal ml-1">
                          — {[suggestedTerms.product_type_default_label, suggestedTerms.product_type_main_category].filter(Boolean).join(' · ')}
                        </span>
                      )}
                    </h4>
                    {suggestedTerms.product_type_notes && (
                      <p className="text-xs text-muted-foreground mb-2 italic max-w-xl">
                        {suggestedTerms.product_type_notes}
                      </p>
                    )}
                    <p className="text-xs text-muted-foreground mb-2">
                      General product-type synonyms only (in your locale). Deny any term that looks like a colour, material, or size—keep those for hook terms. Add your own term or edit a suggestion before saving.
                    </p>
                    {/* Add head term (custom) */}
                    <div className="flex gap-2 mb-3">
                      <Input
                        placeholder="Type a head term and save (e.g. duschtasse)"
                        value={customHeadTerm}
                        onChange={(e) => setCustomHeadTerm(e.target.value)}
                        className="flex-1 text-sm"
                      />
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => {
                          const t = customHeadTerm.trim();
                          if (t) {
                            addHeadTermMutation.mutate({ term: t });
                            setCustomHeadTerm('');
                          }
                        }}
                        disabled={addHeadTermMutation.isPending || !customHeadTerm.trim()}
                        title="Save as head term"
                      >
                        <Save className="w-4 h-4 mr-1" />
                        Add
                      </Button>
                    </div>
                    <ul className="space-y-2 border rounded-md p-2 max-h-60 overflow-auto">
                      {(suggestedTerms.suggested_head_terms || [])
                        .filter((h) => !headRemoved.has(h.term))
                        .map((h: SuggestedHeadTerm) => (
                          <li key={h.keyword_id} className="text-sm py-2 px-2 rounded bg-muted/30 space-y-1">
                            {editingHeadKeywordId === h.keyword_id ? (
                              <div className="flex gap-2 items-center">
                                <Input
                                  value={editingHeadValue}
                                  onChange={(e) => setEditingHeadValue(e.target.value)}
                                  className="flex-1 h-8 text-sm"
                                  placeholder="Edit term"
                                />
                                <Button
                                  size="sm"
                                  className="h-8 px-2 text-green-600"
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
                                  title="Save edited term"
                                >
                                  <Save className="w-4 h-4" />
                                </Button>
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  className="h-8 px-2"
                                  onClick={() => { setEditingHeadKeywordId(null); setEditingHeadValue(''); }}
                                >
                                  Cancel
                                </Button>
                              </div>
                            ) : (
                              <>
                                <div className="flex items-center justify-between gap-2">
                                  <span className="font-medium">{h.term}</span>
                                  <div className="flex items-center gap-0.5 shrink-0">
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      className="h-7 w-7 p-0 text-green-600 hover:text-green-700"
                                      title="Approve (save as-is)"
                                      onClick={() => addHeadTermMutation.mutate({ term: h.term })}
                                      disabled={addHeadTermMutation.isPending}
                                    >
                                      <Check className="w-4 h-4" />
                                    </Button>
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      className="h-7 w-7 p-0 text-muted-foreground"
                                      title="Edit & save (modify term before saving)"
                                      onClick={() => {
                                        setEditingHeadKeywordId(h.keyword_id);
                                        setEditingHeadValue(h.term);
                                      }}
                                      disabled={addHeadTermMutation.isPending}
                                    >
                                      <Pencil className="w-3.5 h-3.5" />
                                    </Button>
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      className="h-7 w-7 p-0 text-muted-foreground"
                                      title="Deny (skip this term)"
                                      onClick={() => setHeadRemoved((prev) => new Set(prev).add(h.term))}
                                    >
                                      <X className="w-4 h-4" />
                                    </Button>
                                  </div>
                                </div>
                                <div className="text-xs text-muted-foreground space-y-0.5">
                                  <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                                    <span className="font-medium text-foreground/90">Meaning:</span>
                                    <span>
                                      {h.meaning_en
                                        ? h.meaning_en
                                        : (h.product_type_default_label ?? suggestedTerms.product_type_default_label) || h.product_type_code || '—'}
                                      {!h.meaning_en && (h.product_type_main_category ?? suggestedTerms.product_type_main_category) && (
                                        <span className="ml-1">
                                          · {h.product_type_main_category ?? suggestedTerms.product_type_main_category}
                                        </span>
                                      )}
                                      {h.meaning_en && h.product_type_code && (
                                        <span className="text-muted-foreground/80 ml-1">({h.product_type_code})</span>
                                      )}
                                    </span>
                                    {!h.meaning_en && h.product_type_code && (h.product_type_default_label ?? suggestedTerms.product_type_default_label) && (
                                      <span className="text-muted-foreground/80">({h.product_type_code})</span>
                                    )}
                                    <span>· {h.product_count} products · {h.avg_searches} vol</span>
                                  </div>
                                  {!h.meaning_en && (h.product_type_notes ?? suggestedTerms.product_type_notes) && (
                                    <p className="text-muted-foreground/90 italic">
                                      {h.product_type_notes ?? suggestedTerms.product_type_notes}
                                    </p>
                                  )}
                                </div>
                              </>
                            )}
                          </li>
                        ))}
                      {(!suggestedTerms.suggested_head_terms?.length || suggestedTerms.suggested_head_terms.every((h) => headRemoved.has(h.term))) && !customHeadTerm && (
                        <li className="text-sm text-muted-foreground py-2">No head terms to show. Add your own above or run Extract terms.</li>
                      )}
                    </ul>
                  </div>
                  <div>
                    <h4 className="text-sm font-medium mb-1">Hook terms by product (variant group)</h4>
                    <p className="text-xs text-muted-foreground mb-3">
                      Product-specific words (colour, shape, material—in your locale). Only terms that match this product&apos;s attributes are suggested. Approve the terms you want in titles; deny ones that don&apos;t fit.
                    </p>
                    <div className="space-y-5 max-h-[520px] overflow-auto pr-1">
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
                              Leave product empty to see hook terms for all products; or enter a product ID for one product.
                            </p>
                          );
                        }
                        return productIds.map((productId) => {
                          const terms = byProduct[productId];
                          const first = terms[0];
                          const disp = first?.product_display || {};
                          const productLabel =
                            (disp.default_label && String(disp.default_label).trim()) ||
                            (disp.code && String(disp.code).trim()) ||
                            (disp.variant_sku && String(disp.variant_sku).trim()) ||
                            (disp.variant_source_title && String(disp.variant_source_title).trim()) ||
                            `Product ${productId}`;
                          const variants = productVariants[String(productId)] || [];
                          return (
                            <div key={productId} className="border rounded-lg overflow-hidden bg-card shadow-sm">
                              <div className="px-4 py-3 bg-muted/50 border-b">
                                <div className="flex items-center justify-between gap-2">
                                  <span className="font-semibold text-sm">
                                    #{productId} · {productLabel}
                                  </span>
                                  {variants.length > 0 && (
                                    <span className="text-xs px-2 py-0.5 rounded-full bg-muted text-muted-foreground">
                                      {variants.length} variant{variants.length !== 1 ? 's' : ''}
                                    </span>
                                  )}
                                </div>
                              </div>
                              {variants.length > 0 && (
                                <div className="px-4 py-2 border-b bg-muted/20">
                                  <p className="text-xs font-medium text-muted-foreground mb-2">Variants in this group</p>
                                  <div className="rounded-md border bg-background overflow-hidden">
                                    <table className="w-full text-xs">
                                      <thead>
                                        <tr className="border-b bg-muted/30">
                                          <th className="text-left py-2 px-3 font-medium">ID</th>
                                          <th className="text-left py-2 px-3 font-medium">SKU</th>
                                          <th className="text-left py-2 px-3 font-medium min-w-[120px]">Source title</th>
                                        </tr>
                                      </thead>
                                      <tbody>
                                        {variants.slice(0, 15).map((v) => (
                                          <tr key={v.id} className="border-b last:border-0">
                                            <td className="py-1.5 px-3 font-mono text-muted-foreground">{v.id}</td>
                                            <td className="py-1.5 px-3 font-mono">{v.sku || '—'}</td>
                                            <td className="py-1.5 px-3 truncate max-w-[200px]" title={v.source_title || undefined}>
                                              {v.source_title || '—'}
                                            </td>
                                          </tr>
                                        ))}
                                      </tbody>
                                    </table>
                                    {variants.length > 15 && (
                                      <p className="text-xs text-muted-foreground py-1.5 px-3 border-t">
                                        +{variants.length - 15} more variant{variants.length - 15 !== 1 ? 's' : ''}
                                      </p>
                                    )}
                                  </div>
                                </div>
                              )}
                              <div className="px-4 py-3">
                                <p className="text-xs font-medium text-muted-foreground mb-2">Suggested hook terms</p>
                                <div className="rounded-md border overflow-hidden">
                                  <table className="w-full text-sm">
                                    <thead>
                                      <tr className="bg-muted/40 border-b text-left text-xs text-muted-foreground">
                                        <th className="py-2 px-3 font-medium">Keyword</th>
                                        <th className="py-2 px-3 font-medium w-32">Meaning</th>
                                        <th className="py-2 px-3 font-medium w-16 text-right">Vol</th>
                                        <th className="w-20" />
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {terms.map((h: SuggestedHookTerm) => {
                                        const meaning = (h.attribute_label && String(h.attribute_label).trim()) || h.attribute_code || h.match_kind;
                                        const hookKey = `${h.keyword_id}-${h.product_id}`;
                                        return (
                                          <tr
                                            key={hookKey}
                                            className="border-b last:border-0 hover:bg-muted/30"
                                          >
                                            {editingHookKey === hookKey ? (
                                              <>
                                                <td className="py-2 px-3" colSpan={2}>
                                                  <Input
                                                    value={editingHookValue}
                                                    onChange={(e) => setEditingHookValue(e.target.value)}
                                                    className="h-8 text-sm w-full"
                                                    placeholder="Edit hook term before saving"
                                                  />
                                                </td>
                                                <td className="py-2 px-3 text-right text-muted-foreground tabular-nums">
                                                  {h.avg_searches > 0 ? h.avg_searches : '—'}
                                                </td>
                                                <td className="py-2 px-2">
                                                  <div className="flex items-center gap-0.5 justify-end">
                                                    <Button
                                                      variant="ghost"
                                                      size="sm"
                                                      className="h-7 w-7 p-0 text-green-600 hover:text-green-700"
                                                      onClick={() => {
                                                        const t = editingHookValue.trim();
                                                        if (!t) return;
                                                        addHookTermMutation.mutate({
                                                          term: t,
                                                          productId: h.product_id,
                                                          keywordId: h.keyword_id,
                                                        });
                                                        setHookRemoved((prev) => new Set(prev).add(hookKey));
                                                        setEditingHookKey(null);
                                                        setEditingHookValue('');
                                                      }}
                                                      disabled={addHookTermMutation.isPending || !editingHookValue.trim()}
                                                      title="Save edited hook term"
                                                    >
                                                      <Save className="w-4 h-4" />
                                                    </Button>
                                                    <Button
                                                      variant="ghost"
                                                      size="sm"
                                                      className="h-7 w-7 p-0 text-muted-foreground"
                                                      onClick={() => {
                                                        setEditingHookKey(null);
                                                        setEditingHookValue('');
                                                      }}
                                                      title="Cancel editing"
                                                    >
                                                      <X className="w-4 h-4" />
                                                    </Button>
                                                  </div>
                                                </td>
                                              </>
                                            ) : (
                                              <>
                                                <td className="py-2 px-3 font-medium">{h.term}</td>
                                                <td className="py-2 px-3">
                                                  <span className="inline-block px-2 py-0.5 rounded text-xs bg-muted text-muted-foreground" title={meaning}>
                                                    {meaning}
                                                  </span>
                                                </td>
                                                <td className="py-2 px-3 text-right text-muted-foreground tabular-nums">
                                                  {h.avg_searches > 0 ? h.avg_searches : '—'}
                                                </td>
                                                <td className="py-2 px-2">
                                                  <div className="flex items-center gap-0.5 justify-end">
                                                    <Button
                                                      variant="ghost"
                                                      size="sm"
                                                      className="h-7 w-7 p-0 text-green-600 hover:text-green-700"
                                                      onClick={() =>
                                                        addHookTermMutation.mutate({
                                                          term: h.term,
                                                          productId: h.product_id,
                                                          keywordId: h.keyword_id,
                                                        })
                                                      }
                                                      disabled={addHookTermMutation.isPending}
                                                      title="Approve (save for titles)"
                                                    >
                                                      <Check className="w-4 h-4" />
                                                    </Button>
                                                    <Button
                                                      variant="ghost"
                                                      size="sm"
                                                      className="h-7 w-7 p-0 text-muted-foreground"
                                                      onClick={() => {
                                                        setEditingHookKey(hookKey);
                                                        setEditingHookValue(h.term);
                                                      }}
                                                      title="Edit & save (modify hook before saving)"
                                                    >
                                                      <Pencil className="w-3.5 h-3.5" />
                                                    </Button>
                                                    <Button
                                                      variant="ghost"
                                                      size="sm"
                                                      className="h-7 w-7 p-0 text-muted-foreground"
                                                      onClick={() =>
                                                        setHookRemoved((prev) => new Set(prev).add(hookKey))
                                                      }
                                                      title="Deny (skip this term)"
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

          <Card>
            <CardContent className="pt-6">
              <div className="flex flex-wrap items-center gap-4 mb-4">
                <Filter className="w-4 h-4 text-muted-foreground shrink-0" />
                <div className="flex items-center gap-2">
                  <label className="text-sm font-medium whitespace-nowrap">Source</label>
                  <Select
                    value={productMapSourceFilter}
                    onValueChange={(v) => {
                      setProductMapSourceFilter(v);
                      setProductMapsPage(1);
                    }}
                  >
                    <SelectTrigger className="w-[160px]">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All</SelectItem>
                      <SelectItem value="enum_map">Enum map</SelectItem>
                      <SelectItem value="pav_text">PAV text</SelectItem>
                      <SelectItem value="pav_text_i18n">PAV text (i18n)</SelectItem>
                      <SelectItem value="pav_text_llm">PAV text (LLM)</SelectItem>
                      <SelectItem value="pav_numeric">PAV numeric</SelectItem>
                      <SelectItem value="attr_value_label">Attr value label</SelectItem>
                      <SelectItem value="attr_value_code">Attr value code</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex items-center gap-2">
                  <label className="text-sm font-medium whitespace-nowrap">Detected</label>
                  <Select value={productMapDetectedFilter} onValueChange={(v) => setProductMapDetectedFilter(v as DetectedFilter)}>
                    <SelectTrigger className="w-[140px]">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All</SelectItem>
                      <SelectItem value="size">Size</SelectItem>
                      <SelectItem value="marketplace">Marketplace</SelectItem>
                      <SelectItem value="other">Other</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex items-center gap-2">
                  <Switch
                    id="show-more-details"
                    checked={showMoreDetails}
                    onCheckedChange={setShowMoreDetails}
                  />
                  <Label htmlFor="show-more-details" className="text-sm font-medium cursor-pointer">
                    Show more details
                  </Label>
                </div>
                {productMapDetectedFilter !== 'all' && (
                  <span className="text-xs text-muted-foreground">
                    Showing {productMapsFiltered.length} on this page
                  </span>
                )}
              </div>

              <DataTable
                columns={[
                  {
                    key: 'product_id',
                    header: 'Product ID',
                    render: (item: ProductKeywordMap) => (
                      <span className="font-mono text-sm">{item.product_id}</span>
                    ),
                  },
                  {
                    key: 'variant',
                    header: 'Variant',
                    render: (item: ProductKeywordMap) => {
                      const ev = item.evidence && typeof item.evidence === 'object' ? item.evidence as Record<string, unknown> : {};
                      const vid = ev.variant_id != null ? ev.variant_id : null;
                      return (
                        <span className="text-sm font-mono text-muted-foreground">
                          {vid != null ? String(vid) : '—'}
                        </span>
                      );
                    },
                  },
                  {
                    key: 'keyword_term',
                    header: 'Keyword',
                    render: (item: ProductKeywordMap) => {
                      const sig = detectKeywordSignal(item.keyword_term);
                      return (
                        <span className="font-medium">
                          {item.keyword_term}
                          {sig && (
                            <span className="ml-2 text-xs px-1.5 py-0.5 rounded bg-muted text-muted-foreground capitalize">
                              {sig}
                            </span>
                          )}
                        </span>
                      );
                    },
                  },
                  {
                    key: 'attribute',
                    header: 'Attribute',
                    render: (item: ProductKeywordMap) => (
                      <span className="text-sm font-mono">{item.attribute_code || item.attribute_name || '—'}</span>
                    ),
                  },
                  {
                    key: 'value',
                    header: 'Value',
                    render: (item: ProductKeywordMap) => (
                      <span className="text-sm">{item.attribute_value_label || item.attribute_value_code || '—'}</span>
                    ),
                  },
                  {
                    key: 'source',
                    header: 'Source',
                    render: (item: ProductKeywordMap) => (
                      <span className="text-sm px-2 py-1 rounded bg-muted">{item.source}</span>
                    ),
                  },
                  {
                    key: 'matched_text',
                    header: 'Match',
                    render: (item: ProductKeywordMap) => (
                      <span className="text-sm">{item.matched_text || item.attribute_value_label || '—'}</span>
                    ),
                  },
                  {
                    key: 'reason',
                    header: 'Reason',
                    render: (item: ProductKeywordMap) => {
                      const ev = item.evidence && typeof item.evidence === 'object' ? item.evidence as Record<string, unknown> : {};
                      const reasonCode = ev.reason_code != null ? String(ev.reason_code) : null;
                      const matchedPhrase = ev.matched_phrase != null ? String(ev.matched_phrase) : null;
                      const phraseDisplay = matchedPhrase ? (matchedPhrase.length > 40 && !showMoreDetails ? `${matchedPhrase.slice(0, 40)}…` : matchedPhrase) : null;
                      const reason = reasonCode ?? phraseDisplay ?? (item.match_kind || item.source || '—');
                      return <span className="text-sm text-muted-foreground" title={matchedPhrase && matchedPhrase.length > 40 ? matchedPhrase : undefined}>{reason}</span>;
                    },
                  },
                  ...(showMoreDetails
                    ? [
                        {
                          key: 'match_kind_full',
                          header: 'Match kind',
                          render: (item: ProductKeywordMap) => (
                            <span className="text-xs font-mono text-muted-foreground" title={item.source || ''}>
                              {item.match_kind || item.source || '—'}
                            </span>
                          ),
                        },
                        {
                          key: 'created_at',
                          header: 'Created',
                          render: (item: ProductKeywordMap) =>
                            item.created_at ? (
                              <span className="text-xs text-muted-foreground">
                                {new Date(item.created_at).toLocaleString(undefined, { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })}
                              </span>
                            ) : (
                              <span className="text-muted-foreground">—</span>
                            ),
                        },
                      ]
                    : []),
                  {
                    key: 'num',
                    header: 'Num',
                    render: (item: ProductKeywordMap) => {
                      const hasNum = item.num_value != null;
                      const unit = item.num_unit ? ` ${item.num_unit}` : '';
                      return (
                        <span className="text-sm font-mono">
                          {hasNum ? `${item.num_value}${unit}` : '—'}
                        </span>
                      );
                    },
                  },
                  {
                    key: 'confidence',
                    header: 'Confidence',
                    render: (item: ProductKeywordMap) =>
                      item.confidence ? (
                        <span className="text-sm">{(item.confidence * 100).toFixed(1)}%</span>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      ),
                  },
                  {
                    key: 'details',
                    header: '',
                    render: (item: ProductKeywordMap) => {
                      const ev = item.evidence && typeof item.evidence === 'object' ? item.evidence as Record<string, unknown> : {};
                      const matchedPhrase = ev.matched_phrase != null ? String(ev.matched_phrase) : null;
                      const reasonCode = ev.reason_code != null ? String(ev.reason_code) : null;
                      const model = ev.model != null ? String(ev.model) : null;
                      const variantId = ev.variant_id != null ? String(ev.variant_id) : null;
                      const created = item.created_at
                        ? new Date(item.created_at).toLocaleString(undefined, { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
                        : null;
                      const hasEvidence = matchedPhrase || reasonCode || model || variantId || Object.keys(ev).length > 0;
                      const evidenceJson = JSON.stringify(item.evidence ?? {}, null, 2);
                      const copyEvidence = () => {
                        navigator.clipboard.writeText(evidenceJson);
                        toast({ title: 'Copied', description: 'Evidence copied to clipboard.' });
                      };
                      return (
                        <Popover>
                          <PopoverTrigger asChild>
                            <Button variant="ghost" size="sm" className="h-8 w-8 p-0" title="View details">
                              <Info className="h-4 w-4 text-muted-foreground" />
                            </Button>
                          </PopoverTrigger>
                          <PopoverContent className={showMoreDetails ? 'w-[420px] max-h-[80vh] overflow-auto' : 'w-80'} align="start">
                            <div className="space-y-2 text-sm">
                              {item.attribute_code && (
                                <div>
                                  <span className="font-medium text-muted-foreground">Attribute:</span>{' '}
                                  <span className="font-mono">{item.attribute_code}</span>
                                  {item.attribute_name && item.attribute_name !== item.attribute_code && ` (${item.attribute_name})`}
                                </div>
                              )}
                              {matchedPhrase && (
                                <div>
                                  <span className="font-medium text-muted-foreground">Matched phrase:</span>{' '}
                                  {matchedPhrase}
                                </div>
                              )}
                              {reasonCode && (
                                <div>
                                  <span className="font-medium text-muted-foreground">Reason:</span> {reasonCode}
                                </div>
                              )}
                              {(item.match_kind || item.source) && (
                                <div>
                                  <span className="font-medium text-muted-foreground">Source / match kind:</span>{' '}
                                  {item.match_kind || item.source}
                                </div>
                              )}
                              {item.matched_text && (
                                <div>
                                  <span className="font-medium text-muted-foreground">Matched text:</span>{' '}
                                  {item.matched_text}
                                </div>
                              )}
                              {model && (
                                <div>
                                  <span className="font-medium text-muted-foreground">Model:</span> {model}
                                </div>
                              )}
                              {variantId && (
                                <div>
                                  <span className="font-medium text-muted-foreground">Variant ID:</span> {variantId}
                                </div>
                              )}
                              {item.confidence != null && (
                                <div>
                                  <span className="font-medium text-muted-foreground">Confidence:</span>{' '}
                                  {(Number(item.confidence) * 100).toFixed(1)}%
                                </div>
                              )}
                              {created && (
                                <div>
                                  <span className="font-medium text-muted-foreground">Created:</span> {created}
                                </div>
                              )}
                              {showMoreDetails && (
                                <div className="pt-2 border-t">
                                  <div className="flex items-center justify-between mb-1">
                                    <span className="font-medium text-muted-foreground">Evidence (JSON)</span>
                                    <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={copyEvidence}>
                                      Copy
                                    </Button>
                                  </div>
                                  <pre className="text-xs bg-muted p-2 rounded overflow-auto max-h-40 font-mono whitespace-pre-wrap break-all">
                                    {evidenceJson}
                                  </pre>
                                </div>
                              )}
                              {!hasEvidence && !created && Object.keys(ev).length === 0 && !item.attribute_code && (
                                <span className="text-muted-foreground">No extra details</span>
                              )}
                            </div>
                          </PopoverContent>
                        </Popover>
                      );
                    },
                  },
                  {
                    key: 'actions',
                    header: 'Actions',
                    render: (item: ProductKeywordMap) => (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => deleteProductMapMutation.mutate(item.id)}
                        disabled={deleteProductMapMutation.isPending}
                        className="text-destructive hover:text-destructive"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    ),
                  },
                ]}
                data={productMapsFiltered}
                keyExtractor={(item: ProductKeywordMap) => String(item.id)}
                isLoading={productMapsLoading}
                emptyTitle="No product maps"
                emptyDescription="Run “Map to Products (AI)” above to create product-level keyword maps, then review and remove any you don’t want (e.g. size or marketplace terms)."
              />

              {productMapsCount > pageSize && (
                <div className="mt-4 flex justify-end gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={productMapsPage <= 1}
                    onClick={() => setProductMapsPage((p) => Math.max(1, p - 1))}
                  >
                    Previous
                  </Button>
                  <span className="flex items-center px-2 text-sm text-muted-foreground">
                    Page {productMapsPage} ({(productMapsPage - 1) * pageSize + 1}–{Math.min(productMapsPage * pageSize, productMapsCount)} of {productMapsCount})
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={productMapsPage * pageSize >= productMapsCount}
                    onClick={() => setProductMapsPage((p) => p + 1)}
                  >
                    Next
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Product-level AI Mapping Dialog */}
      <Dialog open={showProductMappingDialog} onOpenChange={setShowProductMappingDialog}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Map Keywords to Products (AI)</DialogTitle>
            <DialogDescription>
              Create per-product keyword mappings using AI to match keywords with product attributes and variants.
              This is used for title generation.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="use_llm">Use LLM (AI) for text matching</Label>
                <p className="text-sm text-muted-foreground">
                  Enable AI-powered matching for better accuracy
                </p>
              </div>
              <Switch
                id="use_llm"
                checked={productMappingOptions.use_llm || false}
                onCheckedChange={(checked) =>
                  setProductMappingOptions({ ...productMappingOptions, use_llm: checked })
                }
              />
            </div>

            {productMappingOptions.use_llm && (
              <div className="space-y-3 rounded-lg border p-4 bg-muted/30">
                <p className="text-sm font-medium">AI mapping instructions (optional)</p>
                <div className="space-y-2">
                  <Label htmlFor="focus_on">Focus on</Label>
                  <Textarea
                    id="focus_on"
                    className="min-h-[60px]"
                    placeholder="e.g. material, installation, dimensions"
                    value={productMappingOptions.focus_on ?? ''}
                    onChange={(e) =>
                      setProductMappingOptions({ ...productMappingOptions, focus_on: e.target.value })
                    }
                  />
                  <p className="text-xs text-muted-foreground">
                    Tell the AI which attributes or topics to prioritize when mapping.
                  </p>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="ignore">Ignore</Label>
                  <Textarea
                    id="ignore"
                    className="min-h-[60px]"
                    placeholder="e.g. oder, vs, comparison words, marketplace names"
                    value={productMappingOptions.ignore ?? ''}
                    onChange={(e) =>
                      setProductMappingOptions({ ...productMappingOptions, ignore: e.target.value })
                    }
                  />
                  <p className="text-xs text-muted-foreground">
                    Tell the AI what not to map (connectors, comparison terms, etc.).
                  </p>
                </div>
                <div className="flex flex-col gap-2 pt-2 border-t">
                  <p className="text-sm font-medium">Presets</p>
                  <label className="flex items-center gap-2 cursor-pointer text-sm">
                    <Checkbox
                      checked={productMappingOptions.ignore_size_and_marketplace ?? false}
                      onCheckedChange={(checked) =>
                        setProductMappingOptions({
                          ...productMappingOptions,
                          ignore_size_and_marketplace: !!checked,
                        })
                      }
                    />
                    Ignore size and marketplace keywords
                  </label>
                  <p className="text-xs text-muted-foreground ml-6">
                    Do not map keywords that are only sizes (S, M, L, dimensions) or marketplace names (Amazon, eBay, etc.).
                  </p>
                  <label className="flex items-center gap-2 cursor-pointer text-sm">
                    <Checkbox
                      checked={productMappingOptions.focus_head_terms ?? false}
                      onCheckedChange={(checked) =>
                        setProductMappingOptions({
                          ...productMappingOptions,
                          focus_head_terms: !!checked,
                        })
                      }
                    />
                    Focus on head terms (broad category terms)
                  </label>
                  <p className="text-xs text-muted-foreground ml-6">
                    Prioritize broad terms that describe the product type.
                  </p>
                  <label className="flex items-center gap-2 cursor-pointer text-sm">
                    <Checkbox
                      checked={productMappingOptions.focus_hook_terms ?? false}
                      onCheckedChange={(checked) =>
                        setProductMappingOptions({
                          ...productMappingOptions,
                          focus_hook_terms: !!checked,
                        })
                      }
                    />
                    Focus on hook terms (product-specific terms)
                  </label>
                  <p className="text-xs text-muted-foreground ml-6">
                    Prioritize specific terms that uniquely describe this product.
                  </p>
                </div>
              </div>
            )}

            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="include_descriptions">Include product descriptions</Label>
                <p className="text-sm text-muted-foreground">
                  Search in product descriptions for keyword matches
                </p>
              </div>
              <Switch
                id="include_descriptions"
                checked={productMappingOptions.include_descriptions || false}
                onCheckedChange={(checked) =>
                  setProductMappingOptions({ ...productMappingOptions, include_descriptions: checked })
                }
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="max_text_matches">Max text matches per product</Label>
                <Input
                  id="max_text_matches"
                  type="number"
                  value={productMappingOptions.max_text_matches || 60}
                  onChange={(e) =>
                    setProductMappingOptions({ ...productMappingOptions, max_text_matches: parseInt(e.target.value) })
                  }
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="max_enum_maps">Max enum maps per product</Label>
                <Input
                  id="max_enum_maps"
                  type="number"
                  value={productMappingOptions.max_enum_maps || 120}
                  onChange={(e) =>
                    setProductMappingOptions({ ...productMappingOptions, max_enum_maps: parseInt(e.target.value) })
                  }
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="llm_max_keywords">LLM max keywords</Label>
                <Input
                  id="llm_max_keywords"
                  type="number"
                  value={productMappingOptions.llm_max_keywords || 80}
                  onChange={(e) =>
                    setProductMappingOptions({ ...productMappingOptions, llm_max_keywords: parseInt(e.target.value) })
                  }
                  disabled={!productMappingOptions.use_llm}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="max_description_chars">Max description chars</Label>
                <Input
                  id="max_description_chars"
                  type="number"
                  value={productMappingOptions.max_description_chars || 2000}
                  onChange={(e) =>
                    setProductMappingOptions({ ...productMappingOptions, max_description_chars: parseInt(e.target.value) })
                  }
                  disabled={!productMappingOptions.include_descriptions}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="limit">Limit products (optional)</Label>
                <Input
                  id="limit"
                  type="number"
                  placeholder="All products"
                  value={productMappingOptions.limit || ''}
                  onChange={(e) =>
                    setProductMappingOptions({
                      ...productMappingOptions,
                      limit: e.target.value ? parseInt(e.target.value) : undefined,
                    })
                  }
                />
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowProductMappingDialog(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => productMappingMutation.mutate(productMappingOptions)}
              disabled={productMappingMutation.isPending}
            >
              {productMappingMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Mapping...
                </>
              ) : (
                'Start Mapping'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
