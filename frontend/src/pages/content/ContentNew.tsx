import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Sparkles, Loader2, Eye, FileText, FileDown, Save } from 'lucide-react';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  contentPreviewFull,
  DESCRIPTION_AI_MODELS,
  generateContent,
  getChannels,
  getLocales,
  previewContent,
  saveContentSelection,
  type Channel,
  type ContentPreviewFullResponse,
  type Locale,
} from '@/lib/api';
import { useToast } from '@/hooks/use-toast';

export default function ContentNew() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [variantIds, setVariantIds] = useState('');
  const [template, setTemplate] = useState('');
  const [previewVariantId, setPreviewVariantId] = useState('');
  const [previewResult, setPreviewResult] = useState('');
  const [descLocaleCode, setDescLocaleCode] = useState('');
  const [descChannelCode, setDescChannelCode] = useState('');
  const [descVariantId, setDescVariantId] = useState('');
  const [descPreviewResult, setDescPreviewResult] = useState<ContentPreviewFullResponse | null>(null);
  const [descModel, setDescModel] = useState('gpt-4o-mini');
  const [descInstructions, setDescInstructions] = useState('');

  const { data: localesData } = useQuery({
    queryKey: ['locales'],
    queryFn: () => getLocales({ page_size: 200 }),
  });
  const { data: channelsData } = useQuery({
    queryKey: ['channels'],
    queryFn: () => getChannels({ page_size: 200 }),
  });
  const locales = (localesData?.results ?? []) as Locale[];
  const channels = (channelsData?.results ?? []) as Channel[];

  const contentMutation = useMutation({
    mutationFn: generateContent,
    onSuccess: () => {
      navigate('/content');
    },
  });

  const previewMutation = useMutation({
    mutationFn: previewContent,
    onSuccess: (data) => {
      setPreviewResult(data.content);
    },
  });

  const descPreviewMutation = useMutation({
    mutationFn: contentPreviewFull,
    onSuccess: (data) => {
      setDescPreviewResult(data);
    },
  });

  const saveContentMutation = useMutation({
    mutationFn: saveContentSelection,
    onSuccess: () => {
      toast({ title: 'Content saved', description: 'Description and bullets saved as draft. You can export them later.' });
    },
    onError: (err: unknown) => {
      toast({
        title: 'Save failed',
        description: err instanceof Error ? err.message : 'Could not save content',
        variant: 'destructive',
      });
    },
  });

  const parseVariantIds = () => {
    return variantIds
      .split(/[,\n]/)
      .map((s) => s.trim())
      .filter(Boolean)
      .map((s) => parseInt(s, 10))
      .filter((n) => !isNaN(n));
  };

  const handleGenerateContent = () => {
    const ids = parseVariantIds();
    if (ids.length > 0) {
      contentMutation.mutate({ variant_ids: ids, template: template || undefined });
    }
  };

  const handlePreview = () => {
    const id = parseInt(previewVariantId, 10);
    if (!isNaN(id)) {
      previewMutation.mutate({ variant_id: id, template: template || undefined });
    }
  };

  const handlePreviewDescription = () => {
    const id = parseInt(descVariantId, 10);
    if (!isNaN(id) && descLocaleCode && descChannelCode) {
      const payload: Parameters<typeof contentPreviewFull>[0] = {
        variant_id: id,
        locale_code: descLocaleCode,
        channel_code: descChannelCode,
        include_descriptions: true,
      };
      if (descInstructions.trim()) {
        payload.description_model = descModel;
        payload.description_instructions = descInstructions.trim();
      }
      descPreviewMutation.mutate(payload);
    }
  };

  return (
    <div className="page-container">
      <PageHeader
        title="New Generation"
        description="Generate titles and content for product variants"
        breadcrumbs={[
          { label: 'Dashboard', href: '/' },
          { label: 'Content', href: '/content' },
          { label: 'New' },
        ]}
      />

      <div className="max-w-3xl mx-auto">
        <Tabs defaultValue="generate" className="space-y-6">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="generate">Generate</TabsTrigger>
            <TabsTrigger value="preview">Preview</TabsTrigger>
            <TabsTrigger value="description">Description</TabsTrigger>
          </TabsList>

          <TabsContent value="generate">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Sparkles className="w-5 h-5" />
                  Content Generation
                </CardTitle>
                <CardDescription>
                  Generate titles or content for selected product variants.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-2">
                  <Label htmlFor="variantIds">Variant IDs</Label>
                  <Textarea
                    id="variantIds"
                    value={variantIds}
                    onChange={(e) => setVariantIds(e.target.value)}
                    placeholder="Enter variant IDs (comma or newline separated)&#10;e.g., 1, 2, 3 or&#10;1&#10;2&#10;3"
                    rows={4}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="template">Template (optional)</Label>
                  <Textarea
                    id="template"
                    value={template}
                    onChange={(e) => setTemplate(e.target.value)}
                    placeholder="Custom template for generation..."
                    rows={3}
                  />
                </div>

                <div className="flex flex-col sm:flex-row gap-3">
                  <Button
                    variant="outline"
                    className="flex-1"
                    asChild
                  >
                    <Link to="/content/generate-titles">
                      <FileText className="w-4 h-4 mr-2" />
                      Generate titles (channel & locale)
                    </Link>
                  </Button>
                  <Button
                    onClick={handleGenerateContent}
                    disabled={!variantIds.trim() || contentMutation.isPending}
                    className="flex-1"
                  >
                    {contentMutation.isPending && (
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    )}
                    Generate Content
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="preview">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Eye className="w-5 h-5" />
                  Content Preview
                </CardTitle>
                <CardDescription>
                  Preview generated content for a single variant.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-2">
                  <Label htmlFor="previewId">Variant ID</Label>
                  <div className="flex gap-2">
                    <Input
                      id="previewId"
                      value={previewVariantId}
                      onChange={(e) => setPreviewVariantId(e.target.value)}
                      placeholder="Enter a variant ID"
                    />
                    <Button
                      onClick={handlePreview}
                      disabled={!previewVariantId || previewMutation.isPending}
                    >
                      {previewMutation.isPending ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Eye className="w-4 h-4" />
                      )}
                    </Button>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="template2">Template (optional)</Label>
                  <Textarea
                    id="template2"
                    value={template}
                    onChange={(e) => setTemplate(e.target.value)}
                    placeholder="Custom template for preview..."
                    rows={3}
                  />
                </div>

                {previewResult && (
                  <div className="space-y-2">
                    <Label>Preview Result</Label>
                    <div className="p-4 bg-muted rounded-lg text-sm whitespace-pre-wrap">
                      {previewResult}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="description">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileDown className="w-5 h-5" />
                  Description from attributes
                </CardTitle>
                <CardDescription>
                  Generate a description from variant attribute values. Choose locale and channel, then preview to see the generated description and the attribute values used for this variant.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <Label>Language (locale)</Label>
                    <Select value={descLocaleCode} onValueChange={setDescLocaleCode}>
                      <SelectTrigger>
                        <SelectValue placeholder="Select locale" />
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
                  <div className="space-y-2">
                    <Label>Marketplace (channel)</Label>
                    <Select value={descChannelCode} onValueChange={setDescChannelCode}>
                      <SelectTrigger>
                        <SelectValue placeholder="Select channel" />
                      </SelectTrigger>
                      <SelectContent>
                        {channels.map((c) => (
                          <SelectItem key={c.code} value={c.code}>
                            {c.code}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="descVariantId">Variant ID</Label>
                    <Input
                      id="descVariantId"
                      type="number"
                      min={1}
                      value={descVariantId}
                      onChange={(e) => setDescVariantId(e.target.value)}
                      placeholder="e.g. 1"
                    />
                  </div>
                </div>

                <div className="space-y-4 rounded-lg border bg-muted/30 p-4">
                  <Label className="text-sm font-medium">AI options (optional)</Label>
                  <p className="text-xs text-muted-foreground">
                    Use AI to improve the description. Leave instructions blank to use the template-based description only.
                  </p>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label className="text-xs">Model</Label>
                      <Select value={descModel} onValueChange={setDescModel}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {DESCRIPTION_AI_MODELS.map((m) => (
                            <SelectItem key={m.value} value={m.value}>
                              {m.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2 sm:col-span-2">
                      <Label className="text-xs">Instructions for the model</Label>
                      <Textarea
                        value={descInstructions}
                        onChange={(e) => setDescInstructions(e.target.value)}
                        placeholder="e.g. Make it more technical. Emphasize durability and ease of installation. Keep under 150 words."
                        rows={3}
                        className="resize-none"
                      />
                    </div>
                  </div>
                </div>

                <Button
                  onClick={handlePreviewDescription}
                  disabled={
                    !descLocaleCode ||
                    !descChannelCode ||
                    !descVariantId.trim() ||
                    descPreviewMutation.isPending
                  }
                >
                  {descPreviewMutation.isPending ? (
                    <Loader2 className="w-4 h-4 animate-spin mr-2" />
                  ) : (
                    <Eye className="w-4 h-4 mr-2" />
                  )}
                  Load attributes & preview description
                </Button>

                {descPreviewMutation.isError && (
                  <div className="p-4 rounded-lg bg-destructive/10 text-destructive text-sm">
                    {descPreviewMutation.error instanceof Error
                      ? descPreviewMutation.error.message
                      : 'Preview failed'}
                  </div>
                )}

                {descPreviewResult && (
                  <div className="space-y-6">
                    <div className="space-y-2">
                      <Label>Generated title</Label>
                      <div className="p-4 bg-muted rounded-lg text-sm">
                        {descPreviewResult.title || '—'}
                      </div>
                    </div>
                    <div className="space-y-2">
                      <Label>Generated description</Label>
                      <div className="p-4 bg-muted rounded-lg text-sm whitespace-pre-wrap">
                        {descPreviewResult.description || '—'}
                      </div>
                    </div>
                    {Array.isArray(descPreviewResult.bullets) &&
                      descPreviewResult.bullets.length > 0 && (
                        <div className="space-y-2">
                          <Label>Bullets</Label>
                          <ul className="list-disc list-inside p-4 bg-muted rounded-lg text-sm space-y-1">
                            {descPreviewResult.bullets.map((b, i) => (
                              <li key={i}>{b}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    <div className="space-y-2">
                      <Label>Attribute values used for this variant</Label>
                      <p className="text-sm text-muted-foreground">
                        These attributes and values were used to build the description above.
                      </p>
                      {descPreviewResult.features && descPreviewResult.features.length > 0 ? (
                        <div className="rounded-md border">
                          <Table>
                            <TableHeader>
                              <TableRow>
                                <TableHead className="w-40">Attribute</TableHead>
                                <TableHead>Value</TableHead>
                                <TableHead className="w-32 text-muted-foreground">Source</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {descPreviewResult.features.map((f, i) => (
                                <TableRow key={i}>
                                  <TableCell className="font-mono text-sm">{f.attribute_code}</TableCell>
                                  <TableCell>{f.value}</TableCell>
                                  <TableCell className="text-muted-foreground text-sm">
                                    {f.source ?? '—'}
                                  </TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </div>
                      ) : (
                        <p className="text-sm text-muted-foreground py-2">
                          No attribute values for this variant in this locale/channel.
                        </p>
                      )}
                    </div>
                    <div className="flex flex-wrap gap-2 pt-2">
                      <Button
                        onClick={() => {
                          const vid = typeof descVariantId === 'string' ? parseInt(descVariantId, 10) : descVariantId;
                          if (!descLocaleCode || !descChannelCode || !Number.isInteger(vid)) return;
                          saveContentMutation.mutate({
                            variant_id: vid,
                            locale_code: descLocaleCode,
                            channel_code: descChannelCode,
                            description: descPreviewResult.description ?? '',
                            bullets: Array.isArray(descPreviewResult.bullets) ? descPreviewResult.bullets : [],
                          });
                        }}
                        disabled={!descLocaleCode || !descChannelCode || saveContentMutation.isPending}
                      >
                        {saveContentMutation.isPending ? (
                          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        ) : (
                          <Save className="w-4 h-4 mr-2" />
                        )}
                        Save content (draft)
                      </Button>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        <div className="flex justify-end mt-6">
          <Button variant="outline" onClick={() => navigate('/content')}>
            Back to List
          </Button>
        </div>
      </div>
    </div>
  );
}
