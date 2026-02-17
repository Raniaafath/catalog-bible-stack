import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft,
  Layers,
  Store,
  Package,
  Settings2,
  Trash2,
  Plus,
  CheckCircle2,
  AlertCircle,
  Loader2,
  TrendingUp,
  X,
  Pencil,
  Languages,
  Search,
  FileText,
  Clock,
  GripVertical,
  Type,
  Link2,
} from 'lucide-react';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  getChannelListing,
  getListingDifferences,
  setListingAxes,
  moveVariantsToListing,
  removeVariantsFromListing,
  updateChannelListing,
  getAvailableVariantsForListing,
  getLocales,
  getAvailableTemplatesForListing,
  createDefaultTemplateForListing,
  generateListingTitles,
  getListingGeneratedTitles,
  updateListingGeneratedTitle,
  getProductTypeAttributes,
  getSavedTerms,
  getTemplateParts,
  createTemplatePart,
  deleteTemplatePart,
  TEMPLATE_PART_TYPES,
  getProductHeadSelection,
  setProductHeadSelection,
  clearProductHeadSelection,
  ChannelListingDetail,
  ListingDifferences,
  AvailableVariantForListing,
  VariantAttributeDetailsResponse,
  VariantAttributeDetailsItem,
  VariantAttributeDetailsResponse as VariantDetailsResponse,
  getVariantAttributeDetails,
  TemplatePart,
  ProductTypeAttribute,
  VariantAttributeValueWrite,
  createVariantAttributeValue,
  updateVariantAttributeValue,
  deleteVariantAttributeValue,
  createTranslationTask,
} from '@/lib/api';
import { getApiErrorMessage } from '@/lib/api';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useToast } from '@/hooks/use-toast';

