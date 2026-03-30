import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, FileText, Pencil, Trash2, CheckCircle2, Sparkles, Loader2, ArrowRight, Info } from 'lucide-react';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import {
  getTemplates,
  getProductTypes,
  getChannels,
  getLocales,
  getPlannerRuns,
  deleteTemplate,
  updateTemplate,
  quickCreateTemplate,
  getApiErrorMessage,
  Template,
  ProductType,
  Channel,
  Locale,
  PlannerRun,
  QuickCreateTemplateResponse,
} from '@/lib/api';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/hooks/use-toast';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';

const AI_MODELS_QUICK = [
  { value: 'gpt-4o-mini', label: 'GPT-4o mini (fast)' },
  { value: 'gpt-4o', label: 'GPT-4o (best)' },
  { value: 'claude-haiku-4-5-20251001', label: 'Claude Haiku (fast)' },
  { value: 'claude-sonnet-4-6', label: 'Claude Sonnet (best)' },
  { value: 'gemini-2.0-flash', label: 'Gemini Flash (fast)' },
  { value: 'gemini-1.5-pro', label: 'Gemini Pro (best)' },
];

export default function TemplatesList() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [filterProductTypeId, setFilterProductTypeId] = useState<string>('all');
  const [filterChannelCode, setFilterChannelCode] = useState<string>('all');
  const [filterLocaleCode, setFilterLocaleCode] = useState<string>('all');
  const [deleteId, setDeleteId] = useState<number | null>(null);

  // Quick-create dialog state
  const [quickOpen, setQuickOpen] = useState(false);
  const [qProductTypeId, setQProductTypeId] = useState('');
  const [qChannelCode, setQChannelCode] = useState('');
  const [qLocaleCode, setQLocaleCode] = useState('');
  const [qRunId, setQRunId] = useState('__none__');
  const [qAiModel, setQAiModel] = useState('gpt-4o-mini');
  const [qResult, setQResult] = useState<QuickCreateTemplateResponse | null>(null);

  const { data: templatesData, isLoading } = useQuery({
    queryKey: ['templates', filterProductTypeId, filterChannelCode, filterLocaleCode],
    queryFn: () =>
      getTemplates({
        page: 1,
        page_size: 200,
        ...(filterProductTypeId !== 'all' && { product_type_id: parseInt(filterProductTypeId) }),
        ...(filterChannelCode !== 'all' && { channel_code: filterChannelCode }),
        ...(filterLocaleCode !== 'all' && { locale_code: filterLocaleCode }),
      }),
  });

  const { data: productTypesData } = useQuery({
    queryKey: ['product-types'],
    queryFn: () => getProductTypes(),
  });
  const { data: channelsData } = useQuery({
    queryKey: ['channels'],
    queryFn: () => getChannels(),
  });
  const { data: localesData } = useQuery({
    queryKey: ['locales'],
    queryFn: () => getLocales(),
  });
  const { data: plannerRunsData } = useQuery({
    queryKey: ['planner-runs-quick'],
    queryFn: () => getPlannerRuns({ page_size: 100 }),
    enabled: quickOpen,
  });

  const quickCreateMutation = useMutation({
    mutationFn: quickCreateTemplate,
    onSuccess: (data) => {
      setQResult(data);
      queryClient.invalidateQueries({ queryKey: ['templates'] });
    },
    onError: (err: unknown) => {
      toast({ title: 'Failed to create template', description: getApiErrorMessage(err), variant: 'destructive' });
    },
  });

  const handleQuickCreate = () => {
    if (!qProductTypeId || !qChannelCode || !qLocaleCode) return;
    setQResult(null);
    quickCreateMutation.mutate({
      product_type_id: parseInt(qProductTypeId),
      channel_code: qChannelCode,
      locale_code: qLocaleCode,
      run_id: qRunId && qRunId !== '__none__' ? parseInt(qRunId) : null,
      ai_model: qAiModel,
    });
  };

  const resetQuickDialog = () => {
    setQProductTypeId('');
    setQChannelCode('');
    setQLocaleCode('');
    setQRunId('__none__');
    setQAiModel('gpt-4o-mini');
    setQResult(null);
    quickCreateMutation.reset();
  };

  const activateMutation = useMutation({
    mutationFn: async (t: Template) => {
      // Archive the current active template for this scope first
      const currentActive = templates.find(
        (x) =>
          x.status === 'active' &&
          x.product_type_id === t.product_type_id &&
          x.channel_code === t.channel_code &&
          x.locale_code === t.locale_code &&
          x.id !== t.id,
      );
      if (currentActive) {
        await updateTemplate(currentActive.id, { status: 'archived' });
      }
      return updateTemplate(t.id, { status: 'active' });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['templates'] });
      toast({ title: 'Template activated' });
    },
    onError: (err: unknown) => {
      toast({ title: 'Failed to activate', description: getApiErrorMessage(err), variant: 'destructive' });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteTemplate(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['templates'] });
      setDeleteId(null);
      toast({ title: 'Template deleted' });
    },
    onError: (err: unknown) => {
      toast({
        title: 'Cannot delete template',
        description: getApiErrorMessage(err),
        variant: 'destructive',
      });
    },
  });

  const templates = templatesData?.results ?? [];
  const productTypes = (productTypesData?.results ?? []) as ProductType[];
  const channels = (channelsData?.results ?? []) as Channel[];
  const locales = (localesData?.results ?? []) as Locale[];
  const plannerRuns = ((plannerRunsData?.results ?? []) as PlannerRun[]).filter(r => r.status === 'success');

  // Client-side filter if backend doesn't filter
  const filtered = templates.filter((t: Template) => {
    if (filterProductTypeId !== 'all' && t.product_type_id !== parseInt(filterProductTypeId)) return false;
    if (filterChannelCode !== 'all' && t.channel_code !== filterChannelCode) return false;
    if (filterLocaleCode !== 'all' && t.locale_code !== filterLocaleCode) return false;
    return true;
  });

  return (
    <div className="page-container">
      <PageHeader
        title="Title templates"
        description="Build templates with head term, hook term, and attributes for title generation."
        breadcrumbs={[
          { label: 'Dashboard', href: '/' },
          { label: 'Templates' },
        ]}
        actions={
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => { resetQuickDialog(); setQuickOpen(true); }}>
              <Sparkles className="w-4 h-4 mr-2" />
              Create with AI
            </Button>
            <Button asChild>
              <Link to="/templates/new">
                <Plus className="w-4 h-4 mr-2" />
                Create manually
              </Link>
            </Button>
          </div>
        }
      />

      <Card>
        <CardHeader>
          <CardTitle>Templates</CardTitle>
          <CardDescription>Filter by product type, channel, or locale.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Product type</label>
              <Select value={filterProductTypeId} onValueChange={setFilterProductTypeId}>
                <SelectTrigger className="w-[200px]">
                  <SelectValue placeholder="All" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All</SelectItem>
                  {productTypes.map((pt) => (
                    <SelectItem key={pt.id} value={String(pt.id)}>
                      {pt.code}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Channel</label>
              <Select value={filterChannelCode} onValueChange={setFilterChannelCode}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="All" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All</SelectItem>
                  {channels.map((c) => (
                    <SelectItem key={c.id} value={c.code}>
                      {c.code}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Locale</label>
              <Select value={filterLocaleCode} onValueChange={setFilterLocaleCode}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="All" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All</SelectItem>
                  {locales.map((loc) => (
                    <SelectItem key={loc.code} value={loc.code}>
                      {loc.name || loc.code} ({loc.code})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {isLoading ? (
            <p className="text-sm text-muted-foreground">Loading templates...</p>
          ) : filtered.length === 0 ? (
            <p className="text-sm text-muted-foreground">No templates found. Create one to get started.</p>
          ) : (
            <ul className="divide-y rounded-md border">
              {filtered.map((t: Template) => (
                <li key={t.id} className="flex items-center justify-between px-4 py-3">
                  <div className="flex items-center gap-3">
                    <FileText className="w-4 h-4 text-muted-foreground" />
                    <div>
                      <span className="font-medium">
                        {t.locale_code} / {t.channel_code}
                      </span>
                      <span className="text-muted-foreground ml-2">
                        product type #{t.product_type_id} · v{t.version}
                      </span>
                      <Badge
                        variant={t.status === 'active' ? 'default' : t.status === 'draft' ? 'secondary' : 'outline'}
                        className="ml-2 text-xs"
                      >
                        {t.status}
                      </Badge>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {t.status === 'draft' && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => activateMutation.mutate(t)}
                        disabled={activateMutation.isPending}
                      >
                        <CheckCircle2 className="w-4 h-4 mr-1" />
                        Activate
                      </Button>
                    )}
                    <Button variant="outline" size="sm" asChild>
                      <Link to={`/templates/${t.id}/edit`}>
                        <Pencil className="w-4 h-4 mr-1" />
                        Edit
                      </Link>
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      asChild
                    >
                      <a
                        href={`/admin/pub/generationrun/?template__id__exact=${t.id}`}
                        target="_blank"
                        rel="noreferrer"
                        title="Open generation runs for this template in admin"
                      >
                        Runs
                      </a>
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-destructive hover:text-destructive"
                      onClick={() => setDeleteId(t.id)}
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      {/* ── Quick Create with AI Dialog ───────────────────────────────────── */}
      <Dialog open={quickOpen} onOpenChange={(open) => { setQuickOpen(open); if (!open) resetQuickDialog(); }}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-primary" />
              Create template with AI
            </DialogTitle>
            <DialogDescription>
              AI will pick and order the best attributes for your title structure.
              Works for any product type and language — no keyword run required.
            </DialogDescription>
          </DialogHeader>

          {!qResult ? (
            <div className="space-y-4 py-2">
              {/* Product type */}
              <div className="space-y-1.5">
                <Label>Product type <span className="text-destructive">*</span></Label>
                <Select value={qProductTypeId} onValueChange={setQProductTypeId}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select product type…" />
                  </SelectTrigger>
                  <SelectContent>
                    {productTypes.map((pt) => (
                      <SelectItem key={pt.id} value={String(pt.id)}>
                        {pt.default_label ? `${pt.default_label} (${pt.code})` : pt.code}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Channel + Locale side by side */}
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label>Channel <span className="text-destructive">*</span></Label>
                  <Select value={qChannelCode} onValueChange={setQChannelCode}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select…" />
                    </SelectTrigger>
                    <SelectContent>
                      {channels.map((c) => (
                        <SelectItem key={c.id} value={c.code}>{c.name || c.code}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label>Language / Locale <span className="text-destructive">*</span></Label>
                  <Select value={qLocaleCode} onValueChange={setQLocaleCode}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select…" />
                    </SelectTrigger>
                    <SelectContent>
                      {locales.map((l) => (
                        <SelectItem key={l.code} value={l.code}>{l.name || l.code}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Keyword run (optional) */}
              <div className="space-y-1.5">
                <Label className="flex items-center gap-1.5">
                  Keyword run
                  <span className="text-xs text-muted-foreground font-normal">(optional — improves attribute ranking)</span>
                </Label>
                <Select value={qRunId} onValueChange={setQRunId}>
                  <SelectTrigger>
                    <SelectValue placeholder="No run — use product type attributes" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__none__">No run — use product type attributes</SelectItem>
                    {plannerRuns.map((r) => (
                      <SelectItem key={r.id} value={String(r.id)}>
                        #{r.id} · {r.product_type_code ?? 'all types'} · {r.locale_code} · {r.keyword_count.toLocaleString()} keywords
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* AI model */}
              <div className="space-y-1.5">
                <Label>AI model</Label>
                <Select value={qAiModel} onValueChange={setQAiModel}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {AI_MODELS_QUICK.map((m) => (
                      <SelectItem key={m.value} value={m.value}>{m.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Fixed structure info */}
              <div className="rounded-md bg-muted/40 border px-3 py-2 flex items-start gap-2 text-xs text-muted-foreground">
                <Info className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                <span>Structure is always: <strong>Head term → Hook term → Variation axis (set per listing) → AI-picked attributes</strong>. You can edit the result after creation.</span>
              </div>
            </div>
          ) : (
            /* ── Result view ──────────────────────────────────────────────── */
            <div className="space-y-4 py-2">
              <div className="rounded-lg border bg-green-50 dark:bg-green-950/20 border-green-200 dark:border-green-800 p-4">
                <p className="text-sm font-medium text-green-800 dark:text-green-300 mb-2">
                  Template created {qResult.source === 'ai' ? 'with AI' : qResult.source === 'volume' ? 'from keyword data' : 'from product type'}
                </p>
                <div className="flex flex-wrap items-center gap-1 text-sm">
                  {qResult.structure.map((part, i) => {
                    // i=0: Head term (blue), i=1: Hook term (purple), i=2: Axis (orange), rest: AI attrs (mono)
                    const isHead = i === 0;
                    const isHook = i === 1;
                    const isAxis = i === 2;
                    return (
                      <span key={i} className="flex items-center gap-1">
                        {i > 0 && <span className="text-muted-foreground/50">–</span>}
                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                          isHead ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' :
                          isHook ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400' :
                          isAxis ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400' :
                          'bg-muted text-foreground font-mono'
                        }`}>{part}</span>
                      </span>
                    );
                  })}
                </div>
              </div>

              {qResult.attributes.length > 0 && qResult.attributes.some(a => a.reason) && (
                <div className="space-y-1.5">
                  <p className="text-xs font-medium text-muted-foreground">AI reasoning:</p>
                  {qResult.attributes.filter(a => a.reason).map((a) => (
                    <div key={a.attribute_code} className="text-xs text-muted-foreground">
                      <span className="font-mono font-medium text-foreground">{a.attribute_code}</span>
                      {' — '}{a.reason}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          <DialogFooter className="gap-2">
            {!qResult ? (
              <>
                <Button variant="outline" onClick={() => setQuickOpen(false)}>Cancel</Button>
                <Button
                  onClick={handleQuickCreate}
                  disabled={!qProductTypeId || !qChannelCode || !qLocaleCode || quickCreateMutation.isPending}
                >
                  {quickCreateMutation.isPending ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Creating…
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4 mr-2" />
                      Create template
                    </>
                  )}
                </Button>
              </>
            ) : (
              <>
                <Button variant="outline" onClick={() => { resetQuickDialog(); }}>
                  Create another
                </Button>
                <Button onClick={() => { setQuickOpen(false); navigate(`/templates/${qResult.template_id}/edit`); }}>
                  Review &amp; edit
                  <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              </>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <AlertDialog open={deleteId !== null} onOpenChange={(open) => !open && setDeleteId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete template?</AlertDialogTitle>
            <AlertDialogDescription>
              This will delete the template and all its parts. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() => deleteId != null && deleteMutation.mutate(deleteId)}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
