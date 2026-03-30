import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, ArrowRight, Check, FileText, Loader2, GripVertical, Info, AlertTriangle, Sparkles, Eye, Trash2 } from 'lucide-react';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  getTemplates,
  getProductTypes,
  getChannels,
  getLocales,
  getAttributes,
  getPlannerRuns,
  proposeTemplateFromRun,
  getSuggestedTerms,
  getSavedTerms,
  addHeadTerm,
  addHookTerm,
  removeHeadTerm,
  removeHookTerm,
  createTemplate,
  createTemplatePart,
  getChannelLocalePolicies,
  Template,
  ProductType,
  Channel,
  Locale,
  Attribute,
  PlannerRun,
  SuggestedHeadTerm,
  SuggestedHookTerm,
  ProposedTemplateAttribute,
} from '@/lib/api';
import { useToast } from '@/hooks/use-toast';

const STEPS = [
  { id: 'template', title: 'Scope', description: 'Choose target channel, locale and product type' },
  { id: 'head', title: 'Head term', description: 'Main product-type label (e.g. "Shower tray")' },
  { id: 'hook', title: 'Hook term', description: 'Differentiator per product (colour, material…)' },
  { id: 'attributes', title: 'Attributes', description: 'Attributes to include in the title and their order' },
] as const;

type StepId = (typeof STEPS)[number]['id'];

// ── Title preview bar ─────────────────────────────────────────────────────────
function TitlePreview({
  includeHead,
  includeHook,
  attrIds,
  attributes,
}: {
  includeHead: boolean;
  includeHook: boolean;
  attrIds: number[];
  attributes: Attribute[];
}) {
  const parts: string[] = [];
  if (includeHead) parts.push('Head term');
  if (includeHook) parts.push('Hook term');
  for (const id of attrIds) {
    const a = attributes.find((x) => x.id === id);
    if (a) parts.push(a.code);
  }
  if (parts.length === 0) return null;
  return (
    <div className="flex items-center gap-2 rounded-lg border bg-muted/40 px-4 py-2.5 text-sm">
      <Eye className="w-4 h-4 text-muted-foreground shrink-0" />
      <span className="text-muted-foreground text-xs font-medium mr-1">Preview:</span>
      <div className="flex flex-wrap items-center gap-1">
        {parts.map((p, i) => (
          <span key={i} className="flex items-center gap-1">
            {i > 0 && <span className="text-muted-foreground/50 text-xs">–</span>}
            <span className={`px-2 py-0.5 rounded text-xs font-medium ${
              p === 'Head term' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' :
              p === 'Hook term' ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400' :
              'bg-muted text-foreground'
            }`}>{p}</span>
          </span>
        ))}
      </div>
    </div>
  );
}