/** Format date for display; avoids dateStyle/timeStyle which can throw in some environments. */
function formatDateTime(isoOrDate: string | Date | null | undefined): string {
  if (isoOrDate == null) return '—';
  try {
    const d = typeof isoOrDate === 'string' ? new Date(isoOrDate) : isoOrDate;
    if (Number.isNaN(d.getTime())) return '—';
    return d.toLocaleString(undefined, {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    try {
      const d = typeof isoOrDate === 'string' ? new Date(isoOrDate) : isoOrDate;
      return d.toISOString().slice(0, 16).replace('T', ' ');
    } catch {
      return '—';
    }
  }
}

export default function GroupDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const listingId = parseInt(id || '0');

  const [activeTab, setActiveTab] = useState('variants');
  const [showAddVariantsDialog, setShowAddVariantsDialog] = useState(false);
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [selectedVariantIds, setSelectedVariantIds] = useState<number[]>([]);
  const [selectedAxes, setSelectedAxes] = useState<number[]>([]);
  
  // Edit form state
  const [editName, setEditName] = useState('');
  const [editIsDefault, setEditIsDefault] = useState(true);
  
  // Title generation state
  const [selectedLocale, setSelectedLocale] = useState('');
  const [selectedTemplate, setSelectedTemplate] = useState<number | null>(null);
  const [addVariantsSearch, setAddVariantsSearch] = useState('');
  const [detailsVariantId, setDetailsVariantId] = useState<number | null>(null);
  const [lastUntranslatedValues, setLastUntranslatedValues] = useState<Array<{ attribute_value_id: number; code: string; attr_code: string; attribute_id?: number }> | null>(null);
  const [editingTitleVariantId, setEditingTitleVariantId] = useState<number | null>(null);
  const [editingTitleValue, setEditingTitleValue] = useState('');

  // Fetch listing details
  const { data: listing, isLoading, error } = useQuery({
    queryKey: ['channel-listing', listingId],
    queryFn: () => getChannelListing(listingId),
    enabled: !!listingId,
  });

  // Fetch differences
  const { data: differences, isLoading: differencesLoading } = useQuery({
    queryKey: ['listing-differences', listingId],
    queryFn: () => getListingDifferences(listingId),
    enabled: !!listingId && activeTab === 'axes',
  });

  // Fetch available variants for this listing (same product, not already in listing) with attributes
  const { data: availableVariantsData, isLoading: variantsLoading } = useQuery({
    queryKey: ['listing-available-variants', listingId],
    queryFn: () => getAvailableVariantsForListing(listingId),
    enabled: showAddVariantsDialog && !!listingId,
  });
  
  // Fetch locales for title generation
  const { data: locales } = useQuery({
    queryKey: ['locales'],
    queryFn: getLocales,
    enabled: activeTab === 'titles',
  });
  
  // Product type attributes (to show which attributes/values are translatable)
  const { data: productTypeAttributes } = useQuery({
    queryKey: ['product-type-attributes', listing?.product_type_id],
    queryFn: () => getProductTypeAttributes(listing!.product_type_id),
    enabled: activeTab === 'titles' && !!listing?.product_type_id,
  });
  
  // Fetch available templates
  const { data: templatesData, isLoading: templatesLoading } = useQuery({
    queryKey: ['listing-templates', listingId, selectedLocale],
    queryFn: () => getAvailableTemplatesForListing(listingId, selectedLocale),
    enabled: activeTab === 'titles' && !!selectedLocale,
  });

  // Fetch generated titles for this listing + locale (shown in Titles tab)
  const { data: generatedTitlesData, isLoading: generatedTitlesLoading } = useQuery({
    queryKey: ['listing-generated-titles', listingId, selectedLocale],
    queryFn: () => getListingGeneratedTitles(listingId, selectedLocale),
    enabled: activeTab === 'titles' && !!selectedLocale && !!listingId,
  });

  // Resolve locale id for saved terms (locales from getLocales have id + code)
  const localeIdForSavedTerms =
    selectedLocale && locales?.results?.length
      ? (locales.results as Array<{ id: number; code: string }>).find((l) => l.code === selectedLocale)?.id
      : null;

  // Saved head/hook terms for this listing's locale and channel (for Build template section)
  const { data: savedTermsData } = useQuery({
    queryKey: ['saved-terms', localeIdForSavedTerms ?? 'none', listing?.channel_id ?? 'none'],
    queryFn: () =>
      getSavedTerms({
        locale_id: localeIdForSavedTerms ?? undefined,
        channel_id: listing?.channel_id ?? undefined,
      }),
    enabled: activeTab === 'titles' && !!localeIdForSavedTerms && listing?.channel_id != null,
  });

  // Template parts for the selected template (for drag-and-drop build)
  const { data: templatePartsData, isLoading: templatePartsLoading } = useQuery({
    queryKey: ['template-parts', selectedTemplate],
    queryFn: () => getTemplateParts(selectedTemplate!),
    enabled: activeTab === 'titles' && !!selectedTemplate,
  });

  // Local order of template parts (for drag reorder before save)
  const [orderedParts, setOrderedParts] = useState<TemplatePart[]>([]);
  const [draggedPartIndex, setDraggedPartIndex] = useState<number | null>(null);

  useEffect(() => {
    if (templatePartsData?.length) {
      const sorted = [...templatePartsData].sort((a, b) => a.position - b.position);
      setOrderedParts(sorted);
    } else {
      setOrderedParts([]);
    }
  }, [templatePartsData]);

  const saveTemplateOrderMutation = useMutation({
    mutationFn: async () => {
      if (!selectedTemplate || orderedParts.length === 0) return;
      const current = (templatePartsData ?? []) as TemplatePart[];
      for (const p of current) {
        await deleteTemplatePart(p.id);
      }
      for (let i = 0; i < orderedParts.length; i++) {
        const p = orderedParts[i];
        await createTemplatePart({
          template_id: selectedTemplate,
          position: i,
          part_type: p.part_type,
          literal_text: p.part_type === 'literal' ? (p.literal_text ?? '') : undefined,
          attribute_id: (p.part_type === 'axis_attribute' || p.part_type === 'attribute_value') ? p.attribute_id ?? null : undefined,
        });
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['template-parts', selectedTemplate] });
      queryClient.invalidateQueries({ queryKey: ['listing-templates', listingId, selectedLocale] });
      toast({ title: 'Template order saved' });
    },
    onError: (err: unknown) => {
      toast({
        title: 'Failed to save order',
        description: String((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail),
        variant: 'destructive',
      });
    },
  });

  const handlePartDragStart = (index: number) => setDraggedPartIndex(index);
  const handlePartDragEnd = () => setDraggedPartIndex(null);
  const handlePartDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer) e.dataTransfer.dropEffect = 'move';
  };
  const handlePartDrop = (e: React.DragEvent, dropIndex: number) => {
    e.preventDefault();
    if (draggedPartIndex == null || draggedPartIndex === dropIndex) {
      setDraggedPartIndex(null);
      return;
    }
    const next = [...orderedParts];
    const [removed] = next.splice(draggedPartIndex, 1);
    next.splice(dropIndex, 0, removed);
    setOrderedParts(next);
    setDraggedPartIndex(null);
  };

  // Head term selection (manual choice from saved head terms)
  const {
    data: headSelectionData,
  } = useQuery({
    queryKey: ['product-head-selection', listing?.product_id, selectedLocale, listing?.channel_code],
    queryFn: () =>
      getProductHeadSelection(listing!.product_id, {
        locale_code: selectedLocale,
        channel_code: listing!.channel_code || '',
      }),
    enabled:
      activeTab === 'titles' &&
      !!selectedLocale &&
      !!listing?.product_id &&
      !!listing?.channel_code,
  });

  const setHeadSelectionMutation = useMutation({
    mutationFn: async (payload: { head_text: string }) => {
      if (!listing?.product_id || !listing.channel_code || !selectedLocale) return;
      return setProductHeadSelection(listing.product_id, {
        locale_code: selectedLocale,
        channel_code: listing.channel_code,
        head_text: payload.head_text,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['product-head-selection', listing?.product_id, selectedLocale, listing?.channel_code],
      });
      toast({ title: 'Head term saved', description: 'New head term will be used for this locale & channel.' });
    },
    onError: (err: unknown) => {
      toast({
        title: 'Failed to save head term',
        description: getApiErrorMessage(err),
        variant: 'destructive',
      });
    },
  });

  const clearHeadSelectionMutation = useMutation({
    mutationFn: async () => {
      if (!listing?.product_id || !listing.channel_code || !selectedLocale) return;
      return clearProductHeadSelection(listing.product_id, {
        locale_code: selectedLocale,
        channel_code: listing.channel_code,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['product-head-selection', listing?.product_id, selectedLocale, listing?.channel_code],
      });
      toast({ title: 'Head term reset', description: 'Head term will now be chosen automatically.' });
    },
    onError: (err: unknown) => {
      toast({
        title: 'Failed to reset head term',
        description: getApiErrorMessage(err),
        variant: 'destructive',
      });
    },
  });

  // Initialize selected axes from listing (resolved axes may omit `enabled`; treat as enabled)
  useEffect(() => {
    if (listing?.axes) {
      setSelectedAxes(
        listing.axes.filter((a) => a.enabled !== false).map((a) => a.attribute_id)
      );
    }
  }, [listing?.axes]);

  // Move variants mutation
  const moveVariantsMutation = useMutation({
    mutationFn: (variantIds: number[]) => moveVariantsToListing(listingId, variantIds),
    onSuccess: (data) => {
      toast({
        title: 'Variants Added',
        description: `${data.moved_count} variant(s) moved to this listing`,
      });
      queryClient.invalidateQueries({ queryKey: ['channel-listing', listingId] });
      queryClient.invalidateQueries({ queryKey: ['listing-differences', listingId] });
      setShowAddVariantsDialog(false);
      setSelectedVariantIds([]);
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to add variants',
        variant: 'destructive',
      });
    },
  });

  // Remove variants mutation
  const removeVariantsMutation = useMutation({
    mutationFn: (variantIds: number[]) => removeVariantsFromListing(listingId, variantIds),
    onSuccess: (data) => {
      toast({
        title: 'Variants Removed',
        description: `${data.removed_count} variant(s) removed from this listing`,
      });
      queryClient.invalidateQueries({ queryKey: ['channel-listing', listingId] });
      queryClient.invalidateQueries({ queryKey: ['listing-differences', listingId] });
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to remove variants',
        variant: 'destructive',
      });
    },
  });

  // Set axes mutation
  const setAxesMutation = useMutation({
    mutationFn: (attributeIds: number[]) =>
      setListingAxes(
        listingId,
        attributeIds.map((attrId, idx) => ({
          attribute_id: attrId,
          position: idx,
          enabled: true,
        }))
      ),
    onSuccess: () => {
      toast({
        title: 'Axes Updated',
        description: 'Variation axes have been saved',
      });
      queryClient.invalidateQueries({ queryKey: ['channel-listing', listingId] });
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to update axes',
        variant: 'destructive',
      });
    },
  });

  // Update listing mutation
  const updateMutation = useMutation({
    mutationFn: () => updateChannelListing(listingId, {
      name: editName,
      is_default: editIsDefault,
    }),
    onSuccess: () => {
      toast({
        title: 'Listing Updated',
        description: 'Listing details have been saved',
      });
      queryClient.invalidateQueries({ queryKey: ['channel-listing', listingId] });
      queryClient.invalidateQueries({ queryKey: ['channel-listings'] });
      setShowEditDialog(false);
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to update listing',
        variant: 'destructive',
      });
    },
  });
  
  // Generate titles mutation
  const generateTitlesMutation = useMutation({
    mutationFn: () => generateListingTitles(listingId, {
      locale_code: selectedLocale,
      template_id: selectedTemplate || undefined,
    }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['listing-generated-titles', listingId, selectedLocale] });
      setLastUntranslatedValues(data.untranslated_attribute_values ?? null);
      toast({
        title: 'Titles Generated',
        description: data.untranslated_attribute_values?.length
          ? `Generated for ${data.variant_count} variant(s). Some attribute values are not translated for ${selectedLocale} — add them in Translations to see them in the chosen language.`
          : `Generated titles for ${data.variant_count} variant(s)`,
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to generate titles',
        variant: 'destructive',
      });
    },
  });

  const createDefaultTemplateMutation = useMutation({
    mutationFn: () => createDefaultTemplateForListing(listingId, selectedLocale),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['listing-templates', listingId, selectedLocale] });
      setSelectedTemplate(data.template.id);
      toast({
        title: data.created ? 'Template Created' : 'Template Ready',
        description: data.created
          ? 'Default title template (Head term - Hook term) was created. You can now generate titles.'
          : 'An active template already exists for this locale.',
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to create template',
        variant: 'destructive',
      });
    },
  });

  const updateTitleMutation = useMutation({
    mutationFn: ({ variantId, title }: { variantId: number; title: string }) =>
      updateListingGeneratedTitle(listingId, variantId, selectedLocale!, title),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['listing-generated-titles', listingId, selectedLocale] });
      setEditingTitleVariantId(null);
      setEditingTitleValue('');
      toast({ title: 'Title updated', description: 'The generated title was saved.' });
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to update title',
        description: getApiErrorMessage(error),
        variant: 'destructive',
      });
    },
  });

  const translateMissingMutation = useMutation({
    mutationFn: ({ locale, attribute_ids }: { locale: string; attribute_ids: number[] }) =>
      createTranslationTask({
        scope: 'product_attribute_value',
        locale,
        target_ids: attribute_ids,
      }),
    onSuccess: (task) => {
      toast({
        title: 'Translation task started',
        description: `Task #${task.id} is processing. When it finishes, regenerate titles to use the new translations.`,
      });
      navigate(`/translations/${task.id}`);
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to start translation',
        description: getApiErrorMessage(error),
        variant: 'destructive',
      });
    },
  });

  const handleToggleAxis = (attributeId: number, checked: boolean) => {
    if (checked) {
      setSelectedAxes([...selectedAxes, attributeId]);
    } else {
      setSelectedAxes(selectedAxes.filter((id) => id !== attributeId));
    }
  };

  const handleOpenEditDialog = () => {
    if (listing) {
      setEditName(listing.name || '');
      setEditIsDefault(listing.is_default);
      setShowEditDialog(true);
    }
  };

  const handleSaveAxes = () => {
    setAxesMutation.mutate(selectedAxes);
  };

  const handleToggleVariantSelection = (variantId: number, checked: boolean) => {
    if (checked) {
      setSelectedVariantIds([...selectedVariantIds, variantId]);
    } else {
      setSelectedVariantIds(selectedVariantIds.filter((id) => id !== variantId));
    }
  };

  const availableVariantsRaw = availableVariantsData?.variants ?? [];
  const attributeCodes = availableVariantsData?.attribute_codes ?? [];

  // Search filter: match SKU, barcode, or any attribute value (case-insensitive)
  const availableVariants = (() => {
    const q = addVariantsSearch.trim().toLowerCase();
    if (!q) return availableVariantsRaw;
    return availableVariantsRaw.filter((v: AvailableVariantForListing) => {
      if ((v.sku ?? '').toLowerCase().includes(q)) return true;
      if ((v.barcode ?? '').toLowerCase().includes(q)) return true;
      return Object.values(v.attributes || {}).some(
        (val) => String(val).toLowerCase().includes(q)
      );
    });
  })();

  if (isLoading) {
    return (
      <div className="page-container flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error || !listing) {
    return (
      <div className="page-container">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Failed to load listing. It may have been deleted.
          </AlertDescription>
        </Alert>
        <Button variant="outline" onClick={() => navigate('/groups')} className="mt-4">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Listings
        </Button>
      </div>
    );
  }

  return (
    <>
      <div className="page-container">
        <PageHeader
          title={listing.name || `${listing.product_code} @ ${listing.channel_code}`}
          description={`Marketplace listing group for ${listing.channel_code}`}
          breadcrumbs={[
            { label: 'Dashboard', href: '/' },
            { label: 'Listing Groups', href: '/groups' },
            { label: listing.name || listing.product_code || `#${listing.id}` },
          ]}
          actions={
            <div className="flex gap-2">
              <Button variant="outline" onClick={handleOpenEditDialog}>
                <Pencil className="w-4 h-4 mr-2" />
                Edit
              </Button>
              <Button variant="outline" onClick={() => navigate('/groups')}>
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back
              </Button>
            </div>
          }
        />

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <div className="p-3 rounded-lg bg-blue-100 dark:bg-blue-900">
                  <Package className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Product family</p>
                  <p className="font-semibold">{listing.product_code}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <div className="p-3 rounded-lg bg-green-100 dark:bg-green-900">
                  <Store className="w-5 h-5 text-green-600 dark:text-green-400" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Channel</p>
                  <p className="font-semibold">
                    {listing.channel_code}
                    {listing.locale_code && ` (${listing.locale_code})`}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <div className="p-3 rounded-lg bg-purple-100 dark:bg-purple-900">
                  <Layers className="w-5 h-5 text-purple-600 dark:text-purple-400" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Variants</p>
                  <p className="font-semibold">{listing.variants.length} in listing</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="mb-4">
            <TabsTrigger value="variants">
              <Package className="w-4 h-4 mr-2" />
              Variants ({listing.variants.length})
            </TabsTrigger>
            <TabsTrigger value="axes">
              <Settings2 className="w-4 h-4 mr-2" />
              Variation Axes
            </TabsTrigger>
            <TabsTrigger value="titles">
              <Languages className="w-4 h-4 mr-2" />
              Generate Titles
            </TabsTrigger>
          </TabsList>

          {/* Variants Tab */}
          <TabsContent value="variants">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle>Variants in Listing</CardTitle>
                  <CardDescription>
                    These variants will be grouped together on {listing.channel_code}
                  </CardDescription>
                </div>
                <Button onClick={() => setShowAddVariantsDialog(true)}>
                  <Plus className="w-4 h-4 mr-2" />
                  Add Variants
                </Button>
              </CardHeader>
              <CardContent>
                {listing.variants.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <Package className="w-12 h-12 mx-auto mb-3 opacity-50" />
                    <p>No variants in this listing yet.</p>
                    <p className="text-sm">Add variants to group them for this marketplace.</p>
                  </div>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>SKU</TableHead>
                        <TableHead>Barcode</TableHead>
                        <TableHead>External ID</TableHead>
                        <TableHead>Sync Status</TableHead>
                        <TableHead></TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {listing.variants.map((variant) => (
                        <TableRow key={variant.id}>
                          <TableCell className="font-medium">
                            {variant.sku || `#${variant.id}`}
                          </TableCell>
                          <TableCell className="font-mono text-sm">
                            {variant.barcode || '—'}
                          </TableCell>
                          <TableCell className="text-sm text-muted-foreground">
                            {variant.external_id || '—'}
                          </TableCell>
                          <TableCell>
                            {variant.sync_status ? (
                              <Badge variant="outline">{variant.sync_status}</Badge>
                            ) : (
                              <Badge variant="secondary">Not synced</Badge>
                            )}
                          </TableCell>
                          <TableCell>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-destructive hover:text-destructive"
                              onClick={() => {
                                if (confirm(`Remove ${variant.sku || `#${variant.id}`} from listing?`)) {
                                  removeVariantsMutation.mutate([variant.id]);
                                }
                              }}
                            >
                              <X className="w-4 h-4" />
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Axes Tab */}
          <TabsContent value="axes">
            <Card>
              <CardHeader>
                <CardTitle>Variation Axes</CardTitle>
                <CardDescription>
                  Select which attributes define variations for this listing group (e.g. Color, Size).
                  When set here, they override channel and product-family defaults for this listing.
                </CardDescription>
              </CardHeader>
              <CardContent>
                {differencesLoading ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
                    <span className="ml-2 text-sm text-muted-foreground">Analyzing variants...</span>
                  </div>
                ) : differences?.message ? (
                  <Alert>
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>{differences.message}</AlertDescription>
                  </Alert>
                ) : (
                  <div className="space-y-6">
                    {/* Suggested Axes */}
                    {differences?.suggested_axes && differences.suggested_axes.length > 0 && (
                      <Alert className="bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800">
                        <TrendingUp className="h-4 w-4 text-blue-600" />
                        <AlertDescription>
                          <strong>Suggested axes:</strong>{' '}
                          {differences.suggested_axes.map((a) => a.attribute_code).join(', ')}
                        </AlertDescription>
                      </Alert>
                    )}

                    {/* Differences List */}
                    {differences?.differences && differences.differences.length > 0 ? (
                      <div className="space-y-3">
                        <Label>Select Variation Axes</Label>
                        {differences.differences.map((diff) => (
                          <div
                            key={diff.attribute_id}
                            className="flex items-start gap-3 p-3 rounded-lg border bg-card"
                          >
                            <Checkbox
                              id={`axis-${diff.attribute_id}`}
                              checked={selectedAxes.includes(diff.attribute_id)}
                              onCheckedChange={(checked) =>
                                handleToggleAxis(diff.attribute_id, !!checked)
                              }
                              disabled={!diff.is_candidate_axis}
                            />
                            <div className="flex-1 space-y-1">
                              <div className="flex items-center gap-2">
                                <Label
                                  htmlFor={`axis-${diff.attribute_id}`}
                                  className="font-medium cursor-pointer"
                                >
                                  {diff.attribute_code}
                                </Label>
                                {diff.is_candidate_axis && (
                                  <Badge variant="default" className="text-xs">
                                    <TrendingUp className="w-3 h-3 mr-1" />
                                    Recommended
                                  </Badge>
                                )}
                                <Badge variant="outline" className="text-xs">
                                  {diff.unique_values_count} value
                                  {diff.unique_values_count !== 1 ? 's' : ''}
                                </Badge>
                              </div>
                              <p className="text-xs text-muted-foreground">
                                Values: {diff.unique_values.slice(0, 5).join(', ')}
                                {diff.unique_values.length > 5 &&
                                  ` +${diff.unique_values.length - 5} more`}
                              </p>
                              {diff.has_missing_values && (
                                <p className="text-xs text-orange-600">
                                  ⚠️ Some variants are missing this value
                                </p>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <Alert>
                        <AlertCircle className="h-4 w-4" />
                        <AlertDescription>
                          No differences found. Add at least 2 variants to detect variation axes.
                        </AlertDescription>
                      </Alert>
                    )}

                    {/* Common Attributes */}
                    {differences?.common_attributes && differences.common_attributes.length > 0 && (
                      <div className="space-y-2">
                        <Label>Common Attributes (same for all variants)</Label>
                        <div className="flex flex-wrap gap-2">
                          {differences.common_attributes.map((attr) => (
                            <Badge key={attr.attribute_id} variant="secondary" className="text-xs">
                              {attr.attribute_code}: {attr.common_value}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Save Button */}
                    {differences?.differences && differences.differences.length > 0 && (
                      <div className="flex justify-end pt-4 border-t">
                        <Button
                          onClick={handleSaveAxes}
                          disabled={setAxesMutation.isPending}
                        >
                          {setAxesMutation.isPending && (
                            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                          )}
                          <CheckCircle2 className="w-4 h-4 mr-2" />
                          Save Axes
                        </Button>
                      </div>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Titles Tab */}
          <TabsContent value="titles">
            <Card>
              <CardHeader>
                <CardTitle>Generate Titles for Listing</CardTitle>
                <CardDescription>
                  Generate optimized titles for all {listing.variants.length} variant(s) in this listing using AI-powered templates.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <Alert className="bg-muted/50 border-muted-foreground/20">
                  <TrendingUp className="h-4 w-4" />
                  <AlertDescription>
                    <strong>Workflow:</strong>{' '}
                    <span className="text-muted-foreground">1) Save head & hook terms in </span>
                    <Link to="/keywords/saved-terms" className="font-medium text-primary underline underline-offset-2">
                      Keywords → Saved terms
                    </Link>
                    <span className="text-muted-foreground">. 2) Build template: create or select a template, then drag to reorder parts and see accepted head/hook terms below. 3) Select the template and click Generate.</span>
                  </AlertDescription>
                </Alert>
                <Alert className="border-blue-200 bg-blue-50/50 dark:bg-blue-950/20 dark:border-blue-800">
                  <AlertDescription>
                    <strong>How titles get their language:</strong> The template only defines <em>which</em> attributes appear in the title (e.g. form, colour, size). When you generate titles, the <strong>Target Language</strong> below decides the language: we use the <strong>translated</strong> value for each attribute in that language. If you see words in the wrong language, add (or backfill) translations for that language in{' '}
                    <Link to="/translations" className="font-medium text-primary underline underline-offset-2">
                      Translations
                    </Link>
                    , then regenerate.
                  </AlertDescription>
                </Alert>
                {listing.variants.length === 0 ? (
                  <Alert>
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>
                      No variants in this listing. Add variants first before generating titles.
                    </AlertDescription>
                  </Alert>
                ) : (
                  <>
                    {/* Locale Selection */}
                    <div className="space-y-2">
                      <Label htmlFor="locale-select">Target Language</Label>
                      <p className="text-xs text-muted-foreground">
                        Attribute values in generated titles will be shown in this language (using translations from Translations).
                      </p>
                      <Select value={selectedLocale} onValueChange={setSelectedLocale}>
                        <SelectTrigger id="locale-select">
                          <SelectValue placeholder="Select language..." />
                        </SelectTrigger>
                        <SelectContent>
                          {locales?.results?.map((loc) => (
                            <SelectItem key={loc.code} value={loc.code}>
                              {loc.name || loc.code} ({loc.code})
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    {/* Build template: drag-and-drop parts + accepted head/hook terms */}
                    {selectedLocale && (
                      <Card className="border-dashed border-2 border-muted">
                        <CardHeader>
                          <CardTitle className="text-base flex items-center gap-2">
                            <Link2 className="w-4 h-4 text-muted-foreground" />
                            Build template
                          </CardTitle>
                          <CardDescription>
                            Define the order of title parts: drag to reorder. Titles are built from the accepted head and hook terms below.
                          </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                          {selectedTemplate ? (
                            <>
                              {templatePartsLoading ? (
                                <div className="flex items-center gap-2 py-4 text-muted-foreground text-sm">
                                  <Loader2 className="w-4 h-4 animate-spin" />
                                  Loading parts…
                                </div>
                              ) : orderedParts.length > 0 ? (
                                <>
                                  <div className="space-y-1">
                                    <Label className="text-xs text-muted-foreground">Template parts (drag to reorder)</Label>
                                    <ul className="space-y-1 rounded-md border bg-muted/30 p-2">
                                      {orderedParts.map((part, index) => (
                                        <li
                                          key={part.id}
                                          draggable
                                          onDragStart={() => handlePartDragStart(index)}
                                          onDragEnd={handlePartDragEnd}
                                          onDragOver={handlePartDragOver}
                                          onDrop={(e) => handlePartDrop(e, index)}
                                          className={`flex items-center gap-2 rounded border bg-background px-3 py-2 text-sm ${draggedPartIndex === index ? 'opacity-50' : ''}`}
                                        >
                                          <GripVertical className="w-4 h-4 shrink-0 text-muted-foreground cursor-grab active:cursor-grabbing" />
                                          <span className="text-muted-foreground w-28 shrink-0">
                                            {TEMPLATE_PART_TYPES[part.part_type as keyof typeof TEMPLATE_PART_TYPES] ?? part.part_type}
                                          </span>
                                          {part.part_type === 'literal' && part.literal_text != null && (
                                            <span className="text-muted-foreground truncate max-w-[200px]">&quot;{part.literal_text}&quot;</span>
                                          )}
                                        </li>
                                      ))}
                                    </ul>
                                  </div>
                                  <div className="flex flex-wrap items-center gap-2">
                                    <Button
                                      size="sm"
                                      variant="secondary"
                                      onClick={() => saveTemplateOrderMutation.mutate()}
                                      disabled={saveTemplateOrderMutation.isPending}
                                    >
                                      {saveTemplateOrderMutation.isPending && (
                                        <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />
                                      )}
                                      Save order
                                    </Button>
                                    <Link
                                      to={`/templates/${selectedTemplate}/edit`}
                                      className="text-sm text-primary underline underline-offset-2 inline-flex items-center gap-1"
                                    >
                                      <Pencil className="w-3.5 h-3.5" />
                                      Edit full template (add/remove parts)
                                    </Link>
                                  </div>
                                </>
                              ) : (
                                <p className="text-sm text-muted-foreground py-2">No parts in this template. Edit it to add head term, hook term, literals, or attributes.</p>
                              )}
                            </>
                          ) : (
                            <p className="text-sm text-muted-foreground py-2">
                              Select a template below (or create one) to build or reorder its parts here.
                            </p>
                          )}

                          {/* Accepted head terms (this product type) */}
                          {savedTermsData?.head_terms_by_product_type != null && listing?.product_type_id != null && (() => {
                            const headTerms = savedTermsData.head_terms_by_product_type
                              .filter((g) => g.product_type_id === listing.product_type_id)
                              .flatMap((g) => g.terms);
                            const currentHeadText = headSelectionData?.head_text || null;
                            return (
                              <div className="space-y-2 pt-2 border-t">
                                <div className="space-y-1.5">
                                  <Label className="text-xs font-medium flex items-center gap-1.5">
                                    <Type className="w-3.5 h-3.5 text-muted-foreground" />
                                    Accepted head terms
                                  </Label>
                                  <p className="text-xs text-muted-foreground">
                                    Product-type terms used at the start of the title (for this locale/channel).
                                  </p>
                                  <div className="flex flex-wrap gap-1.5">
                                    {headTerms.length === 0 ? (
                                      <span className="text-xs text-muted-foreground">None saved. Add head terms in Keywords → Saved terms.</span>
                                    ) : (
                                      headTerms.map((t, i) => (
                                        <Badge key={i} variant="secondary" className="text-xs font-normal">
                                          {t.term}
                                        </Badge>
                                      ))
                                    )}
                                  </div>
                                </div>

                                <div className="space-y-1.5">
                                  <Label className="text-xs font-medium">Choose head term for this listing</Label>
                                  {headTerms.length === 0 ? (
                                    <p className="text-xs text-muted-foreground">
                                      No saved head terms yet. Titles will use the automatic head-term logic.
                                    </p>
                                  ) : (
                                    <Select
                                      value={currentHeadText || '__auto__'}
                                      onValueChange={(val) => {
                                        if (val === '__auto__') {
                                          clearHeadSelectionMutation.mutate();
                                          return;
                                        }
                                        setHeadSelectionMutation.mutate({
                                          head_text: val,
                                        });
                                      }}
                                      disabled={
                                        setHeadSelectionMutation.isPending || clearHeadSelectionMutation.isPending
                                      }
                                    >
                                      <SelectTrigger className="w-[220px] h-8 text-xs">
                                        <SelectValue placeholder="Auto (use best head term)" />
                                      </SelectTrigger>
                                      <SelectContent>
                                        <SelectItem value="__auto__">
                                          Auto (use best head term)
                                        </SelectItem>
                                        {headTerms.map((t, i) => (
                                          <SelectItem key={`${t.term}-${i}`} value={t.term}>
                                            {t.term}
                                          </SelectItem>
                                        ))}
                                      </SelectContent>
                                    </Select>
                                  )}
                                  <p className="text-xs text-muted-foreground">
                                    This choice affects only titles for this product / locale / marketplace. Leave on Auto to let the system choose from saved terms.
                                  </p>
                                </div>
                              </div>
                            );
                          })()}

                          {/* Accepted hook terms (this product) */}
                          {savedTermsData?.hook_terms_by_product != null && listing?.product_id != null && (() => {
                            const hookTerms = savedTermsData.hook_terms_by_product
                              .filter((g) => g.product_id === listing.product_id)
                              .flatMap((g) => g.terms);
                            return (
                              <div className="space-y-1.5">
                                <Label className="text-xs font-medium flex items-center gap-1.5">
                                  <Link2 className="w-3.5 h-3.5 text-muted-foreground" />
                                  Accepted hook terms
                                </Label>
                                <p className="text-xs text-muted-foreground">
                                  Product-specific terms (e.g. colour, material) used after the head term.
                                </p>
                                <div className="flex flex-wrap gap-1.5">
                                  {hookTerms.length === 0 ? (
                                    <span className="text-xs text-muted-foreground">None saved. Add hook terms in Keywords → Saved terms or on the product page.</span>
                                  ) : (
                                    hookTerms.map((t, i) => (
                                      <Badge key={i} variant="outline" className="text-xs font-normal">
                                        {t.term}
                                      </Badge>
                                    ))
                                  )}
                                </div>
                              </div>
                            );
                          })()}
                        </CardContent>
                      </Card>
                    )}

                    {/* Template Selection */}
                    {selectedLocale && (
                      <div className="space-y-2">
                        <Label htmlFor="template-select">Title Template</Label>
                        {templatesLoading ? (
                          <div className="flex items-center gap-2 py-2">
                            <Loader2 className="w-4 h-4 animate-spin" />
                            <span className="text-sm text-muted-foreground">Loading templates...</span>
                          </div>
                        ) : templatesData?.templates && templatesData.templates.length > 0 ? (
                          <>
                            <Select 
                              value={selectedTemplate?.toString() || ''} 
                              onValueChange={(val) => setSelectedTemplate(val ? parseInt(val) : null)}
                            >
                              <SelectTrigger id="template-select">
                                <SelectValue placeholder="Select template..." />
                              </SelectTrigger>
                              <SelectContent>
                                {templatesData.templates.map((template) => (
                                  <SelectItem key={template.id} value={template.id.toString()}>
                                    Template v{template.version} - {template.part_count} parts ({template.locale})
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                            <p className="text-xs text-muted-foreground">
                              {selectedTemplate 
                                ? `Selected template will be used for all variants`
                                : 'Select a template or leave blank for auto-selection'}
                            </p>
                          </>
                        ) : (
                          <div className="space-y-3">
                            <Alert>
                              <AlertCircle className="h-4 w-4" />
                              <AlertDescription>
                                No active templates found for {listing.product_code} on {listing.channel_code} in {selectedLocale}.
                              </AlertDescription>
                            </Alert>
                            <div className="flex flex-wrap gap-2">
                              <Button
                                variant="secondary"
                                onClick={() => createDefaultTemplateMutation.mutate()}
                                disabled={!selectedLocale || createDefaultTemplateMutation.isPending}
                              >
                                {createDefaultTemplateMutation.isPending ? (
                                  <>
                                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                    Creating...
                                  </>
                                ) : (
                                  <>Create default template (Head term - Hook term)</>
                                )}
                              </Button>
                              <Button variant="outline" asChild>
                                <Link
                                  to={{
                                    pathname: '/templates/new',
                                    search: listing?.product_type_id && listing?.channel_code && selectedLocale
                                      ? `?product_type_id=${listing.product_type_id}&channel_code=${encodeURIComponent(listing.channel_code)}&locale_code=${encodeURIComponent(selectedLocale)}`
                                      : undefined,
                                  }}
                                >
                                  <Link2 className="w-4 h-4 mr-2" />
                                  Create template manually
                                </Link>
                              </Button>
                            </div>
                            <p className="text-xs text-muted-foreground">
                              Create default template (uses saved head/hook terms) or build a custom template in the wizard.
                            </p>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Generate Button */}
                    <div className="flex justify-end pt-4 border-t">
                      <Button
                        onClick={() => generateTitlesMutation.mutate()}
                        disabled={!selectedLocale || generateTitlesMutation.isPending}
                      >
                        {generateTitlesMutation.isPending ? (
                          <>
                            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                            Generating...
                          </>
                        ) : (
                          <>
                            <CheckCircle2 className="w-4 h-4 mr-2" />
                            Generate Titles for {listing.variants.length} Variant{listing.variants.length !== 1 ? 's' : ''}
                          </>
                        )}
                      </Button>
                    </div>
                  </>
                )}
              </CardContent>
            </Card>

            {/* Generated titles list (when locale selected) */}
            {selectedLocale && listing?.variants?.length > 0 && (
              <Card className="mt-6">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <FileText className="w-5 h-5" />
                    Generated titles
                  </CardTitle>
                  <CardDescription>
                    Latest generated title per variant for this listing in {selectedLocale}. Generate above to create or refresh.
                  </CardDescription>
                  <p className="text-xs text-muted-foreground mt-1">
                    Titles use the <strong>translated</strong> attribute values for <strong>{selectedLocale}</strong> (the target language you chose above). If some words appear in the wrong language, add translations for {selectedLocale} in{' '}
                    <Link to="/translations" className="underline font-medium text-foreground hover:no-underline">
                      Translations
                    </Link>
                    {' '}(Attribute values &amp; Product attribute values), then regenerate. If titles show only head term plus a short code, add a <strong>hook term</strong> and <strong>variation axes</strong> to your template.
                  </p>
                  {lastUntranslatedValues && lastUntranslatedValues.length > 0 && (
                    <Alert className="mt-3 border-amber-200 bg-amber-50/80 dark:bg-amber-950/30 dark:border-amber-800">
                      <AlertDescription>
                        <strong>Not translated for {selectedLocale}:</strong> The following axis/attribute values appear in titles in their original form. To show them in {selectedLocale}, add translations in{' '}
                        <Link to="/translations" className="font-medium text-primary underline underline-offset-2">
                          Translations
                        </Link>
                        {' '}(Product attribute values or Attribute values for this locale), then regenerate.
                        <ul className="mt-2 text-xs font-mono list-disc list-inside">
                          {lastUntranslatedValues.slice(0, 12).map((u, i) => (
                            <li key={i}>{u.attr_code}: {u.code}</li>
                          ))}
                          {lastUntranslatedValues.length > 12 && <li>…and {lastUntranslatedValues.length - 12} more</li>}
                        </ul>
                        <div className="mt-3 flex flex-wrap items-center gap-2">
                          <Button
                            size="sm"
                            variant="secondary"
                            disabled={translateMissingMutation.isPending || !lastUntranslatedValues.some((u) => u.attribute_id)}
                            onClick={() => {
                              const ids = [...new Set(lastUntranslatedValues!.map((u) => u.attribute_id).filter((id): id is number => id != null))];
                              if (ids.length && selectedLocale) {
                                translateMissingMutation.mutate({ locale: selectedLocale, attribute_ids: ids });
                              }
                            }}
                          >
                            {translateMissingMutation.isPending ? (
                              <>
                                <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />
                                Starting…
                              </>
                            ) : (
                              'Translate missing values'
                            )}
                          </Button>
                          <span className="text-xs text-muted-foreground">
                            Starts a translation task for these attributes in {selectedLocale}, then regenerate titles.
                          </span>
                        </div>
                      </AlertDescription>
                    </Alert>
                  )}
                </CardHeader>
                <CardContent>
                  {productTypeAttributes && productTypeAttributes.length > 0 && (
                    <div className="mb-4 rounded-md border bg-muted/40 p-3">
                      <p className="text-xs font-medium text-muted-foreground mb-2">
                        Attributes for this product type · which ones are translatable?
                      </p>
                      <div className="rounded-md border bg-background overflow-hidden">
                        <table className="w-full text-xs">
                          <thead>
                            <tr className="bg-muted/50 border-b">
                              <th className="text-left py-1.5 px-3 font-medium">Code</th>
                              <th className="text-left py-1.5 px-3 font-medium">Type</th>
                              <th className="text-left py-1.5 px-3 font-medium">Translatable</th>
                            </tr>
                          </thead>
                          <tbody>
                            {productTypeAttributes.map((pta) => (
                              <tr key={pta.id} className="border-b last:border-0">
                                <td className="py-1.5 px-3 font-mono">{pta.attribute.code}</td>
                                <td className="py-1.5 px-3 text-muted-foreground">{pta.attribute.data_type}</td>
                                <td className="py-1.5 px-3">
                                  {pta.attribute.is_value_translatable || pta.attribute.data_type === 'enum' ? (
                                    <span className="inline-flex items-center rounded-full px-2 py-0.5 text-[11px] bg-emerald-50 text-emerald-700">
                                      Yes (titles can use translations)
                                    </span>
                                  ) : (
                                    <span className="inline-flex items-center rounded-full px-2 py-0.5 text-[11px] bg-muted text-muted-foreground">
                                      No (used as-is)
                                    </span>
                                  )}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                      <p className="mt-2 text-[11px] text-muted-foreground">
                        Enum attributes use <strong>Attribute value translations</strong>. Text/number attributes with “Translatable = Yes”
                        use <strong>Product attribute value translations</strong> from Translations → Product Attributes.
                      </p>
                    </div>
                  )}
                  {generatedTitlesLoading ? (
                    <div className="flex items-center gap-2 py-8 justify-center text-muted-foreground">
                      <Loader2 className="w-5 h-5 animate-spin" />
                      <span>Loading titles…</span>
                    </div>
                  ) : !generatedTitlesData?.results?.length ? (
                    <div className="flex flex-col items-center gap-2 py-8 text-center text-muted-foreground">
                      <FileText className="w-10 h-10 opacity-50" />
                      <p className="text-sm">No generated titles yet for this locale.</p>
                      <p className="text-xs">Select a template above and click Generate to create titles.</p>
                    </div>
                  ) : (
                    <div className="rounded-md border">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead className="w-24">Variant ID</TableHead>
                            <TableHead className="w-32">SKU</TableHead>
                            <TableHead>Title</TableHead>
                            <TableHead className="w-40 text-muted-foreground">Generated</TableHead>
                            <TableHead className="w-28 text-right">Details</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {generatedTitlesData.results.map((row) => (
                            <TableRow key={row.variant_id}>
                              <TableCell className="font-mono text-sm">{row.variant_id}</TableCell>
                              <TableCell className="font-mono text-sm">{row.sku || '—'}</TableCell>
                              <TableCell className="max-w-md font-medium">
                                {editingTitleVariantId === row.variant_id ? (
                                  <div className="flex flex-col gap-2">
                                    <Input
                                      value={editingTitleValue}
                                      onChange={(e) => setEditingTitleValue(e.target.value)}
                                      className="text-sm"
                                      placeholder="Title"
                                      autoFocus
                                    />
                                    <div className="flex gap-1">
                                      <Button
                                        size="sm"
                                        className="h-7 text-xs"
                                        disabled={updateTitleMutation.isPending || !editingTitleValue.trim()}
                                        onClick={() =>
                                          updateTitleMutation.mutate({
                                            variantId: row.variant_id,
                                            title: editingTitleValue.trim(),
                                          })
                                        }
                                      >
                                        {updateTitleMutation.isPending ? (
                                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                        ) : (
                                          'Save'
                                        )}
                                      </Button>
                                      <Button
                                        size="sm"
                                        variant="outline"
                                        className="h-7 text-xs"
                                        disabled={updateTitleMutation.isPending}
                                        onClick={() => {
                                          setEditingTitleVariantId(null);
                                          setEditingTitleValue('');
                                        }}
                                      >
                                        Cancel
                                      </Button>
                                    </div>
                                  </div>
                                ) : (
                                  <span className="break-words">{row.title || '—'}</span>
                                )}
                              </TableCell>
                              <TableCell className="text-muted-foreground text-sm">
                                {row.generated_at ? (
                                  <span className="inline-flex items-center gap-1">
                                    <Clock className="w-3.5 h-3.5 shrink-0" />
                                    {formatDateTime(row.generated_at)}
                                  </span>
                                ) : (
                                  '—'
                                )}
                              </TableCell>
                              <TableCell className="text-right">
                                {editingTitleVariantId === row.variant_id ? null : (
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    className="h-7 px-2 text-xs mr-1"
                                    onClick={() => {
                                      setEditingTitleVariantId(row.variant_id);
                                      setEditingTitleValue(row.title || '');
                                    }}
                                  >
                                    Edit
                                  </Button>
                                )}
                                <Button
                                  variant="outline"
                                  size="sm"
                                  className="h-7 px-2 text-xs"
                                  onClick={() => setDetailsVariantId(row.variant_id)}
                                >
                                  View details
                                </Button>
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}
          </TabsContent>
        </Tabs>
      </div>

      {/* Add Variants Dialog */}
      <Dialog
        open={showAddVariantsDialog}
        onOpenChange={(open) => {
          setShowAddVariantsDialog(open);
          if (!open) {
            setAddVariantsSearch('');
            setSelectedVariantIds([]);
          }
        }}
      >
        <DialogContent className="max-w-4xl max-h-[90vh] flex flex-col">
          <DialogHeader>
            <DialogTitle>Add Variants to Listing</DialogTitle>
            <DialogDescription>
              {availableVariantsData?.product_code ? (
                <>
                  Select variants from product &quot;{availableVariantsData.product_code}&quot; to add to this listing.
                  Variants can only belong to one listing per channel.
                </>
              ) : (
                <>
                  Select variants to add to this listing. Variants can only belong to one listing per channel.
                </>
              )}
            </DialogDescription>
          </DialogHeader>

          {availableVariantsRaw.length > 0 && (
            <div className="flex items-center gap-2 px-1">
              <Search className="h-4 w-4 text-muted-foreground shrink-0" />
              <Input
                placeholder="Search by SKU, barcode, or attribute value..."
                value={addVariantsSearch}
                onChange={(e) => setAddVariantsSearch(e.target.value)}
                className="max-w-sm"
              />
            </div>
          )}

          <div className="max-h-96 overflow-y-auto border rounded-md">
            {variantsLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 animate-spin" />
              </div>
            ) : availableVariantsRaw.length === 0 ? (
              <Alert className="m-4">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  {listing?.product_id
                    ? 'No more variants available. All variants from this product are already in listings.'
                    : 'This listing has no product yet. Add variants from a product page first, or create a new listing with a product.'}
                </AlertDescription>
              </Alert>
            ) : availableVariants.length === 0 ? (
              <Alert className="m-4">
                <AlertDescription>
                  No variants match the search. Try a different term.
                </AlertDescription>
              </Alert>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-12"></TableHead>
                    <TableHead>SKU</TableHead>
                    <TableHead>Barcode</TableHead>
                    {attributeCodes.map((code) => (
                      <TableHead key={code} className="capitalize">
                        {code.replace(/_/g, ' ')}
                      </TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {availableVariants.map((variant: AvailableVariantForListing) => (
                    <TableRow key={variant.id}>
                      <TableCell>
                        <Checkbox
                          checked={selectedVariantIds.includes(variant.id)}
                          onCheckedChange={(checked) =>
                            handleToggleVariantSelection(variant.id, !!checked)
                          }
                        />
                      </TableCell>
                      <TableCell className="font-medium">
                        {variant.sku ?? '—'}
                      </TableCell>
                      <TableCell className="font-mono text-sm">
                        {variant.barcode ?? '—'}
                      </TableCell>
                      {attributeCodes.map((code) => (
                        <TableCell key={code} className="text-muted-foreground text-sm">
                          {variant.attributes?.[code] ?? '—'}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAddVariantsDialog(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => moveVariantsMutation.mutate(selectedVariantIds)}
              disabled={selectedVariantIds.length === 0 || moveVariantsMutation.isPending}
            >
              {moveVariantsMutation.isPending && (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              )}
              Add {selectedVariantIds.length} Variant{selectedVariantIds.length !== 1 ? 's' : ''}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Listing Dialog */}
      <Dialog open={showEditDialog} onOpenChange={setShowEditDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Listing Group</DialogTitle>
            <DialogDescription>
              Update the listing name and settings.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="edit-name">Listing Name</Label>
              <Input
                id="edit-name"
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                placeholder="e.g., Color variants only"
              />
              <p className="text-xs text-muted-foreground">
                Optional label to distinguish multiple listings per product.
              </p>
            </div>

            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="edit-default">Default Listing</Label>
                <p className="text-xs text-muted-foreground">
                  Mark as the default listing for this product + channel
                </p>
              </div>
              <Switch
                id="edit-default"
                checked={editIsDefault}
                onCheckedChange={setEditIsDefault}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowEditDialog(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => updateMutation.mutate()}
              disabled={updateMutation.isPending}
            >
              {updateMutation.isPending && (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              )}
              Save Changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Variant attribute details dialog (Titles tab) */}
      <Dialog open={detailsVariantId != null} onOpenChange={(open) => !open && setDetailsVariantId(open ? detailsVariantId : null)}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle>Variant attributes and translations</DialogTitle>
            <DialogDescription>
              View the attributes and values for this variant in the current locale. Enum attributes use{' '}
              <strong>Attribute value translations</strong>; text/number attributes marked as translatable use{' '}
              <strong>Product attribute value translations</strong> from Translations → Product Attributes.
            </DialogDescription>
          </DialogHeader>
          {detailsVariantId != null && (
            <VariantDetailsBody
              variantId={detailsVariantId}
              localeCode={selectedLocale}
              channelCode={listing?.channel_code || undefined}
              productTypeAttributes={productTypeAttributes || []}
            />
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}

interface VariantDetailsBodyProps {
  variantId: number;
  localeCode: string;
  channelCode?: string;
  productTypeAttributes: ProductTypeAttribute[];
}

function VariantDetailsBody({
  variantId,
  localeCode,
  channelCode,
  productTypeAttributes,
}: VariantDetailsBodyProps) {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const [newAttributeId, setNewAttributeId] = useState<number | undefined>(undefined);
  const [newEnumValueId, setNewEnumValueId] = useState<number | undefined>(undefined);
  const [newTextValue, setNewTextValue] = useState('');
  const [newNumberValue, setNewNumberValue] = useState<string>('');
  const [newBoolValue, setNewBoolValue] = useState(false);

  const [editingPavId, setEditingPavId] = useState<number | null>(null);
  const [editingEnumValueId, setEditingEnumValueId] = useState<number | undefined>(undefined);
  const [editingTextValue, setEditingTextValue] = useState('');
  const [editingNumberValue, setEditingNumberValue] = useState<string>('');
  const [editingBoolValue, setEditingBoolValue] = useState(false);

  const { data, isLoading, error } = useQuery<VariantAttributeDetailsResponse>({
    queryKey: ['variant-attribute-details', variantId, localeCode, channelCode],
    queryFn: () =>
      getVariantAttributeDetails(variantId, {
        locale_code: localeCode,
        channel_code: channelCode,
      }),
    enabled: !!localeCode && !!variantId,
  });

  const attrs = data?.attributes ?? [];
  const variantLevelAttributes = productTypeAttributes.filter((pta) => pta.variant_level);
  const usedAttributeIds = new Set(attrs.map((a) => a.attribute_id));
  const availableAttributes = variantLevelAttributes.filter((pta) => !usedAttributeIds.has(pta.attribute.id));

  const addMutation = useMutation({
    mutationFn: async () => {
      if (!newAttributeId) return;
      const pta = productTypeAttributes.find((p) => p.attribute.id === newAttributeId);
      if (!pta) return;

      const payload: VariantAttributeValueWrite = { attribute_id: newAttributeId };
      if (pta.attribute.data_type === 'enum') {
        if (!newEnumValueId) return;
        payload.attribute_value_id = newEnumValueId;
      } else if (pta.attribute.data_type === 'text') {
        if (!newTextValue.trim()) return;
        payload.value_text = newTextValue;
      } else if (pta.attribute.data_type === 'number') {
        if (!newNumberValue.trim()) return;
        const num = Number(newNumberValue);
        if (Number.isNaN(num)) return;
        payload.value_number = num;
      } else if (pta.attribute.data_type === 'bool') {
        payload.value_bool = newBoolValue;
      }

      await createVariantAttributeValue(variantId, payload);
    },
    onSuccess: () => {
      resetNewForm();
      invalidateDetails();
      toast({ title: 'Attribute value saved' });
    },
    onError: (err: unknown) => {
      toast({
        title: 'Failed to save attribute value',
        description: getApiErrorMessage(err),
        variant: 'destructive',
      });
    },
  });

  if (!localeCode) {
    return <p className="text-sm text-muted-foreground">Select a locale above to see variant details.</p>;
  }

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 py-6 text-muted-foreground">
        <Loader2 className="w-4 h-4 animate-spin" />
        <span className="text-sm">Loading attributes…</span>
      </div>
    );
  }

  if (error) {
    return (
      <p className="text-sm text-destructive">
        Failed to load attributes for variant {variantId}.
      </p>
    );
  }

  const resetNewForm = () => {
    setNewAttributeId(undefined);
    setNewEnumValueId(undefined);
    setNewTextValue('');
    setNewNumberValue('');
    setNewBoolValue(false);
  };

  const invalidateDetails = () => {
    queryClient.invalidateQueries({ queryKey: ['variant-attribute-details', variantId, localeCode, channelCode] });
  };

  const startEdit = (item: VariantAttributeDetailsItem) => {
    setEditingPavId(item.product_attribute_value_id);
    if (item.data_type === 'enum') {
      const pta = productTypeAttributes.find((p) => p.attribute.id === item.attribute_id);
      const current = pta?.attribute.values?.find((v) => v.code === item.raw_value);
      setEditingEnumValueId(current?.id);
      setEditingTextValue('');
      setEditingNumberValue('');
    } else if (item.data_type === 'text') {
      setEditingTextValue(item.raw_value ?? '');
      setEditingEnumValueId(undefined);
      setEditingNumberValue('');
    } else if (item.data_type === 'number') {
      setEditingNumberValue(item.raw_value ?? '');
      setEditingEnumValueId(undefined);
      setEditingTextValue('');
    } else if (item.data_type === 'bool') {
      setEditingBoolValue((item.raw_value ?? '').toLowerCase() === 'true');
      setEditingEnumValueId(undefined);
      setEditingTextValue('');
      setEditingNumberValue('');
    }
  };

  const cancelEdit = () => {
    setEditingPavId(null);
    setEditingEnumValueId(undefined);
    setEditingTextValue('');
    setEditingNumberValue('');
  };

  const saveEdit = async (item: VariantAttributeDetailsItem) => {
    if (!editingPavId) return;
    const pta = productTypeAttributes.find((p) => p.attribute.id === item.attribute_id);
    if (!pta) return;

    const payload: VariantAttributeValueWrite = {};
    if (item.data_type === 'enum') {
      if (!editingEnumValueId) return;
      payload.attribute_value_id = editingEnumValueId;
    } else if (item.data_type === 'text') {
      if (!editingTextValue.trim()) return;
      payload.value_text = editingTextValue;
    } else if (item.data_type === 'number') {
      if (!editingNumberValue.trim()) return;
      const num = Number(editingNumberValue);
      if (Number.isNaN(num)) return;
      payload.value_number = num;
    } else if (item.data_type === 'bool') {
      payload.value_bool = editingBoolValue;
    }

    try {
      await updateVariantAttributeValue(variantId, editingPavId, payload);
      cancelEdit();
      invalidateDetails();
      toast({ title: 'Attribute value updated' });
    } catch (err) {
      toast({
        title: 'Failed to update attribute value',
        description: getApiErrorMessage(err),
        variant: 'destructive',
      });
    }
  };

  const handleDelete = async (item: VariantAttributeDetailsItem) => {
    try {
      await deleteVariantAttributeValue(variantId, item.product_attribute_value_id);
      invalidateDetails();
      toast({ title: 'Attribute value deleted' });
    } catch (err) {
      toast({
        title: 'Failed to delete attribute value',
        description: getApiErrorMessage(err),
        variant: 'destructive',
      });
    }
  };

  const isAddDisabled = (() => {
    if (!newAttributeId) return true;
    const pta = productTypeAttributes.find((p) => p.attribute.id === newAttributeId);
    if (!pta) return true;
    if (pta.attribute.data_type === 'enum') {
      return !newEnumValueId;
    }
    if (pta.attribute.data_type === 'text') {
      return !newTextValue.trim();
    }
    if (pta.attribute.data_type === 'number') {
      if (!newNumberValue.trim()) return true;
      return Number.isNaN(Number(newNumberValue));
    }
    return false;
  })();

  return (
    <div className="mt-2 space-y-3">
      <div className="space-y-2">
        <div className="flex items-end gap-2">
          <div className="flex-1">
            <Label className="text-xs mb-1">Add attribute</Label>
            <Select
              value={newAttributeId ? String(newAttributeId) : ''}
              onValueChange={(val) => {
                const id = Number(val);
                setNewAttributeId(id);
                setNewEnumValueId(undefined);
                setNewTextValue('');
                setNewNumberValue('');
                setNewBoolValue(false);
              }}
            >
              <SelectTrigger className="h-8 text-xs">
                <SelectValue placeholder={availableAttributes.length ? 'Choose attribute' : 'No more attributes'} />
              </SelectTrigger>
              <SelectContent>
                {availableAttributes.map((pta) => (
                  <SelectItem key={pta.id} value={String(pta.attribute.id)}>
                    {pta.attribute.code}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {newAttributeId && (
            <div className="flex-1">
              <Label className="text-xs mb-1">Value</Label>
              {(() => {
                const pta = productTypeAttributes.find((p) => p.attribute.id === newAttributeId);
                if (!pta) return null;
                if (pta.attribute.data_type === 'enum') {
                  return (
                    <Select
                      value={newEnumValueId ? String(newEnumValueId) : ''}
                      onValueChange={(val) => setNewEnumValueId(Number(val))}
                    >
                      <SelectTrigger className="h-8 text-xs">
                        <SelectValue placeholder="Choose value" />
                      </SelectTrigger>
                      <SelectContent>
                        {pta.attribute.values?.map((v) => (
                          <SelectItem key={v.id} value={String(v.id)}>
                            {v.code}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  );
                }
                if (pta.attribute.data_type === 'text') {
                  return (
                    <Input
                      className="h-8 text-xs"
                      value={newTextValue}
                      onChange={(e) => setNewTextValue(e.target.value)}
                      placeholder="Enter text"
                    />
                  );
                }
                if (pta.attribute.data_type === 'number') {
                  return (
                    <Input
                      className="h-8 text-xs"
                      value={newNumberValue}
                      onChange={(e) => setNewNumberValue(e.target.value)}
                      placeholder="Enter number"
                    />
                  );
                }
                if (pta.attribute.data_type === 'bool') {
                  return (
                    <div className="flex items-center h-8">
                      <Switch checked={newBoolValue} onCheckedChange={setNewBoolValue} />
                    </div>
                  );
                }
                return null;
              })()}
            </div>
          )}

          <Button
            size="sm"
            className="h-8 mt-4"
            onClick={() => addMutation.mutate()}
            disabled={isAddDisabled || addMutation.isPending}
          >
            {addMutation.isPending && <Loader2 className="w-3 h-3 mr-1 animate-spin" />}
            Add
          </Button>
        </div>
      </div>

      <div className="rounded-md border bg-muted/40 overflow-hidden">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-muted/60 border-b">
              <th className="py-1.5 px-3 text-left font-medium">Attribute</th>
              <th className="py-1.5 px-3 text-left font-medium">Type</th>
              <th className="py-1.5 px-3 text-left font-medium">Raw value</th>
              <th className="py-1.5 px-3 text-left font-medium">Translated ({localeCode})</th>
              <th className="py-1.5 px-3 text-left font-medium">Source</th>
              <th className="py-1.5 px-3 text-left font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {attrs.map((a) => {
              const inEdit = editingPavId === a.product_attribute_value_id;
              const pta = productTypeAttributes.find((p) => p.attribute.id === a.attribute_id);
              return (
                <tr key={a.product_attribute_value_id} className="border-b last:border-0">
                  <td className="py-1.5 px-3 font-mono">{a.attribute_code}</td>
                  <td className="py-1.5 px-3 text-muted-foreground">{a.data_type}</td>
                  <td className="py-1.5 px-3">
                    {inEdit && pta ? (
                      <>
                        {pta.attribute.data_type === 'enum' && (
                          <Select
                            value={editingEnumValueId ? String(editingEnumValueId) : ''}
                            onValueChange={(val) => setEditingEnumValueId(Number(val))}
                          >
                            <SelectTrigger className="h-8 text-xs">
                              <SelectValue placeholder="Choose value" />
                            </SelectTrigger>
                            <SelectContent>
                              {pta.attribute.values?.map((v) => (
                                <SelectItem key={v.id} value={String(v.id)}>
                                  {v.code}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        )}
                        {pta.attribute.data_type === 'text' && (
                          <Input
                            className="h-8 text-xs"
                            value={editingTextValue}
                            onChange={(e) => setEditingTextValue(e.target.value)}
                          />
                        )}
                        {pta.attribute.data_type === 'number' && (
                          <Input
                            className="h-8 text-xs"
                            value={editingNumberValue}
                            onChange={(e) => setEditingNumberValue(e.target.value)}
                          />
                        )}
                        {pta.attribute.data_type === 'bool' && (
                          <div className="flex items-center h-8">
                            <Switch
                              checked={editingBoolValue}
                              onCheckedChange={setEditingBoolValue}
                            />
                          </div>
                        )}
                      </>
                    ) : (
                      a.raw_value ?? '—'
                    )}
                  </td>
                  <td className="py-1.5 px-3">
                    {a.translated_value ? (
                      <span className="inline-flex items-center rounded-full px-2 py-0.5 text-[11px] bg-emerald-50 text-emerald-700">
                        {a.translated_value}
                      </span>
                    ) : (
                      <span className="text-[11px] text-muted-foreground">
                        — <span className="italic">(no {localeCode} translation yet – title uses raw value)</span>
                      </span>
                    )}
                  </td>
                  <td className="py-1.5 px-3 text-muted-foreground">{a.source}</td>
                  <td className="py-1.5 px-3 text-right space-x-1">
                    {inEdit ? (
                      <>
                        <Button
                          size="icon"
                          variant="ghost"
                          className="h-7 w-7"
                          onClick={() => saveEdit(a)}
                        >
                          <CheckCircle2 className="h-4 w-4" />
                        </Button>
                        <Button
                          size="icon"
                          variant="ghost"
                          className="h-7 w-7"
                          onClick={cancelEdit}
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </>
                    ) : (
                      <>
                        <Button
                          size="icon"
                          variant="ghost"
                          className="h-7 w-7"
                          onClick={() => startEdit(a)}
                        >
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button
                          size="icon"
                          variant="ghost"
                          className="h-7 w-7 text-destructive"
                          onClick={() => handleDelete(a)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="text-[11px] text-muted-foreground">
        Attributes marked as translatable in the product type use translations when available. If a translated value is
        missing, titles will fall back to the raw value.
      </p>
    </div>
  );
}
