import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { ArrowLeft, Sparkles, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';
import { Link } from 'react-router-dom';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
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
import { Badge } from '@/components/ui/badge';
import {
  getChannels,
  getLocales,
  generateTitles,
  TitleGenerateResponse,
  TitleGenerateOutputItem,
  Channel,
  Locale,
} from '@/lib/api';
import { useToast } from '@/hooks/use-toast';

function parseVariantIds(value: string): number[] {
  return value
    .split(/[,\n]/)
    .map((s) => s.trim())
    .filter(Boolean)
    .map((s) => parseInt(s, 10))
    .filter((n) => !isNaN(n));
}

export default function GenerateTitles() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [channelCode, setChannelCode] = useState('');
  const [localeCode, setLocaleCode] = useState('');
  const [variantIdsText, setVariantIdsText] = useState('');
  const [titleModeOverride, setTitleModeOverride] = useState<string>('');
  const [result, setResult] = useState<TitleGenerateResponse | null>(null);

  const { data: channelsData } = useQuery({
    queryKey: ['channels'],
    queryFn: () => getChannels({ page_size: 200 }),
  });
  const { data: localesData } = useQuery({
    queryKey: ['locales'],
    queryFn: () => getLocales({ page_size: 200 }),
  });

  const channels = (channelsData?.results ?? []) as Channel[];
  const locales = (localesData?.results ?? []) as Locale[];

  const mutation = useMutation({
    mutationFn: generateTitles,
    onSuccess: (data) => {
      setResult(data);
      const generated = data.outputs.filter((o) => o.status === 'generated').length;
      const needsApproval = data.outputs.filter((o) => o.status === 'needs_approval').length;
      toast({
        title: 'Titles generated',
        description: `${generated} generated${needsApproval ? `, ${needsApproval} need approval` : ''}.`,
      });
    },
    onError: (err: { response?: { data?: { detail?: string } }; message?: string }) => {
      toast({
        title: 'Generation failed',
        description: (err as any)?.response?.data?.detail || err?.message || 'Unknown error',
        variant: 'destructive',
      });
    },
  });

  const handleSubmit = () => {
    const ids = parseVariantIds(variantIdsText);
    if (ids.length === 0) {
      toast({ title: 'Enter at least one variant ID', variant: 'destructive' });
      return;
    }
    if (!channelCode) {
      toast({ title: 'Select a channel', variant: 'destructive' });
      return;
    }
    if (!localeCode) {
      toast({ title: 'Select a locale', variant: 'destructive' });
      return;
    }
    setResult(null);
    mutation.mutate({
      variant_ids: ids,
      locale_code: localeCode,
      channel_code: channelCode,
      title_mode_override: titleModeOverride === '' ? undefined : (titleModeOverride as 'auto' | 'review'),
    });
  };

  return (
    <div className="page-container">
      <PageHeader
        title="Generate titles"
        description="Generate titles for product variants by channel and locale. Uses saved head/hook terms and title templates."
        breadcrumbs={[
          { label: 'Dashboard', href: '/' },
          { label: 'Content', href: '/content' },
          { label: 'Generate titles' },
        ]}
        actions={
          <Button variant="outline" asChild>
            <Link to="/content">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Content
            </Link>
          </Button>
        }
      />

      <div className="max-w-4xl space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="w-5 h-5" />
              Title generation
            </CardTitle>
            <CardDescription>
              Choose channel and locale, then enter variant IDs (comma or newline separated). Titles are built from your title templates and saved head/hook terms.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Channel</Label>
                <Select value={channelCode} onValueChange={setChannelCode}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select channel..." />
                  </SelectTrigger>
                  <SelectContent>
                    {channels.map((c) => (
                      <SelectItem key={c.id} value={c.code}>
                        {c.name || c.code}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Locale</Label>
                <Select value={localeCode} onValueChange={setLocaleCode}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select locale..." />
                  </SelectTrigger>
                  <SelectContent>
                    {locales.map((l) => (
                      <SelectItem key={l.id} value={l.code}>
                        {l.name || l.code}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="variantIds">Variant IDs</Label>
              <Textarea
                id="variantIds"
                value={variantIdsText}
                onChange={(e) => setVariantIdsText(e.target.value)}
                placeholder="e.g. 1, 2, 3 or one per line"
                rows={4}
                className="font-mono text-sm"
              />
            </div>

            <div className="space-y-2">
              <Label>Title mode (optional)</Label>
              <Select value={titleModeOverride} onValueChange={setTitleModeOverride}>
                <SelectTrigger className="w-full md:w-48">
                  <SelectValue placeholder="Default" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Default (from settings)</SelectItem>
                  <SelectItem value="auto">Auto-approve</SelectItem>
                  <SelectItem value="review">Require review</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                Override channel/locale policy for this run. Leave default to use Settings → Title rules.
              </p>
            </div>

            <Button
              onClick={handleSubmit}
              disabled={
                !channelCode ||
                !localeCode ||
                !variantIdsText.trim() ||
                mutation.isPending
              }
            >
              {mutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Generating…
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4 mr-2" />
                  Generate titles
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        {result && result.outputs.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                Results
                <Badge variant="secondary">{result.outputs.length} variants</Badge>
              </CardTitle>
              <CardDescription>
                {result.outputs.filter((o) => o.status === 'generated').length} generated,
                {result.outputs.filter((o) => o.status === 'needs_approval').length} need approval in Listings → Titles.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Variant ID</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Title / Preview</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {result.outputs.map((row: TitleGenerateOutputItem) => (
                    <TableRow key={row.variant_id}>
                      <TableCell className="font-mono text-sm">{row.variant_id}</TableCell>
                      <TableCell>
                        {row.status === 'generated' ? (
                          <Badge className="bg-status-success-bg text-status-success">
                            <CheckCircle2 className="w-3 h-3 mr-1" />
                            Generated
                          </Badge>
                        ) : (
                          <Badge variant="secondary">
                            <AlertCircle className="w-3 h-3 mr-1" />
                            Needs approval
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell className="max-w-md">
                        {row.status === 'generated' && row.title && (
                          <span className="text-sm">{row.title}</span>
                        )}
                        {row.status === 'needs_approval' && (
                          <div className="space-y-1 text-sm">
                            {row.preview_title && (
                              <p className="font-medium">{row.preview_title}</p>
                            )}
                            {row.suggestions && row.suggestions.length > 0 && (
                              <p className="text-muted-foreground text-xs">
                                Suggestions: {row.suggestions.slice(0, 3).join(', ')}
                                {row.suggestions.length > 3 ? '…' : ''}
                              </p>
                            )}
                            <p className="text-xs text-muted-foreground">
                              Approve in Listings → open listing → Titles tab.
                            </p>
                          </div>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