export default function TemplateWizard() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [step, setStep] = useState<StepId>('template');

  const urlProductTypeId = searchParams.get('product_type_id') ?? '';
  const urlChannelCode = searchParams.get('channel_code') ?? '';
  const urlLocaleCode = searchParams.get('locale_code') ?? '';
  const urlRunId = searchParams.get('run_id') ?? '';

  // Step 1: template choice
  const [templateMode, setTemplateMode] = useState<'new' | 'clone'>('new');
  const [productTypeId, setProductTypeId] = useState<string>(urlProductTypeId);
  const [channelCode, setChannelCode] = useState<string>(urlChannelCode);
  const [localeCode, setLocaleCode] = useState<string>(urlLocaleCode);
  const [cloneTemplateId, setCloneTemplateId] = useState<string>('');

  // Keyword run — selected in Step 1, used across all steps
  const [selectedRunId, setSelectedRunId] = useState<string>(urlRunId);

  // Step 2 & 3
  const [includeHeadTerm, setIncludeHeadTerm] = useState(true);
  const [includeHookTerm, setIncludeHookTerm] = useState(true);

  // Step 4: attributes
  const [selectedAttributeIds, setSelectedAttributeIds] = useState<number[]>([]);
  const [proposing, setProposing] = useState(false);
  const [useAiPropose, setUseAiPropose] = useState(false);
  const [proposedAttrs, setProposedAttrs] = useState<ProposedTemplateAttribute[]>([]);
  // Axis attributes are fixed at position 2 — sourced from propose-template or product type
  const [axisAttributes, setAxisAttributes] = useState<ProposedTemplateAttribute[]>([]);

  // Approval state
  const [approvedHeadIds, setApprovedHeadIds] = useState<Set<number>>(new Set());
  const [approvedHookKeys, setApprovedHookKeys] = useState<Set<string>>(new Set());

  // Data fetches
  const { data: templatesData } = useQuery({ queryKey: ['templates'], queryFn: () => getTemplates({ page_size: 200 }) });
  const { data: productTypesData } = useQuery({ queryKey: ['product-types'], queryFn: () => getProductTypes() });
  const { data: channelsData } = useQuery({ queryKey: ['channels'], queryFn: () => getChannels() });
  const { data: localesData } = useQuery({ queryKey: ['locales'], queryFn: () => getLocales() });
  const { data: attributesData } = useQuery({ queryKey: ['attributes'], queryFn: () => getAttributes({ page_size: 200 }) });
  const { data: plannerRunsData } = useQuery({ queryKey: ['planner-runs'], queryFn: () => getPlannerRuns({ page_size: 100 }) });

  const templates = (templatesData?.results ?? []) as Template[];
  const productTypes = (productTypesData?.results ?? []) as ProductType[];
  const channels = (channelsData?.results ?? []) as Channel[];
  const locales = (localesData?.results ?? []) as Locale[];
  const attributes = (attributesData?.results ?? []) as Attribute[];
  const allPlannerRuns = (plannerRunsData?.results ?? []) as PlannerRun[];

  // Filter runs by current scope selection so the list is relevant
  const filteredRuns = allPlannerRuns.filter((r) => {
    if (productTypeId && r.product_type_code && r.product_type_code !== productTypes.find((p) => String(p.id) === productTypeId)?.code) return false;
    if (localeCode && r.locale_code !== localeCode) return false;
    return true;
  });
  // Fall back to all runs if filter is too restrictive
  const plannerRuns = filteredRuns.length > 0 ? filteredRuns : allPlannerRuns;

  const selectedLocaleObj = locales.find((l) => l.code === localeCode) ?? null;
  const selectedChannelObj = channels.find((c) => c.code === channelCode) ?? null;

  // Already-saved terms (approved during keyword mapping process) — load as soon as locale is known
  const { data: savedTermsData, refetch: refetchSavedTerms } = useQuery({
    queryKey: ['saved-terms-wizard', selectedLocaleObj?.id, selectedChannelObj?.id],
    queryFn: () =>
      getSavedTerms({
        locale_id: selectedLocaleObj!.id,
        channel_id: selectedChannelObj?.id,
      }),
    enabled: !!selectedLocaleObj,
  });

  // Filter saved head terms for current product type
  const savedHeadTerms = savedTermsData?.head_terms_by_product_type.find(
    (g) => String(g.product_type_id) === productTypeId
  )?.terms ?? [];

  // All saved hook terms (grouped by product)
  const savedHookTermsByProduct = savedTermsData?.hook_terms_by_product ?? [];

  // Suggested head/hook terms — loaded once, shared across steps 2 and 3
  const { data: suggestedTermsData, isFetching: suggestedTermsFetching, refetch: refetchSuggestedTerms } = useQuery({
    queryKey: ['wizard-suggested-terms', selectedRunId, selectedLocaleObj?.id],
    queryFn: () =>
      getSuggestedTerms(parseInt(selectedRunId), {
        locale_id: selectedLocaleObj!.id,
        channel_id: selectedChannelObj?.id,
      }),
    enabled: false,
  });

  const addHeadMutation = useMutation({
    mutationFn: (term: string) =>
      addHeadTerm(parseInt(productTypeId), {
        locale_id: selectedLocaleObj!.id,
        channel_id: selectedChannelObj?.id ?? null,
        term,
      }),
    onSuccess: (_, term) => {
      toast({ title: `Head term "${term}" saved` });
      refetchSavedTerms();
    },
    onError: () => toast({ title: 'Failed to save head term', variant: 'destructive' }),
  });

  const addHookMutation = useMutation({
    mutationFn: ({ productId, term }: { productId: number; term: string }) =>
      addHookTerm(productId, {
        locale_id: selectedLocaleObj!.id,
        channel_id: selectedChannelObj?.id ?? null,
        term,
      }),
    onSuccess: (_, { term }) => {
      toast({ title: `Hook term "${term}" saved` });
      refetchSavedTerms();
    },
    onError: () => toast({ title: 'Failed to save hook term', variant: 'destructive' }),
  });

  const removeHeadMutation = useMutation({
    mutationFn: ({ productTypeId: ptId, synonymId }: { productTypeId: number; synonymId: number }) =>
      removeHeadTerm(ptId, synonymId),
    onSuccess: () => {
      toast({ title: 'Head term removed' });
      refetchSavedTerms();
    },
    onError: () => toast({ title: 'Failed to remove head term', variant: 'destructive' }),
  });

  const removeHookMutation = useMutation({
    mutationFn: ({ productId, hookTermId }: { productId: number; hookTermId: number }) =>
      removeHookTerm(productId, hookTermId),
    onSuccess: () => {
      toast({ title: 'Hook term removed' });
      refetchSavedTerms();
    },
    onError: () => toast({ title: 'Failed to remove hook term', variant: 'destructive' }),
  });

  const { data: policyData } = useQuery({
    queryKey: ['channel-locale-policies', selectedChannelObj?.id, selectedLocaleObj?.id],
    queryFn: () =>
      getChannelLocalePolicies({ channel_id: selectedChannelObj!.id, locale_id: selectedLocaleObj!.id, page_size: 10 }),
    enabled: templateMode === 'new' && !!selectedChannelObj && !!selectedLocaleObj,
  });
  const channelPolicy = policyData?.results?.[0] ?? null;
  const policyLoaded = !!selectedChannelObj && !!selectedLocaleObj && policyData !== undefined;

  const createMutation = useMutation({
    mutationFn: async () => {
      let scope = { product_type_id: 0, channel_code: '', locale_code: '' };
      if (templateMode === 'clone' && cloneTemplateId) {
        const t = templates.find((x) => x.id === parseInt(cloneTemplateId));
        if (!t) throw new Error('Selected template not found. Please go back and reselect.');
        scope = { product_type_id: t.product_type_id, channel_code: t.channel_code, locale_code: t.locale_code };
      } else {
        const ptId = parseInt(productTypeId);
        if (!ptId || !channelCode || !localeCode) {
          throw new Error('Please complete Step 1: select a product type, channel, and locale.');
        }
        scope = { product_type_id: ptId, channel_code: channelCode, locale_code: localeCode };
      }
      const existingVersions = templates
        .filter(
          (t) =>
            t.product_type_id === scope.product_type_id &&
            t.channel_code === scope.channel_code &&
            t.locale_code === scope.locale_code,
        )
        .map((t) => t.version ?? 1);
      const nextVersion = existingVersions.length > 0 ? Math.max(...existingVersions) + 1 : 1;
      const template = await createTemplate({ ...scope, version: nextVersion });
      const parts: { part_type: string; literal_text?: string; attribute_id?: number | null }[] = [];
      // Position 1: head term (product type label)
      if (includeHeadTerm) parts.push({ part_type: 'head_term' });
      // Position 2: variation axis attributes (fixed, one per axis)
      for (const axis of axisAttributes) {
        parts.push({ part_type: 'literal', literal_text: ' - ' });
        parts.push({ part_type: 'axis_attribute', attribute_id: axis.attribute_id });
      }
      // If no axis attrs but hook term is included, fall back to hook_term slot
      if (axisAttributes.length === 0 && includeHookTerm) {
        if (includeHeadTerm) parts.push({ part_type: 'literal', literal_text: ' - ' });
        parts.push({ part_type: 'hook_term' });
      }
      // Positions 3+: AI-selected additional attributes
      for (const attrId of selectedAttributeIds) {
        parts.push({ part_type: 'literal', literal_text: ' - ' });
        parts.push({ part_type: 'attribute_value', attribute_id: attrId });
      }
      for (let i = 0; i < parts.length; i++) {
        await createTemplatePart({
          template_id: template.id,
          position: i,
          part_type: parts[i].part_type,
          literal_text: parts[i].literal_text,
          attribute_id: parts[i].attribute_id,
        });
      }
      return template;
    },
    onSuccess: (t) => {
      queryClient.invalidateQueries({ queryKey: ['templates'] });
      toast({ title: 'Template created' });
      navigate(`/templates/${t.id}/edit`);
    },
    onError: (err: unknown) => {
      const msg =
        err instanceof Error
          ? err.message
          : String((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? '');
      toast({ title: 'Failed to create template', description: msg || undefined, variant: 'destructive' });
    },
  });

  const stepIndex = STEPS.findIndex((s) => s.id === step);

  // Step 1 is complete only when all required scope fields are filled
  const step1Complete =
    templateMode === 'clone' ? !!cloneTemplateId : !!(productTypeId && channelCode && localeCode);

  const canNext = step === 'template' ? step1Complete : true;
  const canSubmit = step === 'attributes';

  // Only allow jumping to steps that have been unlocked
  const canGoToStep = (targetIndex: number) => step1Complete || targetIndex === 0;

  const handleNext = () => {
    if (step === 'attributes') {
      if (createMutation.isPending) return;
      createMutation.mutate();
      return;
    }
    const next = STEPS[stepIndex + 1];
    if (next) setStep(next.id);
  };

  const handleBack = () => {
    if (stepIndex > 0) setStep(STEPS[stepIndex - 1].id);
  };

  // When a run is selected, auto-fill product type and locale if not already set
  const handleRunSelect = (runId: string) => {
    setSelectedRunId(runId);
    const run = allPlannerRuns.find((r) => String(r.id) === runId);
    if (!run) return;
    if (!productTypeId && run.product_type_code) {
      const pt = productTypes.find((p) => p.code === run.product_type_code);
      if (pt) setProductTypeId(String(pt.id));
    }
    if (!localeCode && run.locale_code) {
      setLocaleCode(run.locale_code);
    }
  };

  const addAttribute = (attrId: number) => {
    if (selectedAttributeIds.includes(attrId)) return;
    setSelectedAttributeIds([...selectedAttributeIds, attrId]);
  };
  const removeAttribute = (attrId: number) => {
    setSelectedAttributeIds(selectedAttributeIds.filter((id) => id !== attrId));
  };
  const moveAttribute = (index: number, dir: -1 | 1) => {
    const next = index + dir;
    if (next < 0 || next >= selectedAttributeIds.length) return;
    const arr = [...selectedAttributeIds];
    const t = arr[index]; arr[index] = arr[next]; arr[next] = t;
    setSelectedAttributeIds(arr);
  };

  const handlePropose = async () => {
    if (!selectedRunId) return;
    setProposing(true);
    try {
      const res = await proposeTemplateFromRun(parseInt(selectedRunId), { use_ai: useAiPropose });
      const axisIds = new Set((res.axis_attributes ?? []).map((a) => a.attribute_id));
      const ids = res.proposed.filter((p) => !axisIds.has(p.attribute_id)).map((p) => p.attribute_id);
      setAxisAttributes(res.axis_attributes ?? []);
      setSelectedAttributeIds(ids);
      setProposedAttrs(res.proposed);
      const axisLabel = (res.axis_attributes ?? []).map((a) => a.attribute_code).join(', ');
      toast({
        title: `${ids.length} attributes suggested (${res.source === 'ai' ? 'AI-ordered' : 'by search volume'})`,
        description: axisLabel ? `Variation axis locked at position 2: ${axisLabel}` : undefined,
      });
    } catch {
      toast({ title: 'Could not load suggestions', variant: 'destructive' });
    } finally {
      setProposing(false);
    }
  };

  const runLabel = (r: PlannerRun) =>
    `${r.product_type_code ?? 'all types'} · ${r.locale_code} · ${r.keyword_count.toLocaleString()} keywords`;

  return (
    <div className="page-container">
      <PageHeader
        title="Create template"
        description="A title template defines the structure of marketplace titles for a product type and channel."
        breadcrumbs={[
          { label: 'Dashboard', href: '/' },
          { label: 'Templates', href: '/templates' },
          { label: 'New' },
        ]}
        actions={
          <Button variant="outline" asChild>
            <Link to="/templates">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back
            </Link>
          </Button>
        }
      />

      {/* Step indicator */}
      <div className="flex flex-wrap gap-2 mb-6">
        {STEPS.map((s, i) => {
          const unlocked = canGoToStep(i);
          return (
            <button
              key={s.id}
              type="button"
              onClick={() => unlocked && setStep(s.id)}
              disabled={!unlocked}
              title={!unlocked ? 'Complete Step 1 first' : undefined}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                !unlocked
                  ? 'opacity-40 cursor-not-allowed bg-muted/40 text-muted-foreground'
                  : step === s.id
                    ? 'bg-primary text-primary-foreground'
                    : i < stepIndex
                      ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                      : 'bg-muted/60 text-muted-foreground hover:bg-muted'
              }`}
            >
              {i < stepIndex && unlocked ? <Check className="w-3.5 h-3.5" /> : <span className="w-4 h-4 rounded-full bg-current/10 flex items-center justify-center text-xs">{i + 1}</span>}
              {s.title}
            </button>
          );
        })}
      </div>

      {/* Live title preview (shown once at least one part is configured) */}
      <div className="mb-4">
        <TitlePreview
          includeHead={includeHeadTerm}
          includeHook={includeHookTerm}
          attrIds={selectedAttributeIds}
          attributes={attributes}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{STEPS[stepIndex].title}</CardTitle>
          <CardDescription>{STEPS[stepIndex].description}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">

          {/* ── Step 1: Scope ───────────────────────────────────────────────── */}
          {step === 'template' && (
            <div className="space-y-6">
              <div className="flex gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="radio" name="templateMode" checked={templateMode === 'new'} onChange={() => setTemplateMode('new')} />
                  <span>New template</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="radio" name="templateMode" checked={templateMode === 'clone'} onChange={() => setTemplateMode('clone')} />
                  <span>Clone from existing</span>
                </label>
              </div>

              {templateMode === 'new' && (
                <>
                  {/* Quick-fill from a keyword run */}
                  <div className="rounded-lg border bg-blue-50 dark:bg-blue-950/20 border-blue-200 dark:border-blue-800 p-4 space-y-3">
                    <div className="flex items-start gap-2">
                      <Sparkles className="w-4 h-4 text-blue-600 dark:text-blue-400 shrink-0 mt-0.5" />
                      <div>
                        <p className="text-sm font-medium text-blue-900 dark:text-blue-200">Start from a keyword run (recommended)</p>
                        <p className="text-xs text-blue-700 dark:text-blue-400 mt-0.5">
                          Selecting a run auto-fills the product type and locale, and enables AI-powered suggestions in the next steps.
                        </p>
                      </div>
                    </div>
                    <Select value={selectedRunId} onValueChange={handleRunSelect}>
                      <SelectTrigger className="w-full max-w-md bg-white dark:bg-background">
                        <SelectValue placeholder="Choose a keyword run…" />
                      </SelectTrigger>
                      <SelectContent>
                        {allPlannerRuns.filter((r) => r.status === 'success').map((r) => (
                          <SelectItem key={r.id} value={String(r.id)}>
                            Run #{r.id} · {runLabel(r)}
                          </SelectItem>
                        ))}
                        {allPlannerRuns.filter((r) => r.status === 'success').length === 0 && (
                          <div className="px-3 py-2 text-xs text-muted-foreground">No completed keyword runs yet.</div>
                        )}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="space-y-2">
                      <Label>Product type <span className="text-destructive">*</span></Label>
                      <Select value={productTypeId} onValueChange={setProductTypeId}>
                        <SelectTrigger>
                          <SelectValue placeholder="Select…" />
                        </SelectTrigger>
                        <SelectContent>
                          {productTypes.map((pt) => (
                            <SelectItem key={pt.id} value={String(pt.id)}>{pt.code}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label>Channel <span className="text-destructive">*</span></Label>
                      <Select value={channelCode} onValueChange={setChannelCode}>
                        <SelectTrigger><SelectValue placeholder="Select…" /></SelectTrigger>
                        <SelectContent>
                          {channels.map((c) => (
                            <SelectItem key={c.id} value={c.code}>{c.code}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label>Locale <span className="text-destructive">*</span></Label>
                      <Select value={localeCode} onValueChange={setLocaleCode}>
                        <SelectTrigger><SelectValue placeholder="Select…" /></SelectTrigger>
                        <SelectContent>
                          {locales.map((loc) => (
                            <SelectItem key={loc.code} value={loc.code}>
                              {loc.name || loc.code} ({loc.code})
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  {/* Marketplace rules summary */}
                  {policyLoaded && (
                    <div className={`rounded-lg border p-4 text-sm ${channelPolicy ? 'bg-muted/40' : 'bg-amber-50 border-amber-200 dark:bg-amber-950/20 dark:border-amber-800'}`}>
                      {channelPolicy ? (
                        <div className="space-y-3">
                          <div className="flex items-center gap-2 font-medium">
                            <Info className="w-4 h-4 text-muted-foreground shrink-0" />
                            Title rules · {channelPolicy.channel_code ?? channelCode} · {channelPolicy.locale_code ?? localeCode}
                          </div>
                          <div className="flex flex-wrap gap-2">
                            <Badge variant="secondary">Max {channelPolicy.title_max_len} chars</Badge>
                            <Badge variant="secondary">Sep: <span className="font-mono ml-1">"{channelPolicy.title_separator}"</span></Badge>
                            <Badge variant="secondary">Brand: {channelPolicy.brand_position}</Badge>
                            <Badge variant="secondary">Mode: {channelPolicy.title_mode}</Badge>
                            {channelPolicy.dedupe_words && <Badge variant="outline">dedupe words</Badge>}
                            {channelPolicy.normalize_whitespace && <Badge variant="outline">normalize spaces</Badge>}
                          </div>
                          {Array.isArray(channelPolicy.banned_terms) && channelPolicy.banned_terms.length > 0 && (
                            <div className="text-xs text-muted-foreground">Banned: {channelPolicy.banned_terms.join(', ')}</div>
                          )}
                        </div>
                      ) : (
                        <div className="flex items-start gap-2 text-amber-800 dark:text-amber-300">
                          <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
                          <div>
                            <span className="font-medium">No title rules for {channelCode} · {localeCode}.</span>{' '}
                            Generation defaults will be used.{' '}
                            <Link to="/settings" className="underline underline-offset-2 hover:no-underline">
                              Configure in Settings → Title Rules
                            </Link>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </>
              )}

              {templateMode === 'clone' && (
                <div className="space-y-2">
                  <Label>Template to clone</Label>
                  <Select value={cloneTemplateId} onValueChange={setCloneTemplateId}>
                    <SelectTrigger className="max-w-md">
                      <SelectValue placeholder="Select template…" />
                    </SelectTrigger>
                    <SelectContent>
                      {templates.map((t) => (
                        <SelectItem key={t.id} value={String(t.id)}>
                          <span className="flex items-center gap-2">
                            <FileText className="w-4 h-4" />
                            {t.locale_code} / {t.channel_code} · #{t.product_type_id} · v{t.version}
                          </span>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {templates.length === 0 && (
                    <p className="text-sm text-muted-foreground">No templates yet.</p>
                  )}
                </div>
              )}
            </div>
          )}

          {/* ── Step 2: Head term ───────────────────────────────────────────── */}
          {step === 'head' && (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">
                The head term is the main product-type label used in every title (e.g. "Receveur de douche", "Shower tray").
                It is looked up per product type and locale at generation time.
              </p>

              <label className="flex items-center gap-3 cursor-pointer rounded-lg border p-3 hover:bg-muted/40 transition-colors">
                <input
                  type="checkbox"
                  checked={includeHeadTerm}
                  onChange={(e) => setIncludeHeadTerm(e.target.checked)}
                  className="rounded"
                />
                <div>
                  <span className="font-medium text-sm">Include head term in title</span>
                  <p className="text-xs text-muted-foreground mt-0.5">Adds the product category name at the start of every title.</p>
                </div>
              </label>

              {/* ── Already-saved head terms (from keyword mapping process) ── */}
              {selectedLocaleObj && parseInt(productTypeId || '0') > 0 && (
                <div className="rounded-lg border bg-card p-4 space-y-3">
                  <div className="flex items-center gap-2 text-sm font-semibold">
                    <Check className="w-4 h-4 text-green-600 shrink-0" />
                    Saved head terms
                    <span className="text-xs font-normal text-muted-foreground ml-1">
                      · {localeCode}{channelCode ? ` · ${channelCode}` : ''}
                    </span>
                    <Link
                      to="/keywords/saved-terms"
                      className="ml-auto text-xs text-muted-foreground underline underline-offset-2 hover:no-underline font-normal"
                    >
                      Manage all →
                    </Link>
                  </div>
                  {savedHeadTerms.length === 0 ? (
                    <p className="text-xs text-muted-foreground">
                      No head terms saved yet for this product type and locale.
                      Approve suggestions below to add them.
                    </p>
                  ) : (
                    <div className="space-y-1.5">
                      {savedHeadTerms.map((t) => (
                        <div key={t.id ?? t.term} className="flex items-center justify-between gap-3 rounded-md border bg-muted/30 px-3 py-2">
                          <div className="flex-1 min-w-0 flex items-center gap-2">
                            <Check className="w-3.5 h-3.5 text-green-600 shrink-0" />
                            <span className="font-medium text-sm">{t.term}</span>
                            {t.source === 'label' && (
                              <span className="text-xs px-1.5 py-0.5 rounded bg-muted text-muted-foreground">default label</span>
                            )}
                          </div>
                          {t.id !== null && t.source !== 'label' && (
                            <Button
                              type="button" variant="ghost" size="icon"
                              className="h-6 w-6 text-muted-foreground hover:text-destructive shrink-0"
                              disabled={removeHeadMutation.isPending}
                              onClick={() => removeHeadMutation.mutate({ productTypeId: parseInt(productTypeId), synonymId: t.id! })}
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </Button>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* ── New suggestions from keyword run ── */}
              {selectedRunId && selectedLocaleObj && parseInt(productTypeId || '0') > 0 && (
                <div className="rounded-lg border bg-muted/30 p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-sm font-medium">
                      <Sparkles className="w-4 h-4 text-muted-foreground shrink-0" />
                      New suggestions from keyword run #{selectedRunId}
                    </div>
                    <Button type="button" variant="secondary" size="sm" disabled={suggestedTermsFetching} onClick={() => refetchSuggestedTerms()}>
                      {suggestedTermsFetching && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                      {suggestedTermsData ? 'Refresh' : 'Load suggestions'}
                    </Button>
                  </div>

                  {!suggestedTermsData && !suggestedTermsFetching && (
                    <p className="text-xs text-muted-foreground">
                      Load to see additional head terms extracted from keyword data — approve the ones you want to add.
                    </p>
                  )}

                  {suggestedTermsData && (() => {
                    // Hide suggestions already saved
                    const savedSet = new Set(savedHeadTerms.map((t) => t.term.toLowerCase()));
                    const newSuggestions = suggestedTermsData.suggested_head_terms.filter(
                      (h) => !savedSet.has(h.term.toLowerCase())
                    );
                    if (newSuggestions.length === 0) {
                      return <p className="text-xs text-muted-foreground">All suggestions are already saved.</p>;
                    }
                    return (
                      <div className="space-y-1.5">
                        {newSuggestions.map((h: SuggestedHeadTerm) => (
                          <div key={h.keyword_id} className="flex items-center justify-between gap-3 rounded-md border bg-card px-3 py-2">
                            <div className="flex-1 min-w-0">
                              <span className="font-medium text-sm">{h.term}</span>
                              {h.avg_searches > 0 && (
                                <span className="ml-2 text-xs text-muted-foreground tabular-nums">{h.avg_searches.toLocaleString()} / mo</span>
                              )}
                              {h.meaning_en && (
                                <p className="text-xs text-muted-foreground italic mt-0.5">{h.meaning_en}</p>
                              )}
                            </div>
                            {approvedHeadIds.has(h.keyword_id) ? (
                              <Badge className="bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 shrink-0">
                                <Check className="w-3 h-3 mr-1" /> Saved
                              </Badge>
                            ) : (
                              <Button
                                type="button" size="sm" variant="outline"
                                className="shrink-0 h-7 text-xs"
                                disabled={addHeadMutation.isPending}
                                onClick={() => addHeadMutation.mutate(h.term, {
                                  onSuccess: () => setApprovedHeadIds((prev) => new Set(prev).add(h.keyword_id)),
                                })}
                              >
                                Approve
                              </Button>
                            )}
                          </div>
                        ))}
                      </div>
                    );
                  })()}
                </div>
              )}

              {!selectedLocaleObj && (
                <p className="text-xs text-muted-foreground border rounded p-3">
                  Go back to Step 1 and select a locale to see saved and suggested head terms.
                </p>
              )}
            </div>
          )}

          {/* ── Step 3: Hook term ───────────────────────────────────────────── */}
          {step === 'hook' && (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">
                The hook term is a short per-product differentiator — colour, material, style, finish, etc.
                Each product has its own hook term saved per locale.
              </p>

              <label className="flex items-center gap-3 cursor-pointer rounded-lg border p-3 hover:bg-muted/40 transition-colors">
                <input
                  type="checkbox"
                  checked={includeHookTerm}
                  onChange={(e) => setIncludeHookTerm(e.target.checked)}
                  className="rounded"
                />
                <div>
                  <span className="font-medium text-sm">Include hook term slot in title</span>
                  <p className="text-xs text-muted-foreground mt-0.5">Adds a per-product differentiator right after the head term.</p>
                </div>
              </label>

              {/* ── Already-saved hook terms ── */}
              {selectedLocaleObj && (
                <div className="rounded-lg border bg-card p-4 space-y-3">
                  <div className="flex items-center gap-2 text-sm font-semibold">
                    <Check className="w-4 h-4 text-green-600 shrink-0" />
                    Saved hook terms
                    <span className="text-xs font-normal text-muted-foreground ml-1">
                      · {localeCode}{channelCode ? ` · ${channelCode}` : ''}
                    </span>
                    <Link
                      to="/keywords/saved-terms"
                      className="ml-auto text-xs text-muted-foreground underline underline-offset-2 hover:no-underline font-normal"
                    >
                      Manage all →
                    </Link>
                  </div>
                  {savedHookTermsByProduct.length === 0 ? (
                    <p className="text-xs text-muted-foreground">
                      No hook terms saved yet for this locale. Approve suggestions below to add them.
                    </p>
                  ) : (
                    <div className="space-y-2 max-h-64 overflow-auto pr-1">
                      {savedHookTermsByProduct.map((group) => (
                        <div key={group.product_id} className="border rounded-md overflow-hidden bg-muted/20">
                          <div className="px-3 py-1.5 bg-muted/40 border-b text-xs font-medium text-muted-foreground">
                            {group.default_label || group.product_code || `Product ${group.product_id}`}
                          </div>
                          <div className="divide-y">
                            {group.terms.map((t) => (
                              <div key={t.id} className="flex items-center gap-2 px-3 py-1.5">
                                <Check className="w-3 h-3 text-green-600 shrink-0" />
                                <span className="text-sm flex-1">{t.term}</span>
                                <Button
                                  type="button" variant="ghost" size="icon"
                                  className="h-6 w-6 text-muted-foreground hover:text-destructive shrink-0"
                                  disabled={removeHookMutation.isPending}
                                  onClick={() => removeHookMutation.mutate({ productId: group.product_id, hookTermId: t.id })}
                                >
                                  <Trash2 className="w-3 h-3" />
                                </Button>
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* ── New suggestions from keyword run ── */}
              {selectedRunId && selectedLocaleObj && (
                <div className="rounded-lg border bg-muted/30 p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-sm font-medium">
                      <Sparkles className="w-4 h-4 text-muted-foreground shrink-0" />
                      New suggestions from keyword run #{selectedRunId}
                    </div>
                    {!suggestedTermsData && (
                      <Button type="button" variant="secondary" size="sm" disabled={suggestedTermsFetching} onClick={() => refetchSuggestedTerms()}>
                        {suggestedTermsFetching && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                        Load suggestions
                      </Button>
                    )}
                  </div>

                  {!suggestedTermsData && !suggestedTermsFetching && (
                    <p className="text-xs text-muted-foreground">Load to see hook terms grouped by product — colour, material, and other differentiators not yet saved.</p>
                  )}

                  {suggestedTermsData && (() => {
                    // Build set of already-saved terms per product to filter out duplicates
                    const savedByProduct = new Map<number, Set<string>>(
                      savedHookTermsByProduct.map((g) => [g.product_id, new Set(g.terms.map((t) => t.term.toLowerCase()))])
                    );
                    const hookTerms = suggestedTermsData.suggested_hook_terms.filter(
                      (h) => !savedByProduct.get(h.product_id)?.has(h.term.toLowerCase())
                    );
                    if (hookTerms.length === 0) {
                      return <p className="text-xs text-muted-foreground">All suggestions are already saved.</p>;
                    }
                    const byProduct = hookTerms.reduce<Record<number, SuggestedHookTerm[]>>((acc, h) => {
                      if (!acc[h.product_id]) acc[h.product_id] = [];
                      acc[h.product_id].push(h);
                      return acc;
                    }, {});
                    return (
                      <div className="space-y-3 max-h-80 overflow-auto pr-1">
                        {Object.entries(byProduct).map(([pidStr, terms]) => {
                          const pid = Number(pidStr);
                          const disp = terms[0]?.product_display;
                          const label = disp?.default_label || disp?.variant_source_title || `Product ${pid}`;
                          return (
                            <div key={pid} className="border rounded-md overflow-hidden bg-card">
                              <div className="px-3 py-2 bg-muted/40 border-b text-xs font-medium text-muted-foreground">
                                {label}
                              </div>
                              <div className="divide-y">
                                {terms.map((h: SuggestedHookTerm) => {
                                  const hookKey = `${h.keyword_id}-${h.product_id}`;
                                  const attrLabel = h.attribute_label || h.attribute_code || h.match_kind;
                                  return (
                                    <div key={hookKey} className="flex items-center justify-between gap-3 px-3 py-2">
                                      <div className="flex-1 min-w-0">
                                        <span className="font-medium text-sm">{h.term}</span>
                                        {attrLabel && (
                                          <span className="ml-2 text-xs px-1.5 py-0.5 rounded bg-muted text-muted-foreground">{attrLabel}</span>
                                        )}
                                        {h.avg_searches > 0 && (
                                          <span className="ml-2 text-xs text-muted-foreground tabular-nums">{h.avg_searches.toLocaleString()} / mo</span>
                                        )}
                                      </div>
                                      {approvedHookKeys.has(hookKey) ? (
                                        <Badge className="bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 shrink-0 text-xs">
                                          <Check className="w-3 h-3 mr-1" /> Saved
                                        </Badge>
                                      ) : (
                                        <Button
                                          type="button" size="sm" variant="outline"
                                          className="shrink-0 h-7 text-xs"
                                          disabled={addHookMutation.isPending}
                                          onClick={() => addHookMutation.mutate({ productId: pid, term: h.term }, {
                                            onSuccess: () => setApprovedHookKeys((prev) => new Set(prev).add(hookKey)),
                                          })}
                                        >
                                          Approve
                                        </Button>
                                      )}
                                    </div>
                                  );
                                })}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    );
                  })()}
                </div>
              )}

              {!selectedLocaleObj && (
                <p className="text-xs text-muted-foreground border rounded p-3">
                  Go back to Step 1 and select a locale to see saved and suggested hook terms.
                </p>
              )}
            </div>
          )}

          {/* ── Step 4: Attributes ──────────────────────────────────────────── */}
          {step === 'attributes' && (
            <div className="space-y-5">
              <p className="text-sm text-muted-foreground">
                The title always starts with the <strong>head term</strong> (position 1) and the <strong>variation axis</strong> (position 2, fixed).
                Choose additional attributes for positions 3+ below — AI can suggest the best ones from your keyword data.
              </p>

              {/* Fixed structure preview */}
              <div className="rounded-lg border bg-muted/20 divide-y">
                <div className="flex items-center gap-3 px-3 py-2 opacity-60">
                  <span className="text-xs font-mono w-4 text-muted-foreground">1</span>
                  <span className="text-xs px-2 py-0.5 rounded bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400 font-medium">Head term</span>
                  <span className="text-xs text-muted-foreground ml-auto">fixed</span>
                </div>
                {axisAttributes.length > 0 ? (
                  axisAttributes.map((a, i) => (
                    <div key={a.attribute_id} className="flex items-center gap-3 px-3 py-2 opacity-60">
                      <span className="text-xs font-mono w-4 text-muted-foreground">{i + 2}</span>
                      <span className="text-xs px-2 py-0.5 rounded bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400 font-medium font-mono">{a.attribute_code}</span>
                      <span className="text-xs text-muted-foreground">variation axis</span>
                      <span className="text-xs text-muted-foreground ml-auto">fixed</span>
                    </div>
                  ))
                ) : (
                  <div className="flex items-center gap-3 px-3 py-2 opacity-40">
                    <span className="text-xs font-mono w-4 text-muted-foreground">2</span>
                    <span className="text-xs px-2 py-0.5 rounded bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400 font-medium">Hook term</span>
                    <span className="text-xs text-muted-foreground ml-auto">fixed — use "Suggest attributes" to detect variation axis</span>
                  </div>
                )}
              </div>

              {/* AI suggest panel */}
              <div className="rounded-lg border bg-muted/30 p-4 space-y-3">
                <div className="flex items-center gap-2 text-sm font-medium">
                  <Sparkles className="w-4 h-4 text-muted-foreground shrink-0" />
                  AI attribute suggestions for positions 3+
                </div>
                {selectedRunId ? (
                  <>
                    <p className="text-xs text-muted-foreground">
                      Using <strong>Run #{selectedRunId}</strong>. AI picks the best attributes for positions 3+ from your keyword data, skipping the fixed head and axis slots.
                    </p>
                    <div className="flex gap-2 flex-wrap items-center">
                      <label className="flex items-center gap-1.5 text-sm cursor-pointer select-none">
                        <input
                          type="checkbox"
                          checked={useAiPropose}
                          onChange={(e) => setUseAiPropose(e.target.checked)}
                          className="rounded"
                        />
                        <span>Use AI to semantically reorder</span>
                        <span className="text-xs text-muted-foreground">(adapts to product type &amp; locale)</span>
                      </label>
                      <Button type="button" variant="secondary" size="sm" disabled={proposing} onClick={handlePropose}>
                        {proposing && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                        <Sparkles className="w-3.5 h-3.5 mr-1.5" />
                        Suggest attributes
                      </Button>
                    </div>
                    {proposedAttrs.length > 0 && proposedAttrs.some((p) => p.reason) && (
                      <div className="space-y-1 border-t pt-3">
                        <p className="text-xs font-medium text-muted-foreground">AI reasoning:</p>
                        {proposedAttrs.filter((p) => p.reason).map((p) => (
                          <div key={p.attribute_id} className="text-xs text-muted-foreground">
                            <span className="font-mono font-medium text-foreground">{p.attribute_code}</span>
                            {' — '}{p.reason}
                          </div>
                        ))}
                      </div>
                    )}
                  </>
                ) : (
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-xs text-muted-foreground">No keyword run selected. Go back to Step 1 to pick one.</p>
                    <Button type="button" variant="ghost" size="sm" onClick={() => setStep('template')}>
                      <ArrowLeft className="w-3.5 h-3.5 mr-1" /> Step 1
                    </Button>
                  </div>
                )}
              </div>

              {/* Add attributes manually */}
              <div className="space-y-2">
                <Label className="text-sm">Add attributes manually (positions 3+)</Label>
                <div className="flex flex-wrap gap-2">
                  {attributes
                    .filter((a) => !selectedAttributeIds.includes(a.id) && !axisAttributes.some((ax) => ax.attribute_id === a.id))
                    .map((a) => (
                      <Button key={a.id} type="button" variant="outline" size="sm" onClick={() => addAttribute(a.id)}>
                        + {a.code}
                      </Button>
                    ))}
                  {attributes.filter((a) => !selectedAttributeIds.includes(a.id) && !axisAttributes.some((ax) => ax.attribute_id === a.id)).length === 0 && (
                    <span className="text-sm text-muted-foreground">All attributes added.</span>
                  )}
                </div>
              </div>

              {/* Ordered list for positions 3+ */}
              <div className="space-y-2">
                <Label>Additional attributes (positions {axisAttributes.length + 2}+)</Label>
                {selectedAttributeIds.length > 0 ? (
                  <ul className="space-y-1 border rounded-md divide-y">
                    {selectedAttributeIds.map((id, index) => {
                      const attr = attributes.find((a) => a.id === id);
                      const reason = proposedAttrs.find((p) => p.attribute_id === id)?.reason;
                      const position = axisAttributes.length + 2 + index;
                      return (
                        <li key={id} className="flex items-center gap-2 px-3 py-2 bg-card group">
                          <span className="text-xs font-mono w-4 text-muted-foreground shrink-0">{position}</span>
                          <div className="flex flex-col gap-0.5">
                            <Button type="button" variant="ghost" size="icon" className="h-6 w-6" onClick={() => moveAttribute(index, -1)} disabled={index === 0}>
                              <span className="text-xs">↑</span>
                            </Button>
                            <Button type="button" variant="ghost" size="icon" className="h-6 w-6" onClick={() => moveAttribute(index, 1)} disabled={index === selectedAttributeIds.length - 1}>
                              <span className="text-xs">↓</span>
                            </Button>
                          </div>
                          <GripVertical className="w-4 h-4 text-muted-foreground" />
                          <div className="flex-1 min-w-0">
                            <span className="font-mono text-sm">{attr?.code ?? id}</span>
                            {reason && <p className="text-xs text-muted-foreground italic mt-0.5">{reason}</p>}
                          </div>
                          <Button type="button" variant="ghost" size="sm" className="text-muted-foreground hover:text-destructive opacity-0 group-hover:opacity-100 transition-opacity" onClick={() => removeAttribute(id)}>
                            Remove
                          </Button>
                        </li>
                      );
                    })}
                  </ul>
                ) : (
                  <p className="text-sm text-muted-foreground py-4 text-center border rounded-md border-dashed">
                    No additional attributes yet. Use "Suggest attributes" or add them manually above.
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Navigation */}
          <div className="flex justify-between pt-4 border-t">
            <Button variant="outline" onClick={handleBack} disabled={stepIndex === 0}>
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back
            </Button>
            {canSubmit ? (
              <Button onClick={handleNext} disabled={createMutation.isPending || (!includeHeadTerm && axisAttributes.length === 0 && selectedAttributeIds.length === 0)}>
                {createMutation.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                Create template
                <Check className="w-4 h-4 ml-2" />
              </Button>
            ) : (
              <Button onClick={handleNext} disabled={!canNext}>
                Next
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
