import { useState, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { FileText, Download, Loader2, FileSpreadsheet } from 'lucide-react';
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  getLocales,
  getChannels,
  getAllGeneratedTitles,
  type AllGeneratedTitleItem,
  type Locale,
  type Channel,
} from '@/lib/api';
import { useToast } from '@/hooks/use-toast';
import * as XLSX from 'xlsx';

const PAGE_SIZE = 100;

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
  const [localeCode, setLocaleCode] = useState<string>('');
  const [channelCode, setChannelCode] = useState<string>('');
  const [page, setPage] = useState(1);

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

  const { data, isLoading } = useQuery({
    queryKey: ['all-generated-titles', localeCode || null, channelCode || null, page],
    queryFn: () =>
      getAllGeneratedTitles({
        ...(localeCode && { locale_code: localeCode }),
        ...(channelCode && { channel_code: channelCode }),
        page,
        page_size: PAGE_SIZE,
      }),
  });

  const results = data?.results ?? [];
  const count = data?.count ?? 0;
  const totalPages = Math.max(1, Math.ceil(count / PAGE_SIZE));

  const exportData = useCallback(async (format: 'csv' | 'xlsx') => {
    try {
      const params: { locale_code?: string; channel_code?: string; page?: number; page_size?: number } = {
        page: 1,
        page_size: 5000,
      };
      if (localeCode) params.locale_code = localeCode;
      if (channelCode) params.channel_code = channelCode;
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
  }, [localeCode, channelCode, toast]);

  return (
    <div className="page-container">
      <PageHeader
        title="All generated titles"
        description="View and export all generated titles in the database, filtered by language and marketplace."
        breadcrumbs={[
          { label: 'Dashboard', href: '/' },
          { label: 'Content', href: '/content' },
          { label: 'Generated titles' },
        ]}
      />

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="w-5 h-5" />
            Generated titles
          </CardTitle>
          <CardDescription>
            Latest generated title per variant, per language, per marketplace. Use filters below and export to CSV or Excel.
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
                  <SelectItem value="">All languages</SelectItem>
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
                  <SelectItem value="">All marketplaces</SelectItem>
                  {channels.map((c) => (
                    <SelectItem key={c.code} value={c.code}>
                      {c.code}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex gap-2 ml-auto">
              <Button variant="outline" size="sm" onClick={() => exportData('csv')} disabled={count === 0}>
                <Download className="w-4 h-4 mr-2" />
                Export CSV
              </Button>
              <Button variant="outline" size="sm" onClick={() => exportData('xlsx')} disabled={count === 0}>
                <FileSpreadsheet className="w-4 h-4 mr-2" />
                Export Excel
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
                      <TableHead className="w-24">Variant ID</TableHead>
                      <TableHead className="w-32">SKU</TableHead>
                      <TableHead className="w-28">Product</TableHead>
                      <TableHead className="w-24">Channel</TableHead>
                      <TableHead className="w-24">Locale</TableHead>
                      <TableHead>Title</TableHead>
                      <TableHead className="w-40 text-muted-foreground">Generated</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {results.map((row: AllGeneratedTitleItem) => (
                      <TableRow key={`${row.variant_id}-${row.channel_code}-${row.locale_code}`}>
                        <TableCell className="font-mono text-sm">{row.variant_id}</TableCell>
                        <TableCell className="font-mono text-sm">{row.sku || '—'}</TableCell>
                        <TableCell className="text-sm">{row.product_code || '—'}</TableCell>
                        <TableCell className="text-sm">{row.channel_code || '—'}</TableCell>
                        <TableCell className="text-sm">{row.locale_code || '—'}</TableCell>
                        <TableCell className="max-w-md font-medium">{row.title || '—'}</TableCell>
                        <TableCell className="text-muted-foreground text-sm">
                          {formatDateTime(row.generated_at)}
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
    </div>
  );
}
