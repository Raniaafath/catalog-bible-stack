import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { ArrowRight, Search, Loader2, Plus, X, Upload, FileSpreadsheet, Download } from 'lucide-react';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { toast } from '@/components/ui/sonner';
import { getLocales, getProductTypes, getChannels, createPlannerRun, importKeywordsCsv } from '@/lib/api';
import { AxiosError } from 'axios';

function getCsvImportErrorMessage(error: unknown): string {
  if (error && typeof error === 'object' && 'response' in error) {
    const data = (error as AxiosError<{ detail?: string | string[] }>).response?.data;
    const detail = data?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) return detail.join(' ');
  }
  if (error instanceof Error) return error.message;
  return 'Import failed. Please check the file format and try again.';
}

type NewRunMode = 'seed' | 'csv';

export default function KeywordsNew() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<NewRunMode>('seed');
  const [locale, setLocale] = useState('');
  const [channel, setChannel] = useState('');
  const [productType, setProductType] = useState('');
  const [seedTerms, setSeedTerms] = useState<string[]>([]);
  const [negativeTerms, setNegativeTerms] = useState<string[]>([]);
  const [seedInput, setSeedInput] = useState('');
  const [negativeInput, setNegativeInput] = useState('');
  const [csvFile, setCsvFile] = useState<File | null>(null);

  const { data: locales } = useQuery({
    queryKey: ['locales'],
    queryFn: getLocales,
  });

  const { data: productTypes } = useQuery({
    queryKey: ['product-types'],
    queryFn: getProductTypes,
  });

  const { data: channels } = useQuery({
    queryKey: ['channels'],
    queryFn: () => getChannels({ page_size: 200 }),
  });

  const createMutation = useMutation({
    mutationFn: createPlannerRun,
    onSuccess: (data) => {
      const runId = (data as { run_id?: number; id?: number }).run_id ?? (data as { id?: number }).id;
      if (runId) navigate(`/keywords/${runId}`);
    },
  });

  const importCsvMutation = useMutation({
    mutationFn: ({ file, params }: { file: File; params: Parameters<typeof importKeywordsCsv>[1] }) =>
      importKeywordsCsv(file, params),
    onSuccess: (data) => {
      navigate(`/keywords/${data.run_id}`);
    },
    onError: (error) => {
      toast.error('CSV import failed', {
        description: getCsvImportErrorMessage(error),
      });
    },
  });

  const addSeedTerm = () => {
    if (seedInput.trim() && !seedTerms.includes(seedInput.trim())) {
      setSeedTerms([...seedTerms, seedInput.trim()]);
      setSeedInput('');
    }
  };

  const addNegativeTerm = () => {
    if (negativeInput.trim() && !negativeTerms.includes(negativeInput.trim())) {
      setNegativeTerms([...negativeTerms, negativeInput.trim()]);
      setNegativeInput('');
    }
  };

  const handleSubmitSeed = (e: React.FormEvent) => {
    e.preventDefault();
    if (locale && productType && seedTerms.length > 0) {
      const productTypeId = productTypes?.results?.find((t) => t.code === productType)?.id;
      createMutation.mutate({
        locale,
        product_type_id: productTypeId,
        seed_terms: seedTerms,
        negative_terms: negativeTerms,
      });
    }
  };

  const handleSubmitCsv = (e: React.FormEvent) => {
    e.preventDefault();
    if (!csvFile || !locale || !channel) return;
    const productTypeId = productType ? productTypes?.results?.find((t) => t.code === productType)?.id : undefined;
    importCsvMutation.mutate({
      file: csvFile,
      params: {
        locale_code: locale,
        channel_code: channel,
        product_type_id: productTypeId ?? undefined,
      },
    });
  };

  return (
    <div className="page-container">
      <PageHeader
        title="New Keyword Run"
        description="Configure and start a keyword planner run"
        breadcrumbs={[
          { label: 'Dashboard', href: '/' },
          { label: 'Keywords', href: '/keywords' },
          { label: 'New Run' },
        ]}
      />

      <div className="max-w-2xl mx-auto">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Search className="w-5 h-5" />
              Keyword run
            </CardTitle>
            <CardDescription>
              Create from seed terms or import a CSV from Google Keyword Planner.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs value={mode} onValueChange={(v) => setMode(v as NewRunMode)} className="w-full">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="seed" className="flex items-center gap-2">
                  <Search className="w-4 h-4" />
                  Seed terms
                </TabsTrigger>
                <TabsTrigger value="csv" className="flex items-center gap-2">
                  <FileSpreadsheet className="w-4 h-4" />
                  Import CSV
                </TabsTrigger>
              </TabsList>

              <TabsContent value="seed" className="mt-6">
                <form onSubmit={handleSubmitSeed} className="space-y-6">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="locale">Locale</Label>
                      <Select value={locale} onValueChange={setLocale}>
                        <SelectTrigger>
                          <SelectValue placeholder="Select locale..." />
                        </SelectTrigger>
                        <SelectContent>
                          {locales?.results?.map((loc) => (
                            <SelectItem key={loc.code} value={loc.code}>
                              {loc.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="productType">Product Type</Label>
                      <Select value={productType} onValueChange={setProductType}>
                        <SelectTrigger>
                          <SelectValue placeholder="Select type..." />
                        </SelectTrigger>
                        <SelectContent>
                          {productTypes?.results?.map((type) => (
                            <SelectItem key={type.id} value={type.code}>
                              {type.category_path || type.default_label || type.code}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label>Seed Terms</Label>
                    <div className="flex gap-2">
                      <Input
                        value={seedInput}
                        onChange={(e) => setSeedInput(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addSeedTerm())}
                        placeholder="Enter a seed keyword..."
                      />
                      <Button type="button" variant="outline" onClick={addSeedTerm}>
                        <Plus className="w-4 h-4" />
                      </Button>
                    </div>
                    {seedTerms.length > 0 && (
                      <div className="flex flex-wrap gap-2 mt-2">
                        {seedTerms.map((term) => (
                          <Badge key={term} variant="secondary" className="gap-1">
                            {term}
                            <X
                              className="w-3 h-3 cursor-pointer"
                              onClick={() => setSeedTerms(seedTerms.filter((t) => t !== term))}
                            />
                          </Badge>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label>Negative Terms (optional)</Label>
                    <div className="flex gap-2">
                      <Input
                        value={negativeInput}
                        onChange={(e) => setNegativeInput(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addNegativeTerm())}
                        placeholder="Enter terms to exclude..."
                      />
                      <Button type="button" variant="outline" onClick={addNegativeTerm}>
                        <Plus className="w-4 h-4" />
                      </Button>
                    </div>
                    {negativeTerms.length > 0 && (
                      <div className="flex flex-wrap gap-2 mt-2">
                        {negativeTerms.map((term) => (
                          <Badge key={term} variant="outline" className="gap-1 text-status-error border-status-error/50">
                            {term}
                            <X
                              className="w-3 h-3 cursor-pointer"
                              onClick={() => setNegativeTerms(negativeTerms.filter((t) => t !== term))}
                            />
                          </Badge>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="flex justify-end gap-3">
                    <Button type="button" variant="outline" onClick={() => navigate('/keywords')}>
                      Cancel
                    </Button>
                    <Button
                      type="submit"
                      disabled={!locale || !productType || seedTerms.length === 0 || createMutation.isPending}
                    >
                      {createMutation.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                      Start Run
                      <ArrowRight className="w-4 h-4 ml-2" />
                    </Button>
                  </div>
                </form>
              </TabsContent>

              <TabsContent value="csv" className="mt-6">
                <form onSubmit={handleSubmitCsv} className="space-y-6">
                  {importCsvMutation.isError && (
                    <Alert variant="destructive">
                      <AlertTitle>CSV import failed</AlertTitle>
                      <AlertDescription className="mt-2 whitespace-pre-wrap">
                        {getCsvImportErrorMessage(importCsvMutation.error)}
                      </AlertDescription>
                    </Alert>
                  )}
                  <div className="rounded-md border bg-muted/40 p-4 text-sm text-muted-foreground space-y-3">
                    <p className="font-medium text-foreground">CSV format</p>
                    <ul className="list-disc list-inside space-y-1">
                      <li><strong>Source:</strong> Export from Google Keyword Planner / Keyword Stats (e.g. &quot;Keyword Stats …&quot; report).</li>
                      <li><strong>Required columns:</strong> <code className="rounded bg-muted px-1">Keyword</code>, <code className="rounded bg-muted px-1">Avg. monthly searches</code>.</li>
                      <li><strong>Optional columns:</strong> <code className="rounded bg-muted px-1">Competition (indexed value)</code>, <code className="rounded bg-muted px-1">Top of page bid (low range)</code>, <code className="rounded bg-muted px-1">Top of page bid (high range)</code>.</li>
                      <li><strong>Format:</strong> Save as <strong>UTF-8</strong> (not UTF-16); first row = header; comma or semicolon delimiter. Extra columns (Currency, monthly breakdown, etc.) are ignored.</li>
                    </ul>
                    <a
                      href="/keyword-stats-example.csv"
                      download="keyword-stats-example.csv"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2 text-primary hover:underline"
                    >
                      <Download className="w-4 h-4" />
                      Download example CSV
                    </a>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Locale</Label>
                      <Select value={locale} onValueChange={setLocale}>
                        <SelectTrigger>
                          <SelectValue placeholder="Select locale..." />
                        </SelectTrigger>
                        <SelectContent>
                          {locales?.results?.map((loc) => (
                            <SelectItem key={loc.code} value={loc.code}>
                              {loc.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label>Channel</Label>
                      <Select value={channel} onValueChange={setChannel}>
                        <SelectTrigger>
                          <SelectValue placeholder="Select channel..." />
                        </SelectTrigger>
                        <SelectContent>
                          {channels?.results?.map((ch) => (
                            <SelectItem key={ch.id} value={ch.code}>
                              {ch.name || ch.code}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label>Product Type (optional)</Label>
                    <Select value={productType} onValueChange={setProductType}>
                      <SelectTrigger>
                        <SelectValue placeholder="Select type (optional)..." />
                      </SelectTrigger>
                      <SelectContent>
                        {productTypes?.results?.map((type) => (
                          <SelectItem key={type.id} value={type.code}>
                            {type.category_path || type.default_label || type.code}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>CSV file</Label>
                    <div className="flex items-center gap-2">
                      <Input
                        type="file"
                        accept=".csv"
                        onChange={(e) => setCsvFile(e.target.files?.[0] ?? null)}
                      />
                      {csvFile && (
                        <span className="text-sm text-muted-foreground">{csvFile.name}</span>
                      )}
                    </div>
                  </div>
                  <div className="flex justify-end gap-3">
                    <Button type="button" variant="outline" onClick={() => navigate('/keywords')}>
                      Cancel
                    </Button>
                    <Button
                      type="submit"
                      disabled={!locale || !channel || !csvFile || importCsvMutation.isPending}
                    >
                      {importCsvMutation.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                      <Upload className="w-4 h-4 mr-2" />
                      Import and open run
                    </Button>
                  </div>
                </form>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
