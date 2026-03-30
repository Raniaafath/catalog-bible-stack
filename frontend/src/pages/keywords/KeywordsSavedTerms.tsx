import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Type, Loader2, Trash2, Globe, Store, ArrowRight, Plus } from 'lucide-react';
import { PageHeader } from '@/components/PageHeader';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
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
  getSavedTerms,
  removeHeadTerm,
  removeHookTerm,
  addHeadTerm,
  addHookTerm,
  getApiErrorMessage,
  type SavedTermsHeadByProductType,
  type SavedTermsHookByProduct,
} from '@/lib/api';
import { useToast } from '@/hooks/use-toast';
import { Alert, AlertDescription } from '@/components/ui/alert';

export default function KeywordsSavedTerms() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [localeId, setLocaleId] = useState<number | null>(null);
  const [channelId, setChannelId] = useState<number | ''>('');

  // Per-item delete loading state
  const [removingHeadId, setRemovingHeadId] = useState<number | null>(null);
  const [removingHookId, setRemovingHookId] = useState<number | null>(null);

  // Inline add-term inputs keyed by product_type_id / product_id
  const [addHeadInputs, setAddHeadInputs] = useState<Record<number, string>>({});
  const [addHookInputs, setAddHookInputs] = useState<Record<number, string>>({});
  const [addHookPriorities, setAddHookPriorities] = useState<Record<number, string>>({});

  // Always-on query just for the filter dropdowns (no locale_id needed)
  const { data: filtersData } = useQuery({
    queryKey: ['saved-terms-filters'],
    queryFn: () => getSavedTerms({}),
  });

  // Terms query — only fires when a locale is selected
  const { data: termsData, isLoading: termsLoading } = useQuery({
    queryKey: ['saved-terms', localeId, channelId || null],
    queryFn: () =>
      getSavedTerms({
        locale_id: localeId!,
        channel_id: typeof channelId === 'number' ? channelId : undefined,
      }),
    enabled: !!localeId,
  });

  const removeHeadMutation = useMutation({
    mutationFn: ({ productTypeId, synonymId }: { productTypeId: number; synonymId: number }) =>
      removeHeadTerm(productTypeId, synonymId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['saved-terms'] });
      toast({ title: 'Head term removed' });
    },
    onError: (err) =>
      toast({ title: 'Failed to remove head term', description: getApiErrorMessage(err), variant: 'destructive' }),
    onSettled: () => setRemovingHeadId(null),
  });

  const removeHookMutation = useMutation({
    mutationFn: ({ productId, hookTermId }: { productId: number; hookTermId: number }) =>
      removeHookTerm(productId, hookTermId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['saved-terms'] });
      toast({ title: 'Hook term removed' });
    },
    onError: (err) =>
      toast({ title: 'Failed to remove hook term', description: getApiErrorMessage(err), variant: 'destructive' }),
    onSettled: () => setRemovingHookId(null),
  });

  const addHeadMutation = useMutation({
    mutationFn: ({ productTypeId, term }: { productTypeId: number; term: string }) =>
      addHeadTerm(productTypeId, {
        locale_id: localeId!,
        channel_id: typeof channelId === 'number' ? channelId : null,
        term,
      }),
    onSuccess: (_data, { productTypeId }) => {
      queryClient.invalidateQueries({ queryKey: ['saved-terms'] });
      setAddHeadInputs((prev) => ({ ...prev, [productTypeId]: '' }));
      toast({ title: 'Head term added' });
    },
    onError: (err) =>
      toast({ title: 'Failed to add head term', description: getApiErrorMessage(err), variant: 'destructive' }),
  });

  const addHookMutation = useMutation({
    mutationFn: ({ productId, term, priority }: { productId: number; term: string; priority: number }) =>
      addHookTerm(productId, {
        locale_id: localeId!,
        channel_id: typeof channelId === 'number' ? channelId : null,
        term,
        priority,
      }),
    onSuccess: (_data, { productId }) => {
      queryClient.invalidateQueries({ queryKey: ['saved-terms'] });
      setAddHookInputs((prev) => ({ ...prev, [productId]: '' }));
      setAddHookPriorities((prev) => ({ ...prev, [productId]: '' }));
      toast({ title: 'Hook term added' });
    },
    onError: (err) =>
      toast({ title: 'Failed to add hook term', description: getApiErrorMessage(err), variant: 'destructive' }),
  });

  const locales = filtersData?.locales ?? [];
  const channels = filtersData?.channels ?? [];
  const headByProductType = (termsData?.head_terms_by_product_type ?? []) as SavedTermsHeadByProductType[];
  const hookByProduct = (termsData?.hook_terms_by_product ?? []) as SavedTermsHookByProduct[];

  const selectedChannelId = channelId === '' ? null : channelId;

  return (
    <div className="page-container">
      <PageHeader
        title="Saved terms"
        description="Head and hook terms by language and marketplace. Used for title generation."
        breadcrumbs={[
          { label: 'Dashboard', href: '/' },
          { label: 'Keywords', href: '/keywords' },
          { label: 'Saved terms' },
        ]}
      />
      <Alert className="mb-6 bg-muted/50 border-muted-foreground/20">
        <ArrowRight className="h-4 w-4" />
        <AlertDescription>
          <strong>Next:</strong> Create a title template for your product type and locale in{' '}
          <Link to="/groups" className="font-medium text-primary underline underline-offset-2">
            Listings
          </Link>
          {' '}→ open a listing → <strong>Titles</strong> tab (use &quot;Create default template&quot; if none exist), then generate titles.
        </AlertDescription>
      </Alert>

      {/* Filters */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Globe className="w-4 h-4 text-muted-foreground" />
            Language & marketplace
          </CardTitle>
          <CardDescription>
            Choose a locale to see head terms (by product type) and hook terms (by product). Optionally filter by channel.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-4">
          <div className="flex flex-col gap-2">
            <Label className="text-sm">Language (locale)</Label>
            <Select
              value={localeId?.toString() ?? ''}
              onValueChange={(v) => setLocaleId(v ? Number(v) : null)}
            >
              <SelectTrigger className="w-56">
                <SelectValue placeholder="Select locale" />
              </SelectTrigger>
              <SelectContent>
                {locales.map((loc) => (
                  <SelectItem key={loc.id} value={loc.id.toString()}>
                    {loc.code} {loc.name ? `— ${loc.name}` : ''}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-col gap-2">
            <Label className="text-sm">Marketplace (channel)</Label>
            <Select
              value={selectedChannelId === null ? 'all' : selectedChannelId.toString()}
              onValueChange={(v) => setChannelId(v === 'all' ? '' : Number(v))}
            >
              <SelectTrigger className="w-56">
                <SelectValue placeholder="All" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All</SelectItem>
                {channels.map((ch) => (
                  <SelectItem key={ch.id} value={ch.id.toString()}>
                    {ch.code} {ch.name ? `— ${ch.name}` : ''}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {!localeId && (
        <Card className="border-dashed">
          <CardContent className="py-12 text-center text-muted-foreground">
            <Type className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p className="font-medium">Select a language to see saved terms</p>
            <p className="text-sm mt-1">Head terms are grouped by product type; hook terms by product.</p>
          </CardContent>
        </Card>
      )}

      {localeId && termsLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
        </div>
      )}

      {localeId && !termsLoading && (
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Head terms by product type */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Type className="w-4 h-4 text-muted-foreground" />
                Head terms (by product type)
              </CardTitle>
              <CardDescription>
                General product-type synonyms for this locale. One set per product type.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 max-h-[calc(100vh-380px)] overflow-auto">
              {headByProductType.length === 0 ? (
                <p className="text-sm text-muted-foreground py-4">No head terms for this locale and channel.</p>
              ) : (
                headByProductType.map((pt) => {
                  const inputVal = addHeadInputs[pt.product_type_id] ?? '';
                  return (
                    <div
                      key={pt.product_type_id}
                      className="rounded-lg border bg-muted/20 p-3 space-y-2"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2 min-w-0">
                          <span className="font-medium text-sm">
                            {pt.product_type_code || pt.default_label || `Product type #${pt.product_type_id}`}
                          </span>
                          {pt.default_label && pt.product_type_code && (
                            <span className="text-xs text-muted-foreground truncate">{pt.default_label}</span>
                          )}
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 w-7 p-0 text-muted-foreground hover:text-foreground shrink-0"
                          title="Add head term"
                          onClick={() =>
                            setAddHeadInputs((prev) =>
                              pt.product_type_id in prev ? prev : { ...prev, [pt.product_type_id]: '' }
                            )
                          }
                        >
                          <Plus className="w-3.5 h-3.5" />
                        </Button>
                      </div>
                      <ul className="space-y-1.5">
                        {pt.terms.map((t) => (
                          <li
                            key={t.id ?? t.term}
                            className="flex items-center justify-between gap-2 text-sm py-1 px-2 rounded bg-background/60"
                          >
                            <span className="font-medium truncate">{t.term}</span>
                            {t.source === 'synonym' && t.id != null ? (
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-7 w-7 p-0 text-muted-foreground hover:text-destructive shrink-0"
                                title="Remove head term"
                                onClick={() => {
                                  setRemovingHeadId(t.id!);
                                  removeHeadMutation.mutate({
                                    productTypeId: pt.product_type_id,
                                    synonymId: t.id!,
                                  });
                                }}
                                disabled={removingHeadId === t.id}
                              >
                                {removingHeadId === t.id ? (
                                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                ) : (
                                  <Trash2 className="w-3.5 h-3.5" />
                                )}
                              </Button>
                            ) : (
                              <span className="text-xs text-muted-foreground shrink-0">label</span>
                            )}
                          </li>
                        ))}
                      </ul>
                      {/* Inline add form */}
                      {pt.product_type_id in addHeadInputs && (
                        <div className="flex items-center gap-2 pt-1">
                          <Input
                            className="h-7 text-sm"
                            placeholder="New head term"
                            value={inputVal}
                            onChange={(e) =>
                              setAddHeadInputs((prev) => ({ ...prev, [pt.product_type_id]: e.target.value }))
                            }
                            onKeyDown={(e) => {
                              if (e.key === 'Enter' && inputVal.trim()) {
                                addHeadMutation.mutate({ productTypeId: pt.product_type_id, term: inputVal.trim() });
                              }
                            }}
                          />
                          <Button
                            size="sm"
                            className="h-7 shrink-0"
                            disabled={!inputVal.trim() || addHeadMutation.isPending}
                            onClick={() =>
                              addHeadMutation.mutate({ productTypeId: pt.product_type_id, term: inputVal.trim() })
                            }
                          >
                            {addHeadMutation.isPending ? (
                              <Loader2 className="w-3.5 h-3.5 animate-spin" />
                            ) : (
                              'Save'
                            )}
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-7 shrink-0"
                            onClick={() =>
                              setAddHeadInputs((prev) => {
                                const next = { ...prev };
                                delete next[pt.product_type_id];
                                return next;
                              })
                            }
                          >
                            Cancel
                          </Button>
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </CardContent>
          </Card>

          {/* Hook terms by product */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Store className="w-4 h-4 text-muted-foreground" />
                Hook terms (by product)
              </CardTitle>
              <CardDescription>
                Product-specific terms (e.g. colour, material) for this locale. One set per product.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 max-h-[calc(100vh-380px)] overflow-auto">
              {hookByProduct.length === 0 ? (
                <p className="text-sm text-muted-foreground py-4">No hook terms for this locale and channel.</p>
              ) : (
                hookByProduct.map((prod) => {
                  const inputVal = addHookInputs[prod.product_id] ?? '';
                  const priorityVal = addHookPriorities[prod.product_id] ?? '';
                  return (
                    <div
                      key={prod.product_id}
                      className="rounded-lg border bg-muted/20 p-3 space-y-2"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2 min-w-0">
                          <span className="font-medium text-sm">
                            {prod.product_code || prod.default_label || `Product #${prod.product_id}`}
                          </span>
                          {prod.default_label && prod.product_code && (
                            <span className="text-xs text-muted-foreground truncate">{prod.default_label}</span>
                          )}
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 w-7 p-0 text-muted-foreground hover:text-foreground shrink-0"
                          title="Add hook term"
                          onClick={() =>
                            setAddHookInputs((prev) =>
                              prod.product_id in prev ? prev : { ...prev, [prod.product_id]: '' }
                            )
                          }
                        >
                          <Plus className="w-3.5 h-3.5" />
                        </Button>
                      </div>
                      <ul className="space-y-1.5">
                        {prod.terms.map((t) => (
                          <li
                            key={t.id}
                            className="flex items-center justify-between gap-2 text-sm py-1 px-2 rounded bg-background/60"
                          >
                            <div className="flex items-center gap-2 min-w-0">
                              <span className="font-medium truncate">{t.term}</span>
                              {t.priority !== 0 && (
                                <span className="text-xs text-muted-foreground shrink-0">
                                  p{t.priority}
                                </span>
                              )}
                            </div>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-7 w-7 p-0 text-muted-foreground hover:text-destructive shrink-0"
                              title="Remove hook term"
                              onClick={() => {
                                setRemovingHookId(t.id);
                                removeHookMutation.mutate({
                                  productId: prod.product_id,
                                  hookTermId: t.id,
                                });
                              }}
                              disabled={removingHookId === t.id}
                            >
                              {removingHookId === t.id ? (
                                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                              ) : (
                                <Trash2 className="w-3.5 h-3.5" />
                              )}
                            </Button>
                          </li>
                        ))}
                      </ul>
                      {/* Inline add form */}
                      {prod.product_id in addHookInputs && (
                        <div className="flex items-center gap-2 pt-1">
                          <Input
                            className="h-7 text-sm"
                            placeholder="New hook term"
                            value={inputVal}
                            onChange={(e) =>
                              setAddHookInputs((prev) => ({ ...prev, [prod.product_id]: e.target.value }))
                            }
                            onKeyDown={(e) => {
                              if (e.key === 'Enter' && inputVal.trim()) {
                                addHookMutation.mutate({
                                  productId: prod.product_id,
                                  term: inputVal.trim(),
                                  priority: Number(priorityVal) || 0,
                                });
                              }
                            }}
                          />
                          <Input
                            className="h-7 text-sm w-16 shrink-0"
                            type="number"
                            placeholder="Pri"
                            title="Priority (higher = used first)"
                            value={priorityVal}
                            onChange={(e) =>
                              setAddHookPriorities((prev) => ({ ...prev, [prod.product_id]: e.target.value }))
                            }
                          />
                          <Button
                            size="sm"
                            className="h-7 shrink-0"
                            disabled={!inputVal.trim() || addHookMutation.isPending}
                            onClick={() =>
                              addHookMutation.mutate({
                                productId: prod.product_id,
                                term: inputVal.trim(),
                                priority: Number(priorityVal) || 0,
                              })
                            }
                          >
                            {addHookMutation.isPending ? (
                              <Loader2 className="w-3.5 h-3.5 animate-spin" />
                            ) : (
                              'Save'
                            )}
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-7 shrink-0"
                            onClick={() =>
                              setAddHookInputs((prev) => {
                                const next = { ...prev };
                                delete next[prod.product_id];
                                return next;
                              })
                            }
                          >
                            Cancel
                          </Button>
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
