import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, Plus, Trash2, GripVertical, Loader2 } from 'lucide-react';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  getTemplate,
  getTemplateParts,
  getProductTypes,
  getChannels,
  getLocales,
  getAttributes,
  createTemplate,
  createTemplatePart,
  deleteTemplatePart,
  TEMPLATE_PART_TYPES,
  Template,
  TemplatePart,
  ProductType,
  Channel,
  Locale,
  Attribute,
} from '@/lib/api';
import { useToast } from '@/hooks/use-toast';

type PartRow = {
  part_type: 'head_term' | 'hook_term' | 'literal' | 'axis_attribute' | 'attribute_value';
  literal_text?: string;
  attribute_id?: number | null;
};

const DEFAULT_PARTS: PartRow[] = [
  { part_type: 'head_term' },
  { part_type: 'literal', literal_text: ' - ' },
  { part_type: 'hook_term' },
];

export default function TemplateForm() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const isEdit = id != null && id !== 'new';

  const [productTypeId, setProductTypeId] = useState<string>('');
  const [channelCode, setChannelCode] = useState<string>('');
  const [localeCode, setLocaleCode] = useState<string>('');
  const [parts, setParts] = useState<PartRow[]>(DEFAULT_PARTS);

  const { data: template, isLoading: templateLoading } = useQuery({
    queryKey: ['template', id],
    queryFn: () => getTemplate(parseInt(id!)),
    enabled: isEdit,
  });

  const { data: existingParts, isLoading: partsLoading } = useQuery({
    queryKey: ['template-parts', id],
    queryFn: () => getTemplateParts(parseInt(id!)),
    enabled: isEdit && !!template,
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

  useEffect(() => {
    if (!isEdit || !template) return;
    setProductTypeId(String(template.product_type_id));
    setChannelCode(template.channel_code);
    setLocaleCode(template.locale_code);
  }, [isEdit, template]);

  useEffect(() => {
    if (!isEdit || !existingParts || existingParts.length === 0) return;
    const rows: PartRow[] = (existingParts as TemplatePart[])
      .sort((a, b) => a.position - b.position)
      .map((p) => {
        if (p.part_type === 'literal')
          return { part_type: 'literal', literal_text: p.literal_text ?? '' };
        if (p.part_type === 'axis_attribute')
          return { part_type: 'axis_attribute', attribute_id: p.attribute_id };
        if (p.part_type === 'attribute_value')
          return { part_type: 'attribute_value', attribute_id: p.attribute_id };
        if (p.part_type === 'head_term') return { part_type: 'head_term' };
        if (p.part_type === 'hook_term') return { part_type: 'hook_term' };
        return { part_type: 'literal', literal_text: '' };
      });
    setParts(rows);
  }, [isEdit, existingParts]);

  const createMutation = useMutation({
    mutationFn: async () => {
      const t = await createTemplate({
        product_type_id: parseInt(productTypeId),
        channel_code: channelCode,
        locale_code: localeCode,
      });
      for (let i = 0; i < parts.length; i++) {
        const p = parts[i];
        await createTemplatePart({
          template_id: t.id,
          position: i,
          part_type: p.part_type,
          literal_text: p.part_type === 'literal' ? (p.literal_text ?? '') : undefined,
          attribute_id: (p.part_type === 'axis_attribute' || p.part_type === 'attribute_value') ? p.attribute_id ?? null : undefined,
        });
      }
      return t;
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

  const updateMutation = useMutation({
    mutationFn: async () => {
      const tid = parseInt(id!);
      const currentParts = (existingParts ?? []) as TemplatePart[];
      for (const p of currentParts) {
        await deleteTemplatePart(p.id);
      }
      for (let i = 0; i < parts.length; i++) {
        const p = parts[i];
        await createTemplatePart({
          template_id: tid,
          position: i,
          part_type: p.part_type,
          literal_text: p.part_type === 'literal' ? (p.literal_text ?? '') : undefined,
          attribute_id: (p.part_type === 'axis_attribute' || p.part_type === 'attribute_value') ? p.attribute_id ?? null : undefined,
        });
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['template-parts', id] });
      queryClient.invalidateQueries({ queryKey: ['templates'] });
      toast({ title: 'Template updated' });
    },
    onError: (err: unknown) => {
      toast({
        title: 'Failed to update template',
        description: String((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail),
        variant: 'destructive',
      });
    },
  });

  const productTypes = (productTypesData?.results ?? []) as ProductType[];
  const channels = (channelsData?.results ?? []) as Channel[];
  const locales = (localesData?.results ?? []) as Locale[];
  const attributes = (attributesData?.results ?? []) as Attribute[];

  const axisAttributeIds = new Set(
    parts
      .filter((p) => p.part_type === 'axis_attribute' && p.attribute_id != null)
      .map((p) => p.attribute_id as number)
  );

  const addPart = (type: PartRow['part_type']) => {
    if (type === 'literal') setParts([...parts, { part_type: 'literal', literal_text: ' - ' }]);
    else if (type === 'axis_attribute')
      setParts([...parts, { part_type: 'axis_attribute', attribute_id: attributes[0]?.id ?? null }]);
    else if (type === 'attribute_value')
      setParts([...parts, { part_type: 'attribute_value', attribute_id: attributes[0]?.id ?? null }]);
    else setParts([...parts, { part_type: type }]);
  };

  const removePart = (index: number) => {
    setParts(parts.filter((_, i) => i !== index));
  };

  const movePart = (index: number, dir: -1 | 1) => {
    const newIndex = index + dir;
    if (newIndex < 0 || newIndex >= parts.length) return;
    const next = [...parts];
    const t = next[index];
    next[index] = next[newIndex];
    next[newIndex] = t;
    setParts(next);
  };

  const updatePart = (index: number, upd: Partial<PartRow>) => {
    setParts(parts.map((p, i) => (i === index ? { ...p, ...upd } : p)));
  };

  const handleSave = () => {
    if (!productTypeId || !channelCode || !localeCode) {
      toast({ title: 'Fill scope', description: 'Product type, channel, and locale are required', variant: 'destructive' });
      return;
    }
    if (parts.length === 0) {
      toast({ title: 'Add at least one part', variant: 'destructive' });
      return;
    }
    const duplicateAttrIds = new Set<number>();
    for (let i = 0; i < parts.length; i++) {
      const p = parts[i];
      if (p.part_type === 'literal' && !(p.literal_text?.trim())) {
        toast({ title: 'Literal text required', description: `Part ${i + 1}: enter text for literal`, variant: 'destructive' });
        return;
      }
      if ((p.part_type === 'axis_attribute' || p.part_type === 'attribute_value') && !p.attribute_id) {
        toast({ title: 'Attribute required', description: `Part ${i + 1}: select an attribute`, variant: 'destructive' });
        return;
      }
      if (p.part_type === 'attribute_value' && p.attribute_id && axisAttributeIds.has(p.attribute_id)) {
        duplicateAttrIds.add(p.attribute_id);
      }
    }
    if (duplicateAttrIds.size > 0) {
      const dupCodes = attributes
        .filter((a) => duplicateAttrIds.has(a.id))
        .map((a) => a.code)
        .join(', ');
      if (dupCodes) {
        toast({
          title: 'Attribute already used as axis',
          description: `These attributes are already included via Axis attribute and will not be added again: ${dupCodes}.`,
        });
      }
    }
    if (isEdit) updateMutation.mutate();
    else createMutation.mutate();
  };

  if (isEdit && (templateLoading || partsLoading)) {
    return (
      <div className="page-container flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="page-container">
      <PageHeader
        title={isEdit ? 'Edit template' : 'Create template'}
        description={
          isEdit
            ? 'Change the order of parts: head term, hook term, literals, then attributes.'
            : 'Choose scope and build the title: head term, hook term, then attributes at the end.'
        }
        breadcrumbs={[
          { label: 'Dashboard', href: '/' },
          { label: 'Templates', href: '/templates' },
          { label: isEdit ? 'Edit' : 'New' },
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

      <Card>
        <CardHeader>
          <CardTitle>Scope</CardTitle>
          <CardDescription>Product type, channel, and locale for this title template.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label>Product type</Label>
              <Select value={productTypeId} onValueChange={setProductTypeId} disabled={isEdit}>
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
              <Select value={channelCode} onValueChange={setChannelCode} disabled={isEdit}>
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
              <Select value={localeCode} onValueChange={setLocaleCode} disabled={isEdit}>
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
        </CardContent>
      </Card>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Template parts</CardTitle>
          <CardDescription>
            Order: head term, hook term, literals, then attributes. Use <strong>Axis attribute</strong> for variation axes (listing Axes tab); use <strong>Attribute (any)</strong> for any other attribute (e.g. colour, finish) even if not an axis. If an attribute is already included as an axis, it won&apos;t be added again when used as Attribute (any).
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2 mb-4">
            <Button type="button" variant="outline" size="sm" onClick={() => addPart('head_term')}>
              <Plus className="w-4 h-4 mr-1" />
              Head term
            </Button>
            <Button type="button" variant="outline" size="sm" onClick={() => addPart('hook_term')}>
              <Plus className="w-4 h-4 mr-1" />
              Hook term
            </Button>
            <Button type="button" variant="outline" size="sm" onClick={() => addPart('literal')}>
              <Plus className="w-4 h-4 mr-1" />
              Literal
            </Button>
            <Button type="button" variant="outline" size="sm" onClick={() => addPart('axis_attribute')}>
              <Plus className="w-4 h-4 mr-1" />
              Axis attribute
            </Button>
            <Button type="button" variant="outline" size="sm" onClick={() => addPart('attribute_value')}>
              <Plus className="w-4 h-4 mr-1" />
              Attribute (any)
            </Button>
          </div>

          <ul className="space-y-2">
            {parts.map((part, index) => (
              <li
                key={index}
                className="flex items-center gap-2 p-3 rounded-lg border bg-card"
              >
                <div className="flex flex-col gap-0.5">
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6"
                    onClick={() => movePart(index, -1)}
                    disabled={index === 0}
                  >
                    <span className="text-xs">↑</span>
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6"
                    onClick={() => movePart(index, 1)}
                    disabled={index === parts.length - 1}
                  >
                    <span className="text-xs">↓</span>
                  </Button>
                </div>
                <span className="text-sm text-muted-foreground w-28 shrink-0">
                  {TEMPLATE_PART_TYPES[part.part_type] ?? part.part_type}
                </span>
                {part.part_type === 'literal' && (
                  <Input
                    className="max-w-xs"
                    value={part.literal_text ?? ''}
                    onChange={(e) => updatePart(index, { literal_text: e.target.value })}
                    placeholder="e.g.  - "
                  />
                )}
                {(part.part_type === 'axis_attribute' || part.part_type === 'attribute_value') && (
                  <Select
                    value={part.attribute_id ? String(part.attribute_id) : ''}
                    onValueChange={(v) => updatePart(index, { attribute_id: v ? parseInt(v) : null })}
                  >
                    <SelectTrigger className="w-[180px]">
                      <SelectValue placeholder="Select attribute..." />
                    </SelectTrigger>
                    <SelectContent>
                      {attributes.map((a) => {
                        return (
                          <SelectItem key={a.id} value={String(a.id)}>
                            {a.code}
                          </SelectItem>
                        );
                      })}
                    </SelectContent>
                  </Select>
                )}
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="ml-auto text-muted-foreground hover:text-destructive"
                  onClick={() => removePart(index)}
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              </li>
            ))}
          </ul>

          <div className="flex justify-end pt-4 border-t">
            <Button
              onClick={handleSave}
              disabled={createMutation.isPending || updateMutation.isPending}
            >
              {(createMutation.isPending || updateMutation.isPending) && (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              )}
              {isEdit ? 'Update template' : 'Create template'}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
