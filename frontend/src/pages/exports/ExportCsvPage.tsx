import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Download, Loader2, FileText, CheckSquare, Package,
  Languages, Tag, Database, AlertCircle, ChevronRight,
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import { getLocales, getChannels, downloadProductsOneRowCsv, getExportPreview } from '@/lib/api';

export default function ExportCsvPage() {
  const [localeCode, setLocaleCode] = useState('');
  const [channelCode, setChannelCode] = useState('all');
  const [includeDescription, setIncludeDescription] = useState(true);
  const [includeNonTranslatable, setIncludeNonTranslatable] = useState(true);
  const [isDownloading, setIsDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState('');

  const { data: locales } = useQuery({ queryKey: ['locales'], queryFn: () => getLocales() });
  const { data: channels } = useQuery({
    queryKey: ['channels'],
    queryFn: () => getChannels({ page: 1, page_size: 100 }),
  });

  const activeChannels = channels?.results?.filter((c) => c.is_active !== false) ?? [];
  const selectedLocale = locales?.results?.find((l) => l.code === localeCode);
  const selectedChannel = activeChannels.find((c) => c.code === channelCode);

  // Live preview — fetches as soon as locale is selected
  const { data: preview, isFetching: previewLoading, isError: previewError } = useQuery({
    queryKey: ['export-preview', localeCode, channelCode],
    queryFn: () => getExportPreview(localeCode, channelCode !== 'all' ? channelCode : undefined),
    enabled: !!localeCode,
  });

  const totalVariants = preview?.count ?? 0;

  // Column summary based on options
  const columnGroups = [
    { label: 'Product & variant identifiers', count: 5, icon: Package, always: true },
    { label: 'Generated title', count: 1, icon: FileText, always: true },
    { label: 'Generated description', count: 1, icon: Languages, always: false, enabled: includeDescription },
    { label: 'Translated attributes', count: null, icon: Tag, always: true },
    { label: 'Non-translatable attributes', count: null, icon: Database, always: false, enabled: includeNonTranslatable },
  ];

  const handleDownload = async () => {
    if (!localeCode) return;
    setIsDownloading(true);
    setDownloadError('');
    try {
      const blob = await downloadProductsOneRowCsv(
        localeCode,
        channelCode !== 'all' ? channelCode : undefined,
        { includeDescription, includeNonTranslatable }
      );
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      const ch = channelCode !== 'all' ? `_${channelCode}` : '';
      a.href = url;
      a.download = `export_${localeCode}${ch}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setDownloadError('Download failed. Please try again.');
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <div className="page-container">
      <PageHeader
        title="Export CSV"
        description="Download product data as a CSV — one row per variant"
        breadcrumbs={[
          { label: 'Dashboard', href: '/' },
          { label: 'Exports', href: '/exports' },
          { label: 'Export CSV' },
        ]}
      />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 max-w-5xl">

        {/* Left: Configuration */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <FileText className="w-4 h-4" />
              Export Options
            </CardTitle>
            <CardDescription>Choose what to include in the export</CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">

            <div className="space-y-2">
              <Label>Language (locale) <span className="text-destructive">*</span></Label>
              <Select value={localeCode} onValueChange={setLocaleCode}>
                <SelectTrigger>
                  <SelectValue placeholder="Select language..." />
                </SelectTrigger>
                <SelectContent>
                  {locales?.results?.map((loc) => (
                    <SelectItem key={loc.id} value={loc.code}>
                      {loc.code}{(loc as any).name ? ` — ${(loc as any).name}` : ''}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Channel</Label>
              <Select value={channelCode} onValueChange={setChannelCode}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All channels</SelectItem>
                  {activeChannels.map((ch) => (
                    <SelectItem key={ch.id} value={ch.code}>
                      {ch.name} ({ch.code})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <Separator />

            <div className="space-y-3">
              <Label>Additional columns</Label>
              <label className="flex items-start gap-3 cursor-pointer group">
                <Checkbox
                  className="mt-0.5"
                  checked={includeDescription}
                  onCheckedChange={(v) => setIncludeDescription(!!v)}
                />
                <div>
                  <p className="text-sm font-medium group-hover:text-foreground transition-colors">Generated description</p>
                  <p className="text-xs text-muted-foreground">AI-generated product description text</p>
                </div>
              </label>
              <label className="flex items-start gap-3 cursor-pointer group">
                <Checkbox
                  className="mt-0.5"
                  checked={includeNonTranslatable}
                  onCheckedChange={(v) => setIncludeNonTranslatable(!!v)}
                />
                <div>
                  <p className="text-sm font-medium group-hover:text-foreground transition-colors">Non-translatable attributes</p>
                  <p className="text-xs text-muted-foreground">Dimensions, materials, SKUs, price, stock, etc.</p>
                </div>
              </label>
            </div>

          </CardContent>
        </Card>

        {/* Right: Preview */}
        <div className="flex flex-col gap-4">

          {!localeCode ? (
            <Card className="flex-1 border-dashed">
              <CardContent className="flex flex-col items-center justify-center h-full min-h-[200px] text-center gap-3 py-10">
                <div className="p-3 rounded-full bg-muted">
                  <ChevronRight className="w-5 h-5 text-muted-foreground" />
                </div>
                <p className="text-sm text-muted-foreground">Select a language to see a preview of what will be exported</p>
              </CardContent>
            </Card>
          ) : (
            <>
              {/* Stats bar */}
              <Card>
                <CardContent className="pt-4 pb-4">
                  {previewLoading ? (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Loading preview…
                    </div>
                  ) : previewError ? (
                    <div className="flex items-center gap-2 text-sm text-destructive">
                      <AlertCircle className="w-4 h-4" />
                      Could not load preview
                    </div>
                  ) : (
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-2xl font-bold">{totalVariants.toLocaleString()}</p>
                        <p className="text-sm text-muted-foreground">
                          variants in{' '}
                          <span className="font-medium text-foreground">{localeCode}</span>
                          {channelCode !== 'all' && (
                            <> · <span className="font-medium text-foreground">{selectedChannel?.name ?? channelCode}</span></>
                          )}
                        </p>
                      </div>
                      <Badge variant={totalVariants > 0 ? 'default' : 'secondary'}>
                        {totalVariants > 0 ? 'Ready' : 'No data'}
                      </Badge>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Columns overview */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Columns in this export</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 pb-4">
                  {columnGroups.map((group) => {
                    const included = group.always || group.enabled;
                    return (
                      <div
                        key={group.label}
                        className={`flex items-center gap-3 text-sm ${included ? '' : 'opacity-40'}`}
                      >
                        <group.icon className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
                        <span className={included ? 'text-foreground' : 'text-muted-foreground line-through'}>
                          {group.label}
                        </span>
                        {group.count !== null && (
                          <span className="ml-auto text-xs text-muted-foreground">{group.count} col</span>
                        )}
                        {!group.always && (
                          <CheckSquare className={`w-3.5 h-3.5 ml-auto shrink-0 ${included ? 'text-primary' : 'text-muted-foreground'}`} />
                        )}
                      </div>
                    );
                  })}
                </CardContent>
              </Card>

              {/* Sample rows */}
              {!previewLoading && !previewError && (preview?.results?.length ?? 0) > 0 && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">Sample rows</CardTitle>
                  </CardHeader>
                  <CardContent className="pb-4">
                    <div className="rounded-md border overflow-hidden">
                      <table className="w-full text-xs">
                        <thead className="bg-muted">
                          <tr>
                            <th className="text-left px-3 py-2 font-medium text-muted-foreground">SKU</th>
                            <th className="text-left px-3 py-2 font-medium text-muted-foreground">Title</th>
                            <th className="text-left px-3 py-2 font-medium text-muted-foreground">Generated</th>
                          </tr>
                        </thead>
                        <tbody>
                          {preview?.results?.map((row, i) => (
                            <tr key={row.run_id} className={i % 2 === 0 ? 'bg-background' : 'bg-muted/30'}>
                              <td className="px-3 py-2 font-mono text-muted-foreground whitespace-nowrap">{row.sku}</td>
                              <td className="px-3 py-2 max-w-[200px]">
                                <span
                                  className="block truncate"
                                  title={row.title}
                                >
                                  {row.title || <span className="text-muted-foreground italic">No title</span>}
                                </span>
                              </td>
                              <td className="px-3 py-2 text-muted-foreground whitespace-nowrap">
                                {formatDistanceToNow(new Date(row.generated_at), { addSuffix: true })}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    {totalVariants > 5 && (
                      <p className="text-xs text-muted-foreground mt-2 text-center">
                        Showing 5 of {totalVariants.toLocaleString()} variants
                      </p>
                    )}
                  </CardContent>
                </Card>
              )}
            </>
          )}

          {/* Download button */}
          {downloadError && (
            <p className="text-sm text-destructive flex items-center gap-1.5">
              <AlertCircle className="w-4 h-4" />
              {downloadError}
            </p>
          )}
          <Button
            size="lg"
            className="w-full"
            disabled={!localeCode || totalVariants === 0 || isDownloading || previewLoading}
            onClick={handleDownload}
          >
            {isDownloading ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <Download className="w-4 h-4 mr-2" />
            )}
            {isDownloading
              ? 'Preparing download…'
              : totalVariants > 0
              ? `Download CSV (${totalVariants.toLocaleString()} rows)`
              : 'Download CSV'}
          </Button>
        </div>
      </div>
    </div>
  );
}
