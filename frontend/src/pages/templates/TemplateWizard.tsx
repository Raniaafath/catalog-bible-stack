import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, ArrowRight, Check, FileText, Loader2, GripVertical } from 'lucide-react';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
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
  createTemplate,
  createTemplatePart,
  Template,
  ProductType,
  Channel,
  Locale,
  Attribute,
} from '@/lib/api';
import { useToast } from '@/hooks/use-toast';

const STEPS = [
  { id: 'template', title: 'Choose template', description: 'Scope or clone from existing' },
  { id: 'head', title: 'Head term', description: 'Product-type term (e.g. product category)' },
  { id: 'hook', title: 'Hook term', description: 'Differentiator (e.g. colour, material)' },
  { id: 'attributes', title: 'Needed attributes', description: 'Attributes to show in title (order)' },
] as const;

type StepId = (typeof STEPS)[number]['id'];

export default function TemplateWizard() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [step, setStep] = useState<StepId>('template');

  // Pre-fill from URL params (e.g. from Groups → Create template manually)
  const urlProductTypeId = searchParams.get('product_type_id') ?? '';
  const urlChannelCode = searchParams.get('channel_code') ?? '';
  const urlLocaleCode = searchParams.get('locale_code') ?? '';

  // Step 1: template choice
  const [templateMode, setTemplateMode] = useState<'new' | 'clone'>('new');
  const [productTypeId, setProductTypeId] = useState<string>(urlProductTypeId);
  const [channelCode, setChannelCode] = useState<string>(urlChannelCode);
  const [localeCode, setLocaleCode] = useState<string>(urlLocaleCode);
  const [cloneTemplateId, setCloneTemplateId] = useState<string>('');

  // Step 2 & 3: include head/hook (we always include them; step is to confirm)
  const [includeHeadTerm, setIncludeHeadTerm] = useState(true);
  const [includeHookTerm, setIncludeHookTerm] = useState(true);

  // Step 4: attributes (ordered list of attribute ids)
  const [selectedAttributeIds, setSelectedAttributeIds] = useState<number[]>([]);

  const { data: templatesData } = useQuery({
    queryKey: ['templates'],
    queryFn: () => getTemplates({ page_size: 200 }),
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
  const { data: attributesData } = useQuery({
    queryKey: ['attributes'],
    queryFn: () => getAttributes({ page_size: 200 }),
  });

  const templates = (templatesData?.results ?? []) as Template[];
  const productTypes = (productTypesData?.results ?? []) as ProductType[];
  const channels = (channelsData?.results ?? []) as Channel[];
  const locales = (localesData?.results ?? []) as Locale[];
  const attributes = (attributesData?.results ?? []) as Attribute[];

  const createMutation = useMutation({
    mutationFn: async () => {
      let scope = { product_type_id: 0, channel_code: '', locale_code: '' };
      if (templateMode === 'clone' && cloneTemplateId) {
        const t = templates.find((x) => x.id === parseInt(cloneTemplateId));
        if (t) scope = { product_type_id: t.product_type_id, channel_code: t.channel_code, locale_code: t.locale_code };
      } else {
        scope = {
          product_type_id: parseInt(productTypeId),
          channel_code: channelCode,
          locale_code: localeCode,
        };
      }
      const template = await createTemplate(scope);
      const parts: { part_type: string; literal_text?: string; attribute_id?: number | null }[] = [];
      let pos = 0;
      if (includeHeadTerm) {
        parts.push({ part_type: 'head_term' });
        pos++;
      }
      if (includeHeadTerm && includeHookTerm) {
        parts.push({ part_type: 'literal', literal_text: ' - ' });
        pos++;
      }
      if (includeHookTerm) {
        parts.push({ part_type: 'hook_term' });
        pos++;
      }
      for (const attrId of selectedAttributeIds) {
        parts.push({ part_type: 'literal', literal_text: ' - ' });
        parts.push({ part_type: 'axis_attribute', attribute_id: attrId });
        pos += 2;
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
      toast({
        title: 'Failed to create template',
        description: String((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail),
        variant: 'destructive',
      });
    },
  });

  const stepIndex = STEPS.findIndex((s) => s.id === step);
  const canNext =
    step === 'template'
      ? templateMode === 'clone'
        ? !!cloneTemplateId
        : !!(productTypeId && channelCode && localeCode)
      : step === 'head'
        ? true
        : step === 'hook'
          ? true
          : true;
  const canSubmit = step === 'attributes';

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
    const t = arr[index];
    arr[index] = arr[next];
    arr[next] = t;
    setSelectedAttributeIds(arr);
  };

  return (
    <div className="page-container">
      <PageHeader
        title="Create template"
        description="Choose the template scope, then head term, hook term, and needed attributes."
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
        {STEPS.map((s, i) => (
          <button
            key={s.id}
            type="button"
            onClick={() => setStep(s.id)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
              step === s.id
                ? 'bg-primary text-primary-foreground'
                : i < stepIndex
                  ? 'bg-muted text-muted-foreground'
                  : 'bg-muted/60 text-muted-foreground hover:bg-muted'
            }`}
          >
            {i < stepIndex ? <Check className="w-4 h-4" /> : null}
            {s.title}
          </button>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{STEPS[stepIndex].title}</CardTitle>
          <CardDescription>{STEPS[stepIndex].description}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Step 1: Choose template */}
          {step === 'template' && (
            <div className="space-y-6">
              <div className="flex gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="templateMode"
                    checked={templateMode === 'new'}
                    onChange={() => setTemplateMode('new')}
                    className="rounded border-input"
                  />
                  <span>Create new (choose scope)</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="templateMode"
                    checked={templateMode === 'clone'}
                    onChange={() => setTemplateMode('clone')}
                    className="rounded border-input"
                  />
                  <span>Clone from existing template</span>
                </label>
              </div>
              {templateMode === 'new' && (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <Label>Product type</Label>
                    <Select value={productTypeId} onValueChange={setProductTypeId}>
                      <SelectTrigger>
                        <SelectValue placeholder="Select..." />
                      </SelectTrigger>
                      <SelectContent>
                        {productTypes.map((pt) => (
                          <SelectItem key={pt.id} value={String(pt.id)}>
                            {pt.code}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Channel</Label>
                    <Select value={channelCode} onValueChange={setChannelCode}>
                      <SelectTrigger>
                        <SelectValue placeholder="Select..." />
                      </SelectTrigger>
                      <SelectContent>
                        {channels.map((c) => (
                          <SelectItem key={c.id} value={c.code}>
                            {c.code}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Locale</Label>
                    <Select value={localeCode} onValueChange={setLocaleCode}>
                      <SelectTrigger>
                        <SelectValue placeholder="Select..." />
                      </SelectTrigger>
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
              )}
              {templateMode === 'clone' && (
                <div className="space-y-2">
                  <Label>Template to clone</Label>
                  <Select value={cloneTemplateId} onValueChange={setCloneTemplateId}>
                    <SelectTrigger className="max-w-md">
                      <SelectValue placeholder="Select template..." />
                    </SelectTrigger>
                    <SelectContent>
                      {templates.map((t) => (
                        <SelectItem key={t.id} value={String(t.id)}>
                          <span className="flex items-center gap-2">
                            <FileText className="w-4 h-4" />
                            {t.locale_code} / {t.channel_code} · product type #{t.product_type_id} · v{t.version}
                          </span>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {templates.length === 0 && (
                    <p className="text-sm text-muted-foreground">No templates yet. Create new with scope above.</p>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Step 2: Head term */}
          {step === 'head' && (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">
                The head term is the main product-type label (e.g. &quot;Shower tray&quot;, &quot;Duschwanne&quot;). It is
                resolved from the product type and locale when generating titles.
              </p>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={includeHeadTerm}
                  onChange={(e) => setIncludeHeadTerm(e.target.checked)}
                  className="rounded border-input"
                />
                <span>Include head term in template</span>
              </label>
            </div>
          )}

          {/* Step 3: Hook term */}
          {step === 'hook' && (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">
                The hook term differentiates the product (e.g. colour, material). It can come from saved product hook
                terms or from attributes when generating titles.
              </p>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={includeHookTerm}
                  onChange={(e) => setIncludeHookTerm(e.target.checked)}
                  className="rounded border-input"
                />
                <span>Include hook term in template</span>
              </label>
            </div>
          )}

          {/* Step 4: Needed attributes */}
          {step === 'attributes' && (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Add attributes that should appear in the title, in order. They will be inserted after the hook term,
                separated by &quot; - &quot;. When you generate titles, the <strong>translated</strong> value for each attribute is used, based on the target language you choose at generation time (add translations in Translations if you see the wrong language).
              </p>
              <div className="flex flex-wrap gap-2">
                {attributes
                  .filter((a) => !selectedAttributeIds.includes(a.id))
                  .map((a) => (
                    <Button
                      key={a.id}
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => addAttribute(a.id)}
                    >
                      + {a.code}
                    </Button>
                  ))}
                {attributes.filter((a) => !selectedAttributeIds.includes(a.id)).length === 0 && (
                  <span className="text-sm text-muted-foreground">All attributes added.</span>
                )}
              </div>
              <div className="space-y-2">
                <Label>Order of attributes in title</Label>
                <ul className="space-y-1 border rounded-md divide-y">
                  {selectedAttributeIds.map((id, index) => {
                    const attr = attributes.find((a) => a.id === id);
                    return (
                      <li
                        key={id}
                        className="flex items-center gap-2 px-3 py-2 bg-card"
                      >
                        <div className="flex flex-col gap-0.5">
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            className="h-6 w-6"
                            onClick={() => moveAttribute(index, -1)}
                            disabled={index === 0}
                          >
                            <span className="text-xs">↑</span>
                          </Button>
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            className="h-6 w-6"
                            onClick={() => moveAttribute(index, 1)}
                            disabled={index === selectedAttributeIds.length - 1}
                          >
                            <span className="text-xs">↓</span>
                          </Button>
                        </div>
                        <GripVertical className="w-4 h-4 text-muted-foreground" />
                        <span className="font-mono text-sm">{attr?.code ?? id}</span>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="ml-auto text-muted-foreground hover:text-destructive"
                          onClick={() => removeAttribute(id)}
                        >
                          Remove
                        </Button>
                      </li>
                    );
                  })}
                </ul>
                {selectedAttributeIds.length === 0 && (
                  <p className="text-sm text-muted-foreground py-2">No attributes selected. Add some above.</p>
                )}
              </div>
            </div>
          )}

          <div className="flex justify-between pt-4 border-t">
            <Button variant="outline" onClick={handleBack} disabled={stepIndex === 0}>
              Back
            </Button>
            {canSubmit ? (
              <Button
                onClick={handleNext}
                disabled={createMutation.isPending || (includeHeadTerm === false && includeHookTerm === false)}
              >
                {createMutation.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                Create template
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
