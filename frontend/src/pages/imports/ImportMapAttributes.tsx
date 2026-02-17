import { useEffect, useState, useMemo, useCallback } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowRight, Link2, Loader2, CheckCircle2, Search, Info, HelpCircle, FileQuestion, Sparkles, PlusCircle, Wand2 } from 'lucide-react';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { getImport, getImportPreview, getAttributes, mapAttributes, processImport, AttributeMapping, getApiErrorMessage } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';

export default function ImportMapAttributes() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [searchParams] = useSearchParams();
  const importId = Number(id);
  const categoryBatchId = Number(searchParams.get('batch') || 0);

  const [mappings, setMappings] = useState<Record<string, number | null>>({});
  const [createNew, setCreateNew] = useState<Record<string, boolean>>({});
  const [attributeSearch, setAttributeSearch] = useState<Record<string, string>>({});
  const [fieldMappings, setFieldMappings] = useState<Record<string, string>>({});
  const [columnRoles, setColumnRoles] = useState<Record<string, 'PRODUCT_KEY' | 'VARIANT_KEY' | 'ATTRIBUTE' | null>>({});
  const [suggestions, setSuggestions] = useState<Record<string, { attributeId: number; attributeCode: string; matchType: 'exact' | 'similar' } | null>>({});
  const [suggestionsApplied, setSuggestionsApplied] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const { toast } = useToast();

  const { data: importData, isLoading: importLoading } = useQuery({
    queryKey: ['import', importId],
    queryFn: () => getImport(importId),
    enabled: !!importId,
  });

  const { data: previewData, isLoading: previewLoading } = useQuery({
    queryKey: ['import-preview', importId],
    queryFn: () => getImportPreview(importId),
    enabled: !!importId,
  });

  const { data: attributes, isLoading: attributesLoading } = useQuery({
    queryKey: ['attributes'],
    queryFn: getAttributes,
  });

  const mapMutation = useMutation({
    mutationFn: (mappingsList: AttributeMapping[]) =>
      mapAttributes(importId, categoryBatchId, mappingsList),
    onError: (error) => {
      setSubmitError(getApiErrorMessage(error));
      toast({
        variant: 'destructive',
        title: 'Mapping failed',
        description: getApiErrorMessage(error),
      });
    },
    onSuccess: async () => {
      setSubmitError(null);
      queryClient.invalidateQueries({ queryKey: ['import', importId] });
      // Automatically trigger processing
      try {
        const result = await processImport(importId);
        // Invalidate products and variants queries so lists refresh with new data
        queryClient.invalidateQueries({ queryKey: ['products'] });
        queryClient.invalidateQueries({ queryKey: ['variants'] });
        queryClient.invalidateQueries({ queryKey: ['import', importId] });
        navigate(`/imports/${id}`);
      } catch (error) {
        const message = getApiErrorMessage(error);
        setSubmitError(message);
        toast({
          variant: 'destructive',
          title: 'Import processing failed',
          description: message,
        });
        navigate(`/imports/${id}`);
      }
    },
  });

  const handleMappingChange = (column: string, attributeId: number | null) => {
    setMappings((prev) => ({ ...prev, [column]: attributeId }));
    if (attributeId) {
      setCreateNew((prev) => ({ ...prev, [column]: false }));
    }
  };

  const handleCreateNewChange = (column: string, checked: boolean) => {
    setCreateNew((prev) => ({ ...prev, [column]: checked }));
    if (checked) {
      setMappings((prev) => ({ ...prev, [column]: null }));
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!categoryBatchId) {
      return;
    }
    const mappingsList = headers.reduce<Array<AttributeMapping & { role?: string; field_mapping?: string; variant_level?: boolean; is_variation_axis?: boolean }>>((acc, header) => {
      const attributeId = mappings[header] ?? null;
      const shouldCreate = createNew[header];
      const fieldMapping = fieldMappings[header];
      const role = columnRoles[header];
      
      // Skip columns that are not mapped
      if (!fieldMapping && !attributeId && !shouldCreate) {
        return acc;
      }
      
      const mapping: AttributeMapping & { role?: string; field_mapping?: string; variant_level?: boolean; is_variation_axis?: boolean } = {
        source_attr_name: header,
        target_attribute_id: attributeId,
        strategy: shouldCreate ? 'created' : (attributeId ? 'matched' : 'ignored'),
      };
      
      // Add role information
      if (role) {
        mapping.role = role;
      }
      
      // Add field mapping information
      if (fieldMapping) {
        mapping.field_mapping = fieldMapping;
      }
      
      // Determine variant_level and is_variation_axis
      // Note: variant fields (sku, barcode, mpn) are not attributes, so variant_level doesn't apply
      // variant_level is only for attributes that should be stored at variant level
      if (role === 'ATTRIBUTE' && attributeId) {
        // For attributes, variant_level depends on whether it's marked as such
        // Default to product-level unless explicitly marked as variant-level
        mapping.variant_level = false; // Will be determined by user selection if needed
        mapping.is_variation_axis = false; // Will be set by user if needed
      }
      // For field mappings (variant.sku, product.brand, etc.), variant_level is not applicable
      
      acc.push(mapping);
      return acc;
    }, []);
    setSubmitError(null);
    mapMutation.mutate(mappingsList);
  };

  // All available product/variant fields
  // Note: source_* fields are on Variant, not Product (each variant has its own source data)
  const productFields = useMemo(() => [
    // Product fields (shared across variants in a group)
    { value: 'product.code', label: 'Product Code', role: null },
    { value: 'product.default_label', label: 'Product Default Label', role: null },
    { value: 'product.brand', label: 'Product Brand', role: null },
    { value: 'product.model', label: 'Product Model', role: null },
    { value: 'product.series', label: 'Product Series', role: null },
    { value: 'product.status', label: 'Product Status', role: null },
    // Variant fields (specific to each variant/SKU)
    { value: 'variant.sku', label: 'Variant SKU (unique per variant)', role: 'VARIANT_KEY' },
    { value: 'variant.barcode', label: 'Variant Barcode', role: null },
    { value: 'variant.mpn', label: 'Variant MPN', role: null },
    { value: 'variant.source_title', label: 'Variant Source Title', role: null },
    { value: 'variant.source_description', label: 'Variant Source Description', role: null },
    { value: 'variant.source_sku', label: 'Variant Source SKU', role: null },
    { value: 'variant.source_supplier', label: 'Variant Source Supplier', role: null },
    { value: 'variant.source_locale', label: 'Variant Source Locale', role: null },
    // Grouping key
    { value: 'PRODUCT_KEY', label: '🔑 Parent Product ID (groups variants)', role: 'PRODUCT_KEY' },
  ], []);

  const headers = useMemo(() =>
    previewData?.columns?.length
      ? previewData.columns
      : previewData?.rows?.length
        ? Object.keys(previewData.rows[0].raw || {})
        : []
  , [previewData?.columns, previewData?.rows]);

  // Duplicate column names cause "category_batch_id, source_attr_name must be unique" error
  const duplicateHeaders = useMemo(() => {
    const seen = new Map<string, number>();
    headers.forEach((h, i) => seen.set(h, (seen.get(h) ?? 0) + 1));
    return headers.filter((h, i) => (seen.get(h) ?? 0) > 1);
  }, [headers]);
  const uniqueDuplicates = useMemo(() => [...new Set(duplicateHeaders)], [duplicateHeaders]);

  // Normalize string for comparison (lowercase, remove special chars)
  const normalizeString = useCallback((str: string): string => {
    return str.toLowerCase()
      .replace(/[_\-\s]+/g, '') // Remove underscores, hyphens, spaces
      .replace(/[^a-z0-9]/g, ''); // Keep only alphanumeric
  }, []);

  // Find matching attribute for a column name
  const findMatchingAttribute = useCallback((columnName: string, attrs: Array<{ id: number; code: string; name?: string }> | undefined) => {
    if (!attrs?.length) return null;
    
    const normalizedColumn = normalizeString(columnName);
    
    // First try exact match on code
    const exactCodeMatch = attrs.find(attr => 
      normalizeString(attr.code) === normalizedColumn
    );
    if (exactCodeMatch) {
      return { attributeId: exactCodeMatch.id, attributeCode: exactCodeMatch.code, matchType: 'exact' as const };
    }
    
    // Then try exact match on name
    const exactNameMatch = attrs.find(attr => 
      attr.name && normalizeString(attr.name) === normalizedColumn
    );
    if (exactNameMatch) {
      return { attributeId: exactNameMatch.id, attributeCode: exactNameMatch.code, matchType: 'exact' as const };
    }
    
    // Try partial match (column contains attribute code or vice versa)
    const partialMatch = attrs.find(attr => {
      const normalizedCode = normalizeString(attr.code);
      const normalizedName = attr.name ? normalizeString(attr.name) : '';
      return (
        normalizedColumn.includes(normalizedCode) ||
        normalizedCode.includes(normalizedColumn) ||
        (normalizedName && (normalizedColumn.includes(normalizedName) || normalizedName.includes(normalizedColumn)))
      );
    });
    if (partialMatch) {
      return { attributeId: partialMatch.id, attributeCode: partialMatch.code, matchType: 'similar' as const };
    }
    
    return null;
  }, [normalizeString]);

  // Build suggestions when attributes and headers are loaded
  useEffect(() => {
    if (!attributes?.results?.length || !headers.length || suggestionsApplied) return;
    
    const newSuggestions: Record<string, { attributeId: number; attributeCode: string; matchType: 'exact' | 'similar' } | null> = {};
    
    // Skip columns that are likely product/variant fields
    const fieldKeywords = ['sku', 'barcode', 'mpn', 'brand', 'title', 'description', 'parent', 'product_id', 'price', 'id'];
    
    headers.forEach(header => {
      const normalizedHeader = normalizeString(header);
      const isLikelyField = fieldKeywords.some(kw => normalizedHeader.includes(kw));
      
      if (!isLikelyField) {
        const match = findMatchingAttribute(header, attributes.results);
        newSuggestions[header] = match;
      } else {
        newSuggestions[header] = null;
      }
    });
    
    setSuggestions(newSuggestions);
  }, [attributes?.results, headers, findMatchingAttribute, normalizeString, suggestionsApplied]);

  // Apply all suggestions
  const applyAllSuggestions = useCallback(() => {
    const newMappings: Record<string, number | null> = { ...mappings };
    const newColumnRoles: Record<string, 'PRODUCT_KEY' | 'VARIANT_KEY' | 'ATTRIBUTE' | null> = { ...columnRoles };
    
    Object.entries(suggestions).forEach(([header, suggestion]) => {
      if (suggestion && !fieldMappings[header] && !createNew[header]) {
        newMappings[header] = suggestion.attributeId;
        newColumnRoles[header] = 'ATTRIBUTE';
      }
    });
    
    setMappings(newMappings);
    setColumnRoles(newColumnRoles);
    setSuggestionsApplied(true);
  }, [suggestions, mappings, columnRoles, fieldMappings, createNew]);

  // Create new attributes for all unmapped columns
  const createAllNew = useCallback(() => {
    const newCreateNew: Record<string, boolean> = { ...createNew };
    
    // Skip columns that are mapped to fields or attributes
    headers.forEach(header => {
      const hasFieldMapping = !!fieldMappings[header];
      const hasAttributeMapping = !!mappings[header];
      
      if (!hasFieldMapping && !hasAttributeMapping) {
        newCreateNew[header] = true;
      }
    });
    
    setCreateNew(newCreateNew);
  }, [headers, fieldMappings, mappings, createNew]);

  // Count suggestions and unmapped columns
  const suggestionCount = useMemo(() => 
    Object.values(suggestions).filter(s => s !== null).length
  , [suggestions]);
  
  const unmappedCount = useMemo(() => 
    headers.filter(h => !fieldMappings[h] && !mappings[h] && !createNew[h]).length
  , [headers, fieldMappings, mappings, createNew]);

  // Filter attributes based on search term for each column
  // Searches in: code, name, and description
  const getFilteredAttributes = (columnName: string) => {
    const searchTerm = attributeSearch[columnName] || '';
    if (!attributes?.results) return [];
    
    if (!searchTerm) return attributes.results;
    
    const lowerSearch = searchTerm.toLowerCase();
    return attributes.results.filter(attr => {
      const codeMatch = attr.code?.toLowerCase().includes(lowerSearch);
      const nameMatch = attr.name?.toLowerCase().includes(lowerSearch);
      const descMatch = attr.description?.toLowerCase().includes(lowerSearch);
      return codeMatch || nameMatch || descMatch;
    });
  };



  const isLoading = importLoading || previewLoading || attributesLoading;

  if (isLoading) {
    return (
      <div className="page-container flex items-center justify-center min-h-[50vh]">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="page-container">
      <PageHeader
        title="Map Attributes"
        description="Connect file columns to database attributes"
        breadcrumbs={[
          { label: 'Dashboard', href: '/' },
          { label: 'Imports', href: '/imports' },
          { label: importData?.original_filename || `Import #${id}`, href: `/imports/${id}` },
          { label: 'Map Attributes' },
        ]}
      />

      {!categoryBatchId && (
        <Card className="mb-6 border-status-warning/50">
          <CardHeader>
            <CardTitle className="text-status-warning">Category required</CardTitle>
            <CardDescription>
              Select a category before mapping attributes so we can link mappings to a batch.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={() => navigate(`/imports/${id}/assign-category`)}>
              Assign Category
              <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
          </CardContent>
        </Card>
      )}

      {submitError && (
        <Alert variant="destructive" className="mb-6">
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{submitError}</AlertDescription>
        </Alert>
      )}

      {uniqueDuplicates.length > 0 && (
        <Alert variant="destructive" className="mb-6">
          <AlertTitle>Duplicate column names in your file</AlertTitle>
          <AlertDescription>
            Each column header must be unique. Your file has duplicate headers:{' '}
            <strong>{uniqueDuplicates.join(', ')}</strong>. Rename them in your spreadsheet (e.g. &quot;Color&quot; and &quot;Color_2&quot;) and re-upload.
          </AlertDescription>
        </Alert>
      )}

      <Alert className="mb-6">
        <HelpCircle className="h-4 w-4" />
        <AlertTitle>Parent-Variant Product Import</AlertTitle>
        <AlertDescription className="space-y-2 mt-2">
          <p><strong>This import stores products with variants (like different colors/sizes of the same product):</strong></p>
          <ul className="list-disc list-inside space-y-1 ml-2">
            <li><strong>Parent Product ID:</strong> Column that groups variants together (e.g., "parent_id")</li>
            <li><strong>Variant SKU:</strong> Unique identifier for each variant</li>
            <li><strong>Variation Axes:</strong> Attributes like color, size that differentiate variants (auto-detected)</li>
            <li><strong>Product Fields:</strong> Shared data like brand, title (same for all variants)</li>
            <li><strong>Variant Attributes:</strong> Specific data like price, stock (different per variant)</li>
          </ul>
          <p className="text-sm text-muted-foreground mt-2">
            💡 The system will automatically detect variation axes and store them for later title generation.
          </p>
        </AlertDescription>
      </Alert>

      <form onSubmit={handleSubmit}>
        <Card className="mb-6">
          <CardHeader>
            <div className="flex items-start justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Link2 className="w-5 h-5" />
                  Column Mapping
                </CardTitle>
                <CardDescription>
                  Map each file column to an existing database attribute or create a new one.
                </CardDescription>
              </div>
              <div className="flex gap-2">
                {suggestionCount > 0 && !suggestionsApplied && (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={applyAllSuggestions}
                    className="gap-2"
                  >
                    <Wand2 className="w-4 h-4" />
                    Apply {suggestionCount} Suggestions
                  </Button>
                )}
                {unmappedCount > 0 && (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={createAllNew}
                    className="gap-2"
                  >
                    <PlusCircle className="w-4 h-4" />
                    Create All New ({unmappedCount})
                  </Button>
                )}
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>File Column</th>
                    <th>Sample Data</th>
                    <th className="min-w-[350px]">Mapping</th>
                    <th>Create New</th>
                    <th>Variation Axis</th>
                  </tr>
                </thead>
                <tbody>
                  {headers.map((header, i) => {
                    const mapping = mappings[header] ?? null;
                    const shouldCreate = createNew[header] ?? false;
                    const fieldMapping = fieldMappings[header];
                    const suggestion = suggestions[header];
                    const sampleValues = previewData?.rows
                      .slice(0, 3)
                      .map((r) => r.raw?.[header])
                      .filter(Boolean)
                      .join(', ');
                    
                    const filteredAttrs = getFilteredAttributes(header);
                    const isVariationAxis = columnRoles[header] === 'ATTRIBUTE' && mapping;
                    
                    // Check if suggestion is not yet applied
                    const showSuggestion = suggestion && !mapping && !fieldMapping && !shouldCreate;

                    return (
                      <tr key={i}>
                        <td className="font-medium">
                          <div className="flex items-center gap-2">
                            {header}
                            {showSuggestion && (
                              <TooltipProvider>
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <Badge 
                                      variant="outline" 
                                      className={`cursor-pointer text-xs ${
                                        suggestion.matchType === 'exact' 
                                          ? 'border-green-500 text-green-600 bg-green-50' 
                                          : 'border-yellow-500 text-yellow-600 bg-yellow-50'
                                      }`}
                                      onClick={() => {
                                        setMappings(prev => ({ ...prev, [header]: suggestion.attributeId }));
                                        setColumnRoles(prev => ({ ...prev, [header]: 'ATTRIBUTE' }));
                                      }}
                                    >
                                      <Sparkles className="w-3 h-3 mr-1" />
                                      {suggestion.matchType === 'exact' ? 'Match' : 'Similar'}: {suggestion.attributeCode}
                                    </Badge>
                                  </TooltipTrigger>
                                  <TooltipContent>
                                    <p className="text-xs">Click to apply suggestion</p>
                                  </TooltipContent>
                                </Tooltip>
                              </TooltipProvider>
                            )}
                          </div>
                        </td>
                        <td className="text-muted-foreground text-sm max-w-[200px] truncate">
                          {sampleValues || '—'}
                        </td>
                        <td>
                          <div className="space-y-2">
                            <Select
                              value={fieldMapping || mapping?.toString() || 'skip'}
                              onValueChange={(val) => {
                                if (val === 'skip') {
                                  setFieldMappings(prev => ({ ...prev, [header]: '' }));
                                  handleMappingChange(header, null);
                                  setColumnRoles(prev => ({ ...prev, [header]: null }));
                                } else if (val === 'PRODUCT_KEY') {
                                  setFieldMappings(prev => ({ ...prev, [header]: val }));
                                  handleMappingChange(header, null);
                                  setColumnRoles(prev => ({ ...prev, [header]: 'PRODUCT_KEY' }));
                                } else if (val.startsWith('product.') || val.startsWith('variant.')) {
                                  const field = productFields.find(f => f.value === val);
                                  setFieldMappings(prev => ({ ...prev, [header]: val }));
                                  handleMappingChange(header, null);
                                  setColumnRoles(prev => ({ ...prev, [header]: field?.role || null }));
                                } else {
                                  setFieldMappings(prev => ({ ...prev, [header]: '' }));
                                  handleMappingChange(header, Number(val));
                                  setColumnRoles(prev => ({ ...prev, [header]: 'ATTRIBUTE' }));
                                }
                              }}
                              disabled={shouldCreate}
                            >
                              <SelectTrigger className="w-full">
                                <SelectValue placeholder={shouldCreate ? 'Creating new attribute' : 'Select mapping...'} />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="skip">— Skip this column —</SelectItem>
                                <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground">
                                  Parent-Variant Structure
                                </div>
                                <SelectItem value="PRODUCT_KEY">
                                  🔑 Parent Product ID (groups variants)
                                </SelectItem>
                                <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground">
                                  Product Fields
                                </div>
                                {productFields.filter(f => f.value !== 'PRODUCT_KEY').map((field) => (
                                  <SelectItem key={field.value} value={field.value}>
                                    {field.value === 'variant.sku' ? '🔖 ' : ''}{field.label}
                                  </SelectItem>
                                ))}
                                {attributes?.results && attributes.results.length > 0 && (
                                  <>
                                    <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground border-t mt-1 pt-2 flex items-center gap-2">
                                      Attributes (for variations like color, size, etc.)
                                      <TooltipProvider>
                                        <Tooltip>
                                          <TooltipTrigger asChild>
                                            <FileQuestion className="h-3 w-3 cursor-help" />
                                          </TooltipTrigger>
                                          <TooltipContent className="max-w-xs">
                                            <p className="text-xs">Search by attribute code, name, or description. Hover over attributes to see full details.</p>
                                          </TooltipContent>
                                        </Tooltip>
                                      </TooltipProvider>
                                    </div>
                                    <div className="px-2 py-1">
                                      <div className="relative">
                                        <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                                        <Input
                                          type="text"
                                          placeholder="Search code, name, or description..."
                                          value={attributeSearch[header] || ''}
                                          onChange={(e) => {
                                            e.stopPropagation();
                                            setAttributeSearch(prev => ({
                                              ...prev,
                                              [header]: e.target.value
                                            }));
                                          }}
                                          onClick={(e) => e.stopPropagation()}
                                          className="pl-8 h-8 text-sm"
                                        />
                                      </div>
                                    </div>
                                    {filteredAttrs.length > 0 ? (
                                      filteredAttrs.map((attr) => (
                                        <TooltipProvider key={attr.id}>
                                          <Tooltip>
                                            <TooltipTrigger asChild>
                                              <SelectItem value={attr.id.toString()}>
                                                <div className="flex items-center gap-2">
                                                  <span>⚡ {attr.code}</span>
                                                  <span className="text-xs text-muted-foreground">({attr.data_type})</span>
                                                </div>
                                              </SelectItem>
                                            </TooltipTrigger>
                                            <TooltipContent side="right" className="max-w-sm">
                                              <div className="space-y-1">
                                                <p className="font-semibold">{attr.name || attr.code}</p>
                                                {attr.description && (
                                                  <p className="text-xs text-muted-foreground">{attr.description}</p>
                                                )}
                                                <div className="text-xs border-t pt-1 mt-1">
                                                  <div>Type: <span className="font-medium">{attr.data_type}</span></div>
                                                  {attr.is_value_translatable && (
                                                    <div className="text-blue-600">✓ Translatable</div>
                                                  )}
                                                </div>
                                              </div>
                                            </TooltipContent>
                                          </Tooltip>
                                        </TooltipProvider>
                                      ))
                                    ) : (
                                      <div className="px-2 py-2 text-sm text-muted-foreground">
                                        {attributeSearch[header] ? 'No matching attributes found' : 'No attributes found'}
                                      </div>
                                    )}
                                  </>
                                )}
                              </SelectContent>
                            </Select>
                          </div>
                        </td>
                        <td>
                          <div className="flex items-center gap-2">
                            <Checkbox
                              checked={shouldCreate}
                              onCheckedChange={(checked) =>
                                handleCreateNewChange(header, Boolean(checked))
                              }
                              aria-label={`Create new attribute for ${header}`}
                            />
                            {shouldCreate && (
                              <span className="text-xs text-muted-foreground">
                                Will create
                              </span>
                            )}
                          </div>
                        </td>
                        <td>
                          {isVariationAxis && (
                            <div className="flex items-center gap-2">
                              <Checkbox
                                checked={true}
                                onCheckedChange={() => {}}
                              />
                              <span className="text-xs text-muted-foreground">
                                Variation axis
                              </span>
                            </div>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        <div className="flex justify-end gap-3">
          <Button
            type="button"
            variant="outline"
            onClick={() => navigate(`/imports/${id}/assign-category`)}
          >
            Back
          </Button>
          <Button type="submit" disabled={mapMutation.isPending || !categoryBatchId || uniqueDuplicates.length > 0}>
            {mapMutation.isPending ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <CheckCircle2 className="w-4 h-4 mr-2" />
            )}
            Complete Import
          </Button>
        </div>
      </form>
    </div>
  );
}
