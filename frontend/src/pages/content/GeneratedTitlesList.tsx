import { useState, useCallback, useEffect, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { FileText, Download, Loader2, FileSpreadsheet, FileDown, Pencil, Trash2, Check, X, ArrowRight, Wand2 } from 'lucide-react';
import { Link } from 'react-router-dom';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
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
import { Checkbox } from '@/components/ui/checkbox';
import {
  getLocales,
  getChannels,
  getTitleAiOptions,
  getAllGeneratedTitles,
  updateGeneratedTitle,
  deleteGeneratedTitle,
  polishGeneratedTitle,
  type PolishTitleResult,
  getTranslatableAttributes,
  downloadTitlesAndAttributesCsv,
  downloadProductsOneRowCsv,
  type AllGeneratedTitleItem,
  type Locale,
  type Channel,
  type TranslatableAttribute,
} from '@/lib/api';
import { useToast } from '@/hooks/use-toast';
import * as XLSX from 'xlsx';

const PAGE_SIZE = 100;
const ALL_LOCALE = '__all_locale__';
const ALL_CHANNEL = '__all_channel__';
const FALLBACK_AI_MODELS = ['gpt-4o', 'gpt-4o-mini'];

function formatDateTime(iso: string | null | undefined): string {
  if (iso == null) return '—';
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return '—';
    return d.toLocaleString(undefined, {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return '—';
  }
}

function escapeCsvCell(value: string): string {
  if (value == null) return '';
  const s = String(value);
  if (s.includes('"') || s.includes(',') || s.includes('\n') || s.includes('\r')) {
    return '"' + s.replace(/"/g, '""') + '"';
  }
  return s;
}

export default function GeneratedTitlesList() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [localeCode, setLocaleCode] = useState<string>(ALL_LOCALE);
  const [channelCode, setChannelCode] = useState<string>(ALL_CHANNEL);
  const [page, setPage] = useState(1);
  const localeForApi = localeCode === ALL_LOCALE ? '' : localeCode;
  const channelForApi = channelCode === ALL_CHANNEL ? '' : channelCode;

  const [editingRunId, setEditingRunId] = useState<number | null>(null);
  const [editingText, setEditingText] = useState('');

  const queryKey = ['all-generated-titles', localeForApi || null, channelForApi || null, page];

  const updateMutation = useMutation({
    mutationFn: ({ runId, title }: { runId: number; title: string }) => updateGeneratedTitle(runId, title),
    onSuccess: () => {
      setEditingRunId(null);
      queryClient.invalidateQueries({ queryKey });
      toast({ title: 'Title updated' });
    },
    onError: () => toast({ title: 'Update failed', variant: 'destructive' }),
  });

  const deleteMutation = useMutation({
    mutationFn: (runId: number) => deleteGeneratedTitle(runId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey });
      toast({ title: 'Title deleted' });
    },
    onError: () => toast({ title: 'Delete failed', variant: 'destructive' }),
  });

  const [polishDialog, setPolishDialog] = useState<{ runId: number; original: string } | null>(null);
  const [polishResult, setPolishResult] = useState<PolishTitleResult | null>(null);
  const [polishAiModel, setPolishAiModel] = useState('');
  const [polishInstructions, setPolishInstructions] = useState('');
  const [polishDefaultsApplied, setPolishDefaultsApplied] = useState(false);
  const [selectedRunIds, setSelectedRunIds] = useState<Set<number>>(new Set());
  const [isBulkWorking, setIsBulkWorking] = useState(false);
  const polishMutation = useMutation({
    mutationFn: ({ runId, aiModel, instructions }: { runId: number; aiModel?: string; instructions?: string }) =>
      polishGeneratedTitle(runId, aiModel, instructions),
    onSuccess: (data) => setPolishResult(data),
    onError: () => toast({ title: 'Polish failed', variant: 'destructive' }),
  });
  const acceptPolishMutation = useMutation({
    mutationFn: ({ runId, title }: { runId: number; title: string }) => updateGeneratedTitle(runId, title),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey });
      setPolishDialog(null);
      setPolishResult(null);
      toast({ title: 'Title updated with AI polish' });
    },
    onError: () => toast({ title: 'Update failed', variant: 'destructive' }),
  });

  const { data: localesData } = useQuery({
    queryKey: ['locales'],
    queryFn: () => getLocales({ page_size: 200 }),
  });
  const { data: channelsData } = useQuery({
    queryKey: ['channels'],
    queryFn: () => getChannels({ page_size: 200 }),
  });
  const { data: attributesData } = useQuery({
    queryKey: ['translatable-attributes'],
    queryFn: getTranslatableAttributes,
  });
  const { data: titleAiOptions } = useQuery({
    queryKey: ['title-ai-options'],
    queryFn: getTitleAiOptions,
  });

  const aiModels = useMemo(
    () => (titleAiOptions?.title_ai_models?.length ? titleAiOptions.title_ai_models : FALLBACK_AI_MODELS),
    [titleAiOptions]
  );
  const defaultAiModel = titleAiOptions?.default_title_ai_model || aiModels[0] || 'gpt-4o';
  const defaultAiInstructions = titleAiOptions?.default_title_ai_instructions || '';

  useEffect(() => {
    if (polishDefaultsApplied || !titleAiOptions) return;
    setPolishAiModel((prev) => prev || defaultAiModel);
    setPolishInstructions((prev) => prev || defaultAiInstructions);
    setPolishDefaultsApplied(true);
  }, [polishDefaultsApplied, titleAiOptions, defaultAiModel, defaultAiInstructions]);

  const locales = (localesData?.results ?? []) as Locale[];
  const channels = (channelsData?.results ?? []) as Channel[];
  const translatableAttrs = (attributesData?.results ?? []) as TranslatableAttribute[];

  const { data, isLoading } = useQuery({
    queryKey,
    queryFn: () =>
      getAllGeneratedTitles({
        ...(localeForApi && { locale_code: localeForApi }),
        ...(channelForApi && { channel_code: channelForApi }),
        page,
        page_size: PAGE_SIZE,
      }),
  });

  const results = data?.results ?? [];
  const count = data?.count ?? 0;
  const totalPages = Math.max(1, Math.ceil(count / PAGE_SIZE));
  const selectedCount = selectedRunIds.size;
  const allPageSelected = results.length > 0 && results.every((r) => selectedRunIds.has(r.run_id));

  const exportData = useCallback(async (format: 'csv' | 'xlsx') => {
    try {
      const params: { locale_code?: string; channel_code?: string; page?: number; page_size?: number } = {
        page: 1,
        page_size: 5000,
      };
      if (localeForApi) params.locale_code = localeForApi;
      if (channelForApi) params.channel_code = channelForApi;
      const res = await getAllGeneratedTitles(params);
      const rows = res.results;

    const headers = ['Variant ID', 'SKU', 'Product ID', 'Product code', 'Channel', 'Locale', 'Title', 'Generated at'];
    const rowData = rows.map((r) => [
      r.variant_id,
      r.sku ?? '',
      r.product_id ?? '',
      r.product_code ?? '',
      r.channel_code ?? '',
      r.locale_code ?? '',
      r.title ?? '',
      r.generated_at ? formatDateTime(r.generated_at) : '',
    ]);

    if (format === 'csv') {
      const csvLines = [headers.map(escapeCsvCell).join(','), ...rowData.map((row) => row.map(escapeCsvCell).join(','))];
      const blob = new Blob([csvLines.join('\r\n')], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `generated-titles-${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      toast({ title: 'Exported', description: `${rows.length} rows as CSV` });
    } else {
      const ws = XLSX.utils.aoa_to_sheet([headers, ...rowData]);
      const wb = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(wb, ws, 'Generated titles');
      XLSX.writeFile(wb, `generated-titles-${new Date().toISOString().slice(0, 10)}.xlsx`);
      toast({ title: 'Exported', description: `${rows.length} rows as Excel` });
    }
    } catch (err) {
      toast({
        title: 'Export failed',
        description: err instanceof Error ? err.message : 'Unknown error',
        variant: 'destructive',
      });
    }
  }, [localeForApi, channelForApi, toast]);

  const [downloadingTitlesAttrs, setDownloadingTitlesAttrs] = useState(false);
  const [exportIncludeDescription, setExportIncludeDescription] = useState(true);
  const [selectedAttributeCodes, setSelectedAttributeCodes] = useState<Set<string>>(new Set());
  const handleDownloadTitlesAndAttributes = useCallback(async () => {
    if (!localeForApi) {
      toast({
        title: 'Select a language',
        description: 'Choose a language (locale) above to download titles and translated attributes.',
        variant: 'destructive',
      });
      return;
    }
    setDownloadingTitlesAttrs(true);
    try {
      const attributeCodes = selectedAttributeCodes.size > 0 ? Array.from(selectedAttributeCodes) : undefined;
      const blob = await downloadTitlesAndAttributesCsv(localeForApi, channelForApi || undefined, {
        includeDescription: exportIncludeDescription,
        attributeCodes,
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `titles-and-attributes-${localeForApi}-${channelForApi || 'all'}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      toast({ title: 'Download started', description: 'Titles and translated attributes CSV.' });
    } catch (err) {
      toast({
        title: 'Download failed',
        description: err instanceof Error ? err.message : 'Could not download CSV',
        variant: 'destructive',
      });
    } finally {
      setDownloadingTitlesAttrs(false);
    }
  }, [localeForApi, channelForApi, exportIncludeDescription, selectedAttributeCodes, toast]);

  const [downloadingOneRow, setDownloadingOneRow] = useState(false);
  const handleDownloadProductsOneRow = useCallback(async () => {
    if (!localeForApi) {
      toast({
        title: 'Select a language',
        description: 'Choose a language above to download.',
        variant: 'destructive',
      });
      return;
    }
    setDownloadingOneRow(true);
    try {
      const attributeCodes = selectedAttributeCodes.size > 0 ? Array.from(selectedAttributeCodes) : undefined;
      const blob = await downloadProductsOneRowCsv(localeForApi, channelForApi || undefined, {
        includeDescription: exportIncludeDescription,
        attributeCodes,
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `products_one_row_${localeForApi}_${channelForApi || 'all'}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      toast({ title: 'Download started', description: 'One row per product CSV.' });
    } catch (err) {
      toast({
        title: 'Download failed',
        description: err instanceof Error ? err.message : 'Could not download CSV',
        variant: 'destructive',
      });
    } finally {
      setDownloadingOneRow(false);
    }
  }, [localeForApi, channelForApi, exportIncludeDescription, selectedAttributeCodes, toast]);

  const toggleAttribute = (code: string) => {
    setSelectedAttributeCodes((prev) => {
      const next = new Set(prev);
      if (next.has(code)) next.delete(code);
      else next.add(code);
      return next;
    });
  };
  const selectAllAttributes = () => setSelectedAttributeCodes(new Set(translatableAttrs.map((a) => a.code)));
  const clearAttributeSelection = () => setSelectedAttributeCodes(new Set());

  const openPolishDialog = (row: AllGeneratedTitleItem) => {
    setPolishDialog({ runId: row.run_id, original: row.title || '' });
    setPolishResult(null);
    polishMutation.mutate({ runId: row.run_id, aiModel: polishAiModel, instructions: polishInstructions });
  };

  const toggleSelected = (runId: number) => {
    setSelectedRunIds((prev) => {
      const next = new Set(prev);
      if (next.has(runId)) next.delete(runId);
      else next.add(runId);
      return next;
    });
  };

  const toggleSelectAllOnPage = () => {
    setSelectedRunIds((prev) => {
      const next = new Set(prev);
      if (allPageSelected) {
        results.forEach((r) => next.delete(r.run_id));
      } else {
        results.forEach((r) => next.add(r.run_id));
      }
      return next;
    });
  };

  const handleBulkDelete = async () => {
    if (selectedRunIds.size === 0) {
      toast({ title: 'Select at least one title', variant: 'destructive' });
      return;
    }
    if (!confirm(`Delete ${selectedRunIds.size} selected title(s)?`)) return;
    setIsBulkWorking(true);
    let deleted = 0;
    let failed = 0;
    for (const runId of selectedRunIds) {
      try {
        await deleteGeneratedTitle(runId);
        deleted += 1;
      } catch {
        failed += 1;
      }
    }
    setIsBulkWorking(false);
    setSelectedRunIds(new Set());
    queryClient.invalidateQueries({ queryKey });
    toast({
      title: 'Bulk delete complete',
      description: failed > 0 ? `${deleted} deleted, ${failed} failed.` : `${deleted} deleted.`,
      variant: failed > 0 ? 'destructive' : 'default',
    });
  };

  const handleBulkPolishAndApply = async () => {
    if (selectedRunIds.size === 0) {
      toast({ title: 'Select at least one title', variant: 'destructive' });
      return;
    }
    setIsBulkWorking(true);
    let updated = 0;
    let failed = 0;
    for (const runId of selectedRunIds) {
      try {
        const polished = await polishGeneratedTitle(runId, polishAiModel, polishInstructions);
        if (polished?.polished) {
          await updateGeneratedTitle(runId, polished.polished);
          updated += 1;
        } else {
          failed += 1;
        }
      } catch {
        failed += 1;
      }
    }
    setIsBulkWorking(false);
    queryClient.invalidateQueries({ queryKey });
    toast({
      title: 'Bulk polish complete',
      description: failed > 0 ? `${updated} updated, ${failed} failed.` : `${updated} updated.`,
      variant: failed > 0 ? 'destructive' : 'default',
    });
  };

  return (
    <div className="page-container">
      <PageHeader
        title="All generated titles"
        description="View and export generated titles. Titles are generated from Listings to include listing context and variation axes."
        breadcrumbs={[
          { label: 'Dashboard', href: '/' },
          { label: 'Content', href: '/content' },
          { label: 'Generated titles' },
        ]}
        actions={
          <Button variant="outline" asChild>
            <Link to="/groups">
              Go to Listings
              <ArrowRight className="w-4 h-4 ml-2" />
            </Link>
          </Button>
        }
      />

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="w-5 h-5" />
            Generated titles
          </CardTitle>
          <CardDescription>
            Latest generated title per variant, language, and marketplace. Generate titles in Listings, then review and export here.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Filters */}
          <div className="flex flex-wrap items-end gap-4">
            <div className="space-y-2">
              <Label>Language (locale)</Label>
              <Select value={localeCode} onValueChange={(v) => { setLocaleCode(v); setPage(1); }}>
                <SelectTrigger className="w-[200px]">
                  <SelectValue placeholder="All languages" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={ALL_LOCALE}>All languages</SelectItem>
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
              <Select value={channelCode} onValueChange={(v) => { setChannelCode(v); setPage(1); }}>
                <SelectTrigger className="w-[200px]">
                  <SelectValue placeholder="All marketplaces" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={ALL_CHANNEL}>All marketplaces</SelectItem>
                  {channels.map((c) => (
                    <SelectItem key={c.code} value={c.code}>
                      {c.code}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-wrap gap-2 ml-auto">
              <Button variant="outline" size="sm" onClick={() => exportData('csv')} disabled={count === 0}>
                <Download className="w-4 h-4 mr-2" />
                Export CSV
              </Button>
              <Button variant="outline" size="sm" onClick={() => exportData('xlsx')} disabled={count === 0}>
                <FileSpreadsheet className="w-4 h-4 mr-2" />
                Export Excel
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleDownloadTitlesAndAttributes}
                disabled={!localeForApi || downloadingTitlesAttrs}
                title={localeForApi ? 'Download generated titles and their translated attributes as CSV' : 'Select a language first'}
              >
                {downloadingTitlesAttrs ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <FileDown className="w-4 h-4 mr-2" />
                )}
                Titles + attributes CSV
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleDownloadProductsOneRow}
                disabled={!localeForApi || downloadingOneRow}
                title={localeForApi ? 'One row per product/variant, attributes as columns' : 'Select a language first'}
              >
                {downloadingOneRow ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <FileDown className="w-4 h-4 mr-2" />
                )}
                One row per product
              </Button>
            </div>
          </div>
          {/* Export options for both CSV exports below */}
          <div className="space-y-3 pt-2 border-t">
            <div className="flex flex-wrap items-center gap-4 text-sm">
              <Label className="text-muted-foreground font-normal">For CSV exports (titles + attributes / one row per product):</Label>
              <label className="flex items-center gap-2 cursor-pointer">
                <Checkbox
                  checked={exportIncludeDescription}
                  onCheckedChange={(checked) => setExportIncludeDescription(checked === true)}
                />
                Include generated descriptions
              </label>
            </div>
            <div className="space-y-2">
              <div className="flex items-center gap-2 flex-wrap">
                <Label className="text-muted-foreground font-normal">Attributes to include:</Label>
                <span className="text-xs text-muted-foreground">
                  {selectedAttributeCodes.size === 0
                    ? 'All translatable attributes'
                    : `${selectedAttributeCodes.size} selected`}
                </span>
                <Button type="button" variant="ghost" size="sm" className="h-7 text-xs" onClick={selectAllAttributes}>
                  Select all
                </Button>
                <Button type="button" variant="ghost" size="sm" className="h-7 text-xs" onClick={clearAttributeSelection}>
                  Clear
                </Button>
              </div>
              {translatableAttrs.length > 0 ? (
                <div className="flex flex-wrap gap-x-4 gap-y-1 max-h-32 overflow-y-auto py-1 pr-2 rounded border bg-muted/30 px-2">
                  {translatableAttrs.map((attr) => (
                    <label key={attr.id} className="flex items-center gap-2 cursor-pointer text-sm whitespace-nowrap">
                      <Checkbox
                        checked={selectedAttributeCodes.has(attr.code)}
                        onCheckedChange={() => toggleAttribute(attr.code)}
                      />
                      <span className="font-mono">{attr.code}</span>
                    </label>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground">No translatable attributes defined. Export will include all.</p>
              )}
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 rounded-md border bg-muted/20 p-3">
            <div className="text-sm text-muted-foreground">
              {selectedCount === 0 ? 'No titles selected' : `${selectedCount} selected`}
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={handleBulkPolishAndApply}
                disabled={selectedCount === 0 || isBulkWorking}
              >
                {isBulkWorking ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Working...
                  </>
                ) : (
                  'Bulk polish + apply'
                )}
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setSelectedRunIds(new Set())}
                disabled={selectedCount === 0 || isBulkWorking}
              >
                Clear selection
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleBulkDelete}
                disabled={selectedCount === 0 || isBulkWorking}
              >
                Bulk delete
              </Button>
            </div>
          </div>

          {/* Table */}
          {isLoading ? (
            <div className="flex items-center justify-center py-12 text-muted-foreground">
              <Loader2 className="w-8 h-8 animate-spin mr-2" />
              Loading…
            </div>
          ) : results.length === 0 ? (
            <div className="py-12 text-center text-muted-foreground">
              <FileText className="w-12 h-12 mx-auto mb-2 opacity-50" />
              <p>No generated titles found.</p>
              <p className="text-sm mt-1">Try changing filters or generate titles from a listing (Listings → open listing → Titles).</p>
            </div>
          ) : (
            <>
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-10">
                        <Checkbox
                          checked={allPageSelected}
                          onCheckedChange={() => toggleSelectAllOnPage()}
                          aria-label="Select all rows on this page"
                        />
                      </TableHead>
                      <TableHead className="w-24">Variant ID</TableHead>
                      <TableHead className="w-32">SKU</TableHead>
                      <TableHead className="w-28">Product</TableHead>
                      <TableHead className="w-24">Channel</TableHead>
                      <TableHead className="w-24">Locale</TableHead>
                      <TableHead>Title</TableHead>
                      <TableHead className="w-40 text-muted-foreground">Generated</TableHead>
                      <TableHead className="w-20"></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {results.map((row: AllGeneratedTitleItem) => (
                      <TableRow key={row.run_id}>
                        <TableCell>
                          <Checkbox
                            checked={selectedRunIds.has(row.run_id)}
                            onCheckedChange={() => toggleSelected(row.run_id)}
                            aria-label={`Select run ${row.run_id}`}
                          />
                        </TableCell>
                        <TableCell className="font-mono text-sm">{row.variant_id}</TableCell>
                        <TableCell className="font-mono text-sm">{row.sku || '—'}</TableCell>
                        <TableCell className="text-sm">{row.product_code || '—'}</TableCell>
                        <TableCell className="text-sm">{row.channel_code || '—'}</TableCell>
                        <TableCell className="text-sm">{row.locale_code || '—'}</TableCell>
                        <TableCell className="max-w-md">
                          {editingRunId === row.run_id ? (
                            <div className="flex items-center gap-2">
                              <Input
                                value={editingText}
                                onChange={(e) => setEditingText(e.target.value)}
                                className="h-7 text-sm"
                                autoFocus
                                onKeyDown={(e) => {
                                  if (e.key === 'Enter') updateMutation.mutate({ runId: row.run_id, title: editingText });
                                  if (e.key === 'Escape') setEditingRunId(null);
                                }}
                              />
                              <Button size="icon" variant="ghost" className="h-7 w-7 shrink-0" onClick={() => updateMutation.mutate({ runId: row.run_id, title: editingText })} disabled={updateMutation.isPending}>
                                <Check className="w-4 h-4 text-green-600" />
                              </Button>
                              <Button size="icon" variant="ghost" className="h-7 w-7 shrink-0" onClick={() => setEditingRunId(null)}>
                                <X className="w-4 h-4" />
                              </Button>
                            </div>
                          ) : (
                            <span className="font-medium">{row.title || '—'}</span>
                          )}
                        </TableCell>
                        <TableCell className="text-muted-foreground text-sm">
                          {formatDateTime(row.generated_at)}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1">
                            <Button
                              size="icon"
                              variant="ghost"
                              className="h-7 w-7"
                              onClick={() => openPolishDialog(row)}
                              title="Polish title with AI"
                              disabled={polishMutation.isPending || acceptPolishMutation.isPending}
                            >
                              <Wand2 className="w-3.5 h-3.5" />
                            </Button>
                            <Button size="icon" variant="ghost" className="h-7 w-7" onClick={() => { setEditingRunId(row.run_id); setEditingText(row.title); }} title="Edit title">
                              <Pencil className="w-3.5 h-3.5" />
                            </Button>
                            <Button size="icon" variant="ghost" className="h-7 w-7 text-destructive hover:text-destructive" onClick={() => { if (confirm('Delete this title?')) deleteMutation.mutate(row.run_id); }} title="Delete title" disabled={deleteMutation.isPending}>
                              <Trash2 className="w-3.5 h-3.5" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between pt-2">
                  <p className="text-sm text-muted-foreground">
                    Showing {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, count)} of {count}
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      disabled={page <= 1}
                    >
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                      disabled={page >= totalPages}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      <Dialog
        open={!!polishDialog}
        onOpenChange={(open) => {
          if (!open) {
            setPolishDialog(null);
            setPolishResult(null);
          }
        }}
      >
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Wand2 className="w-4 h-4" />
              AI title polish
            </DialogTitle>
          </DialogHeader>

          <div className="rounded-md border bg-muted/30 p-3 space-y-3">
            <div className="space-y-1.5">
              <Label className="text-xs">Model</Label>
              <Select value={polishAiModel} onValueChange={setPolishAiModel}>
                <SelectTrigger className="h-8 text-xs w-full md:w-52">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {aiModels.map((m) => (
                    <SelectItem key={m} value={m} className="text-xs">
                      {m}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs">SEO instructions</Label>
              <Input
                value={polishInstructions}
                onChange={(e) => setPolishInstructions(e.target.value)}
                placeholder="SEO guidance for title polish"
                className="h-8 text-xs"
              />
              <div className="flex items-center gap-2 pt-1">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="h-7 text-xs"
                  onClick={() => setPolishInstructions(defaultAiInstructions)}
                >
                  Use SEO preset
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="h-7 text-xs"
                  onClick={() => setPolishInstructions('')}
                >
                  Clear
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  className="h-7 text-xs"
                  onClick={() => {
                    if (!polishDialog) return;
                    setPolishResult(null);
                    polishMutation.mutate({
                      runId: polishDialog.runId,
                      aiModel: polishAiModel,
                      instructions: polishInstructions,
                    });
                  }}
                  disabled={!polishDialog || polishMutation.isPending}
                >
                  Re-run polish
                </Button>
              </div>
            </div>
          </div>

          {polishMutation.isPending ? (
            <div className="flex items-center gap-2 py-4 text-sm text-muted-foreground">
              <Loader2 className="w-4 h-4 animate-spin" />
              Polishing title...
            </div>
          ) : polishResult ? (
            <div className="space-y-4">
              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">Current title</Label>
                <div className="rounded-md border bg-muted/30 px-3 py-2 text-sm">{polishResult.original || polishDialog?.original || '—'}</div>
              </div>
              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">AI suggestion</Label>
                <div className="rounded-md border px-3 py-2 text-sm font-medium">{polishResult.polished || '—'}</div>
              </div>
              {polishResult.explanation ? (
                <div className="space-y-1">
                  <Label className="text-xs text-muted-foreground">What changed</Label>
                  <p className="text-sm text-muted-foreground">{polishResult.explanation}</p>
                </div>
              ) : null}
            </div>
          ) : (
            <div className="space-y-3 py-1">
              <p className="text-sm text-muted-foreground">Could not generate a polished suggestion yet.</p>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => {
                  if (polishDialog) {
                    polishMutation.mutate({
                      runId: polishDialog.runId,
                      aiModel: polishAiModel,
                      instructions: polishInstructions,
                    });
                  }
                }}
                disabled={!polishDialog || polishMutation.isPending}
              >
                Retry polish
              </Button>
            </div>
          )}

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setPolishDialog(null);
                setPolishResult(null);
              }}
            >
              Close
            </Button>
            <Button
              type="button"
              disabled={!polishDialog || !polishResult?.polished || acceptPolishMutation.isPending}
              onClick={() => {
                if (!polishDialog || !polishResult?.polished) return;
                acceptPolishMutation.mutate({ runId: polishDialog.runId, title: polishResult.polished });
              }}
            >
              {acceptPolishMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Applying...
                </>
              ) : (
                'Use polished title'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
