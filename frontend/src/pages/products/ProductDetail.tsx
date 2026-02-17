import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, Save, Loader2, Plus, Trash2, X, Edit, Package, Eye, ChevronDown, ChevronUp, Tag, List } from 'lucide-react';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { Textarea } from '@/components/ui/textarea';
import { useToast } from '@/components/ui/use-toast';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  getProductTypeAttributes,
  ProductTypeAttribute,
  apiClient,
  createAttributeWithProductType,
  CreateAttributeRequest,
  addAttributeValue,
  AttributeValue,
  getAttributes,
  Attribute,
  linkAttributeToProductType,
  getProductVariants,
  createVariantForProduct,
  updateVariant,
  deleteVariant,
  Variant,
  getVariantAttributeValues,
  getVariantAttributeDetails,
  getProductKeywordMaps,
  getHookTerms,
  removeHookTerm,
  getLocales,
  type ProductKeywordMap,
  type HookTermItem,
  getPlannerRuns,
} from '@/lib/api';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Badge } from '@/components/ui/badge';

interface Product {
  id: number;
  product_type_id: number;
  code: string;
  status: string;
  brand: string | null;
  model: string | null;
  series: string | null;
  default_label: string;
}

interface ProductAttribute {
  id: number;
  product_id: number;
  attribute_id: number;
  attribute_code: string;
  value_text: string | null;
  value_number: number | null;
  value_bool: boolean | null;
  attribute_value_id: number | null;
}

export default function ProductDetail() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const [attributes, setAttributes] = useState<Record<string, string | number | boolean>>({});
  const [isAddAttributeOpen, setIsAddAttributeOpen] = useState(false);
  const [newAttribute, setNewAttribute] = useState<CreateAttributeRequest>({
    code: '',
    data_type: 'text',
    unit: '',
    is_multi: false,
    is_value_translatable: false,
    product_type_id: 0,
    required: false,
    filterable: false,
    variant_level: false,
  });
  const [addingValueToAttribute, setAddingValueToAttribute] = useState<number | null>(null);
  const [newValueCode, setNewValueCode] = useState('');
  
  // Variant management state
  const [showCreateVariantDialog, setShowCreateVariantDialog] = useState(false);
  const [showEditVariantDialog, setShowEditVariantDialog] = useState(false);
  const [showDeleteVariantDialog, setShowDeleteVariantDialog] = useState(false);
  const [selectedVariant, setSelectedVariant] = useState<Variant | null>(null);
  const [variantForm, setVariantForm] = useState<Omit<Variant, 'id' | 'product_id' | 'internal_sku' | 'created_at'>>({
    sku: null,
    barcode: null,
    mpn: null,
    axis_signature: null,
    source_title: '',
    source_description: '',
    source_locale: '',
    source_supplier: '',
    source_sku: '',
  });
  const [variantAttributes, setVariantAttributes] = useState<Record<string, string | number | boolean>>({});
  const [expandedVariantId, setExpandedVariantId] = useState<number | null>(null);
  
  // Keyword mapping state
  const [selectedRunId, setSelectedRunId] = useState<number | null>(null);
  const [hookTermsLocaleId, setHookTermsLocaleId] = useState<number | null>(null);

  // Attributes & Values viewer state
  const [attrsViewVariantId, setAttrsViewVariantId] = useState<number | null>(null);
  const [attrsViewLocaleCode, setAttrsViewLocaleCode] = useState<string>('');

  const { data: product, isLoading: isLoadingProduct } = useQuery({
    queryKey: ['product', id],
    queryFn: async () => {
      const response = await apiClient.get<Product>(`/products/${id}/`);
      return response.data;
    },
    enabled: !!id,
  });

  const { data: productAttributes, isLoading: isLoadingAttributes, refetch: refetchAttributes, error: productAttributesError } = useQuery({
    queryKey: ['product-attributes', id],
    queryFn: async () => {
      if (!id) throw new Error('Product ID is required');
      const response = await apiClient.get<ProductAttribute[]>(`/products/${id}/attribute-values/`);
      return response.data;
    },
    enabled: !!id && !!Number(id),
    retry: 1,
  });

  const { data: typeAttributes, refetch: refetchTypeAttributes, error: typeAttributesError, isLoading: isLoadingTypeAttributes } = useQuery({
    queryKey: ['product-type-attributes', product?.product_type_id],
    queryFn: () => {
      if (!product?.product_type_id) throw new Error('Product type ID is required');
      return getProductTypeAttributes(product.product_type_id);
    },
    enabled: !!product?.product_type_id && !!Number(product.product_type_id),
    retry: 1,
  });

  const { data: allAttributes } = useQuery({
    queryKey: ['all-attributes'],
    queryFn: () => getAttributes(),
  });

  // Fetch variants for this product
  const { data: variants, isLoading: isLoadingVariants, refetch: refetchVariants } = useQuery({
    queryKey: ['product-variants', id],
    queryFn: () => getProductVariants(Number(id)),
    enabled: !!id,
  });

  const { data: localesData } = useQuery({
    queryKey: ['locales'],
    queryFn: () => getLocales({ page_size: 100 }),
  });
  const locales = localesData?.results ?? [];
  useEffect(() => {
    if (hookTermsLocaleId == null && locales.length > 0) setHookTermsLocaleId(locales[0].id);
  }, [locales.length, locales, hookTermsLocaleId]);
  useEffect(() => {
    if (!attrsViewLocaleCode && locales.length > 0) setAttrsViewLocaleCode(locales[0].code);
  }, [locales, attrsViewLocaleCode]);

  const { data: variantAttrDetails, isLoading: isLoadingVariantAttrs } = useQuery({
    queryKey: ['variant-attribute-details', attrsViewVariantId, attrsViewLocaleCode],
    queryFn: () =>
      getVariantAttributeDetails(attrsViewVariantId!, {
        locale_code: attrsViewLocaleCode,
        channel_code: undefined,
      }),
    enabled: !!attrsViewVariantId && !!attrsViewLocaleCode,
  });

  const productId = id ? Number(id) : undefined;
  const { data: savedHookData, refetch: refetchSavedHook } = useQuery({
    queryKey: ['hook-terms', productId, hookTermsLocaleId],
    queryFn: () =>
      getHookTerms(productId!, { locale_id: hookTermsLocaleId!, channel_id: null }),
    enabled: !!productId && !!hookTermsLocaleId,
  });

  const removeHookTermMutation = useMutation({
    mutationFn: ({ hookTermId }: { hookTermId: number }) => removeHookTerm(productId!, hookTermId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['hook-terms', productId, hookTermsLocaleId] });
      refetchSavedHook();
    },
    onError: (err: any) =>
      toast({ title: 'Failed to remove hook term', description: err?.response?.data?.detail || err?.message, variant: 'destructive' }),
  });

  // Get unlinked attributes (attributes not in typeAttributes)
  const linkedAttributeIds = new Set(typeAttributes?.map((ta) => ta.attribute.id) || []);
  const unlinkedAttributes = allAttributes?.results?.filter(
    (attr) => !linkedAttributeIds.has(attr.id)
  ) || [];

  // Get variant-level attributes for the variant form
  const variantLevelAttributes = typeAttributes?.filter((ta) => ta.variant_level) || [];

  const addValueMutation = useMutation({
    mutationFn: (attributeId: number) =>
      addAttributeValue({
        attribute_id: attributeId,
        code: newValueCode.toLowerCase().replace(/[^a-z0-9_]/g, '_'),
      }),
    onSuccess: (data, attributeId) => {
      toast({
        title: 'Value added',
        description: `New value "${data.code}" has been added to the attribute.`,
      });
      setNewValueCode('');
      setAddingValueToAttribute(null);
      // Refetch type attributes to get updated values
      queryClient.invalidateQueries({ queryKey: ['product-type-attributes', product?.product_type_id] });
      refetchTypeAttributes();
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to add value',
        description: error?.response?.data?.error || error?.message || 'Something went wrong.',
        variant: 'destructive',
      });
    },
  });

  const linkAttributeMutation = useMutation({
    mutationFn: (attributeId: number) =>
      linkAttributeToProductType(product!.product_type_id, {
        attribute_id: attributeId,
        required: false,
        filterable: false,
        variant_level: false,
      }),
    onSuccess: () => {
      toast({
        title: 'Attribute linked',
        description: 'The attribute has been linked to this product type.',
      });
      queryClient.invalidateQueries({ queryKey: ['product-type-attributes', product?.product_type_id] });
      queryClient.invalidateQueries({ queryKey: ['all-attributes'] });
      refetchTypeAttributes();
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to link attribute',
        description: error?.response?.data?.error || error?.message || 'Something went wrong.',
        variant: 'destructive',
      });
    },
  });

  // Update product_type_id when product changes
  useEffect(() => {
    if (product) {
      setNewAttribute((prev) => ({
        ...prev,
        product_type_id: product.product_type_id,
      }));
    }
  }, [product]);

  // Load existing attributes into state
  useEffect(() => {
    if (productAttributes && Object.keys(attributes).length === 0) {
      const attrMap: Record<string, string | number | boolean> = {};
      productAttributes.forEach((attr) => {
        if (attr.value_text !== null) {
          attrMap[attr.attribute_code] = attr.value_text;
        } else if (attr.value_number !== null) {
          attrMap[attr.attribute_code] = attr.value_number;
        } else if (attr.value_bool !== null) {
          attrMap[attr.attribute_code] = attr.value_bool;
        } else if (attr.attribute_value_id !== null) {
          attrMap[attr.attribute_code] = attr.attribute_value_id;
        }
      });
      setAttributes(attrMap);
    }
  }, [productAttributes]);

  const updateAttributesMutation = useMutation({
    mutationFn: async () => {
      if (!product) return;

      // Send attributes to backend
      const payload = { attributes };
      const response = await apiClient.patch(`/products/${product.id}/`, payload);
      return response.data;
    },
    onSuccess: () => {
      toast({
        title: 'Attributes saved',
        description: 'Group attributes have been updated successfully.',
      });
      refetchAttributes();
    },
    onError: (error) => {
      toast({
        title: 'Failed to save attributes',
        description: error instanceof Error ? error.message : 'Something went wrong.',
        variant: 'destructive',
      });
    },
  });

  const createAttributeMutation = useMutation({
    mutationFn: () => createAttributeWithProductType(newAttribute),
    onSuccess: () => {
      toast({
        title: 'Attribute created',
        description: 'The new attribute has been added to this product type.',
      });
      setIsAddAttributeOpen(false);
      setNewAttribute({
        code: '',
        data_type: 'text',
        unit: '',
        is_multi: false,
        is_value_translatable: false,
        product_type_id: product?.product_type_id || 0,
        required: false,
        filterable: false,
        variant_level: false,
      });
      // Invalidate and refetch type attributes
      queryClient.invalidateQueries({ queryKey: ['product-type-attributes', product?.product_type_id] });
      refetchTypeAttributes();
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to create attribute',
        description: error?.response?.data?.detail || error?.message || 'Something went wrong.',
        variant: 'destructive',
      });
    },
  });

  // Fetch variant attributes when editing or viewing
  const { data: currentVariantAttributes, refetch: refetchCurrentVariantAttributes } = useQuery({
    queryKey: ['variant-attributes', selectedVariant?.id],
    queryFn: () => getVariantAttributeValues(selectedVariant!.id),
    enabled: !!selectedVariant && (showEditVariantDialog || expandedVariantId === selectedVariant.id),
  });

  // Fetch variant attributes for expanded row
  const { data: expandedVariantAttributes } = useQuery({
    queryKey: ['variant-attributes', expandedVariantId],
    queryFn: () => getVariantAttributeValues(expandedVariantId!),
    enabled: !!expandedVariantId,
  });

  // Fetch available planner runs
  const { data: plannerRunsData } = useQuery({
    queryKey: ['planner-runs-list'],
    queryFn: () => getPlannerRuns({ page_size: 100 }),
  });

  // Fetch product keyword maps for selected run
  const { data: keywordMapsData, isLoading: keywordMapsLoading } = useQuery({
    queryKey: ['product-keyword-maps', id, selectedRunId],
    queryFn: () => getProductKeywordMaps(selectedRunId!, { 
      product_id: Number(id),
      page_size: 100 
    }),
    enabled: !!selectedRunId && !!id,
  });

  // Load variant attributes into state when editing
  useEffect(() => {
    if (currentVariantAttributes && showEditVariantDialog) {
      const attrMap: Record<string, string | number | boolean> = {};
      currentVariantAttributes.forEach((attr) => {
        if (attr.value_text !== null) {
          attrMap[attr.attribute_code] = attr.value_text;
        } else if (attr.value_number !== null) {
          attrMap[attr.attribute_code] = attr.value_number;
        } else if (attr.value_bool !== null) {
          attrMap[attr.attribute_code] = attr.value_bool;
        } else if (attr.attribute_value_id !== null) {
          attrMap[attr.attribute_code] = attr.attribute_value_id;
        }
      });
      setVariantAttributes(attrMap);
    }
  }, [currentVariantAttributes, showEditVariantDialog]);

  // Variant mutations
  const createVariantMutation = useMutation({
    mutationFn: () => createVariantForProduct(Number(id), {
      ...variantForm,
      sku: variantForm.sku || null,
      barcode: variantForm.barcode || null,
      mpn: variantForm.mpn || null,
      attributes: variantAttributes,
    } as any),
    onSuccess: () => {
      toast({
        title: 'Variant created',
        description: 'The new variant has been added to this product.',
      });
      setShowCreateVariantDialog(false);
      setVariantForm({
        sku: null,
        barcode: null,
        mpn: null,
        axis_signature: null,
        source_title: '',
        source_description: '',
        source_locale: '',
        source_supplier: '',
        source_sku: '',
      });
      setVariantAttributes({});
      refetchVariants();
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to create variant',
        description: error?.response?.data?.detail || error?.message || 'Something went wrong.',
        variant: 'destructive',
      });
    },
  });

  const updateVariantMutation = useMutation({
    mutationFn: () => updateVariant(selectedVariant!.id, {
      ...variantForm,
      attributes: variantAttributes,
    } as any),
    onSuccess: () => {
      toast({
        title: 'Variant updated',
        description: 'The variant has been updated successfully.',
      });
      setShowEditVariantDialog(false);
      setSelectedVariant(null);
      refetchVariants();
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to update variant',
        description: error?.response?.data?.detail || error?.message || 'Something went wrong.',
        variant: 'destructive',
      });
    },
  });

  const deleteVariantMutation = useMutation({
    mutationFn: () => deleteVariant(selectedVariant!.id),
    onSuccess: () => {
      toast({
        title: 'Variant deleted',
        description: 'The variant has been deleted successfully.',
      });
      setShowDeleteVariantDialog(false);
      setSelectedVariant(null);
      refetchVariants();
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to delete variant',
        description: error?.response?.data?.detail || error?.message || 'Something went wrong.',
        variant: 'destructive',
      });
    },
  });

  const handleAttributeChange = (attrCode: string, value: string | number | boolean) => {
    setAttributes((prev) => ({
      ...prev,
      [attrCode]: value,
    }));
  };

  const handleEditVariant = (variant: Variant) => {
    setSelectedVariant(variant);
    setVariantForm({
      sku: variant.sku,
      barcode: variant.barcode,
      mpn: variant.mpn,
      axis_signature: variant.axis_signature,
      source_title: variant.source_title || '',
      source_description: variant.source_description || '',
      source_locale: variant.source_locale || '',
      source_supplier: variant.source_supplier || '',
      source_sku: variant.source_sku || '',
    });
    setVariantAttributes({});
    setShowEditVariantDialog(true);
  };

  const handleVariantAttributeChange = (attrCode: string, value: string | number | boolean) => {
    setVariantAttributes((prev) => ({
      ...prev,
      [attrCode]: value,
    }));
  };

  const renderVariantAttributeField = (typeAttr: ProductTypeAttribute) => {
    const attr = typeAttr.attribute;
    const value = variantAttributes[attr.code] ?? '';

    switch (attr.data_type) {
      case 'text':
        return (
          <div key={attr.code} className="space-y-2">
            <Label htmlFor={`v-attr-${attr.code}`}>
              {attr.code.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
            </Label>
            <Textarea
              id={`v-attr-${attr.code}`}
              value={String(value)}
              onChange={(e) => handleVariantAttributeChange(attr.code, e.target.value)}
              placeholder={`Enter ${attr.code}`}
              rows={2}
            />
          </div>
        );

      case 'number':
        return (
          <div key={attr.code} className="space-y-2">
            <Label htmlFor={`v-attr-${attr.code}`}>
              {attr.code.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
              {attr.unit && <span className="text-xs text-muted-foreground ml-1">({attr.unit})</span>}
            </Label>
            <Input
              id={`v-attr-${attr.code}`}
              type="number"
              step="any"
              value={value === '' ? '' : Number(value)}
              onChange={(e) => handleVariantAttributeChange(attr.code, e.target.value ? parseFloat(e.target.value) : '')}
              placeholder={`Enter ${attr.code}`}
            />
          </div>
        );

      case 'bool':
        return (
          <div key={attr.code} className="flex items-center space-x-2 py-2">
            <Checkbox
              id={`v-attr-${attr.code}`}
              checked={Boolean(value)}
              onCheckedChange={(checked) => handleVariantAttributeChange(attr.code, Boolean(checked))}
            />
            <Label htmlFor={`v-attr-${attr.code}`} className="cursor-pointer">
              {attr.code.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
            </Label>
          </div>
        );

      case 'enum':
        return (
          <div key={attr.code} className="space-y-2">
            <Label htmlFor={`v-attr-${attr.code}`}>
              {attr.code.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
            </Label>
            <Select value={String(value)} onValueChange={(val) => handleVariantAttributeChange(attr.code, parseInt(val))}>
              <SelectTrigger id={`v-attr-${attr.code}`}>
                <SelectValue placeholder={`Select ${attr.code}...`} />
              </SelectTrigger>
              <SelectContent>
                {attr.values?.map((v) => (
                  <SelectItem key={v.id} value={String(v.id)}>
                    {v.code}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        );

      default:
        return null;
    }
  };

  const handleDeleteVariant = (variant: Variant) => {
    setSelectedVariant(variant);
    setShowDeleteVariantDialog(true);
  };

  const renderAttributeField = (typeAttr: ProductTypeAttribute) => {
    const attr = typeAttr.attribute;
    const value = attributes[attr.code] ?? '';

    switch (attr.data_type) {
      case 'text':
        return (
          <div key={attr.code} className="space-y-2">
            <Label htmlFor={`attr-${attr.code}`} className={typeAttr.required ? 'font-semibold' : ''}>
              {attr.code.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
              {typeAttr.required && <span className="text-red-500 ml-1 text-lg">*</span>}
            </Label>
            <Textarea
              id={`attr-${attr.code}`}
              value={String(value)}
              onChange={(e) => handleAttributeChange(attr.code, e.target.value)}
              placeholder={`Enter ${attr.code}`}
              rows={3}
            />
            {attr.unit && <span className="text-sm text-muted-foreground">Unit: {attr.unit}</span>}
          </div>
        );

      case 'number':
        return (
          <div key={attr.code} className="space-y-2">
            <Label htmlFor={`attr-${attr.code}`} className={typeAttr.required ? 'font-semibold' : ''}>
              {attr.code.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
              {typeAttr.required && <span className="text-red-500 ml-1 text-lg">*</span>}
            </Label>
            <Input
              id={`attr-${attr.code}`}
              type="number"
              step="any"
              value={value === '' ? '' : Number(value)}
              onChange={(e) => handleAttributeChange(attr.code, e.target.value ? parseFloat(e.target.value) : '')}
              placeholder={`Enter ${attr.code}`}
            />
            {attr.unit && <span className="text-sm text-muted-foreground">Unité: {attr.unit}</span>}
          </div>
        );

      case 'bool':
        return (
          <div key={attr.code} className="flex items-center space-x-2 py-2">
            <Checkbox
              id={`attr-${attr.code}`}
              checked={Boolean(value)}
              onCheckedChange={(checked) => handleAttributeChange(attr.code, Boolean(checked))}
            />
            <Label htmlFor={`attr-${attr.code}`} className="cursor-pointer">
              {attr.code.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
              {typeAttr.required && <span className="text-red-500 ml-1 text-lg">*</span>}
            </Label>
          </div>
        );

      case 'enum':
        return (
          <div key={attr.code} className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor={`attr-${attr.code}`} className={typeAttr.required ? 'font-semibold' : ''}>
                {attr.code.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
                {typeAttr.required && <span className="text-red-500 ml-1 text-lg">*</span>}
              </Label>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => {
                  setAddingValueToAttribute(attr.id);
                  setNewValueCode('');
                }}
                className="h-7 text-xs"
              >
                <Plus className="w-3 h-3 mr-1" />
                Add Value
              </Button>
            </div>
            <Select value={String(value)} onValueChange={(val) => handleAttributeChange(attr.code, parseInt(val))}>
              <SelectTrigger id={`attr-${attr.code}`}>
                <SelectValue placeholder={`Select ${attr.code}...`} />
              </SelectTrigger>
              <SelectContent>
                {attr.values?.map((v) => (
                  <SelectItem key={v.id} value={String(v.id)}>
                    {v.code}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {addingValueToAttribute === attr.id && (
              <div className="flex gap-2 items-end p-3 border rounded-md bg-muted/50">
                <div className="flex-1 space-y-1">
                  <Label htmlFor={`new-value-${attr.id}`} className="text-xs">
                    New Value Code
                  </Label>
                  <Input
                    id={`new-value-${attr.id}`}
                    value={newValueCode}
                    onChange={(e) =>
                      setNewValueCode(e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, '_'))
                    }
                    placeholder="e.g., france, germany"
                    className="h-8 text-sm"
                    autoFocus
                  />
                </div>
                <Button
                  type="button"
                  size="sm"
                  onClick={() => addValueMutation.mutate(attr.id)}
                  disabled={!newValueCode || addValueMutation.isPending}
                  className="h-8"
                >
                  {addValueMutation.isPending ? (
                    <Loader2 className="w-3 h-3 animate-spin" />
                  ) : (
                    'Add'
                  )}
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setAddingValueToAttribute(null);
                    setNewValueCode('');
                  }}
                  className="h-8"
                >
                  <X className="w-3 h-3" />
                </Button>
              </div>
            )}
          </div>
        );

      case 'json':
        return (
          <div key={attr.code} className="space-y-2">
            <Label htmlFor={`attr-${attr.code}`} className={typeAttr.required ? 'font-semibold' : ''}>
              {attr.code.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
              {typeAttr.required && <span className="text-red-500 ml-1 text-lg">*</span>}
            </Label>
            <Textarea
              id={`attr-${attr.code}`}
              value={String(value)}
              onChange={(e) => handleAttributeChange(attr.code, e.target.value)}
              placeholder={`Enter JSON for ${attr.code}`}
              rows={4}
            />
            <span className="text-sm text-muted-foreground">Enter valid JSON</span>
          </div>
        );

      default:
        return null;
    }
  };

  if (isLoadingProduct) {
    return (
      <div className="page-container flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!product) {
    return (
      <div className="page-container">
        <div className="text-center py-12">
          <h2 className="text-2xl font-bold">Product not found</h2>
          <Button className="mt-4" onClick={() => navigate('/products')}>
            Back to Products
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <PageHeader
        title={product.code}
        description={`Edit product family ${product.code} and manage its attributes and variants.`}
        breadcrumbs={[
          { label: 'Dashboard', href: '/' },
          { label: 'Products', href: '/products' },
          { label: product.code },
        ]}
        actions={
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => navigate('/products')}>
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Products
            </Button>
            <Button onClick={() => updateAttributesMutation.mutate()} disabled={updateAttributesMutation.isPending}>
              {updateAttributesMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="w-4 h-4 mr-2" />
                  Save Attributes
                </>
              )}
            </Button>
          </div>
        }
      />

      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Product family</CardTitle>
            <CardDescription>Basic details for this product family. It can contain multiple variants.</CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label className="text-sm text-muted-foreground">Code</Label>
              <p className="font-mono">{product.code}</p>
            </div>
            <div>
              <Label className="text-sm text-muted-foreground">Status</Label>
              <p className="capitalize">{product.status}</p>
            </div>
            <div>
              <Label className="text-sm text-muted-foreground">Brand</Label>
              <p>{product.brand || '-'}</p>
            </div>
            <div>
              <Label className="text-sm text-muted-foreground">Model</Label>
              <p>{product.model || '-'}</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Group Attributes</CardTitle>
                <CardDescription>
                  {isLoadingAttributes
                    ? 'Loading attributes...'
                    : `Edit the attributes for this product type. ${productAttributes?.length || 0} attributes currently saved.`}
                </CardDescription>
              </div>
              <Button onClick={() => setIsAddAttributeOpen(true)} variant="outline" size="sm">
                <Plus className="w-4 h-4 mr-2" />
                Add Attribute
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {isLoadingTypeAttributes ? (
              <div className="py-12 text-center text-muted-foreground">
                <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
                Loading attributes...
              </div>
            ) : typeAttributesError ? (
              <div className="py-12 text-center">
                <p className="text-red-500 mb-2">Error loading attributes</p>
                <p className="text-sm text-muted-foreground">
                  {typeAttributesError instanceof Error ? typeAttributesError.message : 'Unknown error'}
                </p>
                <Button onClick={() => refetchTypeAttributes()} variant="outline" size="sm" className="mt-4">
                  Retry
                </Button>
              </div>
            ) : typeAttributes && typeAttributes.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {typeAttributes
                  .filter((ta) => !ta.variant_level)
                  .map((ta) => renderAttributeField(ta))}
              </div>
            ) : (
              <div className="py-12 text-center text-muted-foreground">
                No attributes defined for this product type. Click "Add Attribute" to create one.
              </div>
            )}
          </CardContent>
        </Card>

        {/* Attributes & Values - Read-only overview */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <List className="w-5 h-5" />
              Attributes & Values
            </CardTitle>
            <CardDescription>
              View product and variant attribute values. Product attributes apply to the whole family; variant attributes vary per SKU. Use locale to see translated values.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Product-level attributes */}
            <div>
              <h4 className="font-medium text-sm mb-3">Product attributes</h4>
              {productAttributes && productAttributes.length > 0 ? (
                <div className="border rounded-md overflow-hidden">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Attribute</TableHead>
                        <TableHead>Value</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {productAttributes.map((pa) => {
                        const typeAttr = typeAttributes?.find((ta) => ta.attribute.id === pa.attribute_id);
                        let displayValue = '—';
                        if (pa.value_text !== null) displayValue = String(pa.value_text);
                        else if (pa.value_number !== null) displayValue = String(pa.value_number);
                        else if (pa.value_bool !== null) displayValue = pa.value_bool ? 'Yes' : 'No';
                        else if (pa.attribute_value_id != null) {
                          const av = typeAttr?.attribute.values?.find((v) => v.id === pa.attribute_value_id);
                          displayValue = av?.code ?? `ID: ${pa.attribute_value_id}`;
                        }
                        return (
                          <TableRow key={pa.id}>
                            <TableCell className="font-medium">{pa.attribute_code.replace(/_/g, ' ')}</TableCell>
                            <TableCell>{displayValue}</TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground py-2">No product-level attributes set.</p>
              )}
            </div>

            {/* Variant attributes (with locale for translations) */}
            <div>
              <h4 className="font-medium text-sm mb-3">Variant attributes</h4>
              <div className="flex flex-wrap gap-3 mb-3">
                <div>
                  <Label className="text-xs text-muted-foreground block mb-1">Variant</Label>
                  <Select
                    value={attrsViewVariantId?.toString() ?? '_none'}
                    onValueChange={(v) => setAttrsViewVariantId(v === '_none' ? null : Number(v))}
                  >
                    <SelectTrigger className="w-48">
                      <SelectValue placeholder="Select variant" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="_none">— Select variant —</SelectItem>
                      {variants?.map((v) => (
                        <SelectItem key={v.id} value={v.id.toString()}>
                          {v.sku || v.internal_sku || `Variant ${v.id}`}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="text-xs text-muted-foreground block mb-1">Locale (translations)</Label>
                  <Select
                    value={attrsViewLocaleCode}
                    onValueChange={setAttrsViewLocaleCode}
                  >
                    <SelectTrigger className="w-40">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {locales.map((loc: { id: number; code: string; name?: string }) => (
                        <SelectItem key={loc.id} value={loc.code}>
                          {loc.code}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              {attrsViewVariantId ? (
                isLoadingVariantAttrs ? (
                  <div className="flex items-center gap-2 py-4 text-muted-foreground">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span className="text-sm">Loading attributes…</span>
                  </div>
                ) : variantAttrDetails?.attributes && variantAttrDetails.attributes.length > 0 ? (
                  <div className="border rounded-md overflow-hidden">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Attribute</TableHead>
                          <TableHead>Raw value</TableHead>
                          <TableHead>Translated value</TableHead>
                          <TableHead className="w-24">Source</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {variantAttrDetails.attributes.map((attr) => (
                          <TableRow key={attr.product_attribute_value_id}>
                            <TableCell className="font-medium">{attr.attribute_code.replace(/_/g, ' ')}</TableCell>
                            <TableCell className="text-muted-foreground">{attr.raw_value ?? '—'}</TableCell>
                            <TableCell>{attr.translated_value ?? (attr.raw_value ?? '—')}</TableCell>
                            <TableCell>
                              <Badge variant="outline" className="text-xs font-normal">
                                {attr.source}
                              </Badge>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground py-2">No attributes for this variant.</p>
                )
              ) : (
                <p className="text-sm text-muted-foreground py-2">Select a variant to view its attributes and translated values.</p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Variants Section */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Package className="w-5 h-5" />
                  Variants
                </CardTitle>
                <CardDescription>
                  {isLoadingVariants
                    ? 'Loading variants...'
                    : `Manage the ${variants?.length || 0} variant${(variants?.length || 0) !== 1 ? 's' : ''} in this product family.`}
                </CardDescription>
              </div>
              <Button onClick={() => setShowCreateVariantDialog(true)} size="sm">
                <Plus className="w-4 h-4 mr-2" />
                Add Variant
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {isLoadingVariants ? (
              <div className="py-12 text-center">
                <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2 text-muted-foreground" />
                <p className="text-sm text-muted-foreground">Loading variants...</p>
              </div>
            ) : !variants || variants.length === 0 ? (
              <div className="py-12 text-center text-muted-foreground">
                <Package className="w-12 h-12 mx-auto mb-4 opacity-20" />
                <p className="mb-2">No variants yet</p>
                <p className="text-sm mb-4">Add variants to this product family.</p>
                <Button onClick={() => setShowCreateVariantDialog(true)} variant="outline" size="sm">
                  <Plus className="w-4 h-4 mr-2" />
                  Add First Variant
                </Button>
              </div>
            ) : (
              <div className="border rounded-md overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>SKU</TableHead>
                      <TableHead>Internal SKU</TableHead>
                      <TableHead>Barcode</TableHead>
                      <TableHead>MPN</TableHead>
                      <TableHead>Source Title</TableHead>
                      <TableHead>Source Supplier</TableHead>
                      <TableHead>Axis</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {variants.map((variant) => (
                      <>
                        <TableRow key={variant.id}>
                          <TableCell className="font-mono text-sm">
                            {variant.sku || <span className="text-muted-foreground">—</span>}
                          </TableCell>
                          <TableCell className="font-mono text-sm text-muted-foreground">
                            {variant.internal_sku || <span className="text-muted-foreground">—</span>}
                          </TableCell>
                          <TableCell className="font-mono text-sm">
                            {variant.barcode || <span className="text-muted-foreground">—</span>}
                          </TableCell>
                          <TableCell>{variant.mpn || <span className="text-muted-foreground">—</span>}</TableCell>
                          <TableCell className="max-w-xs truncate">
                            {variant.source_title || <span className="text-muted-foreground">—</span>}
                          </TableCell>
                          <TableCell>{variant.source_supplier || <span className="text-muted-foreground">—</span>}</TableCell>
                          <TableCell className="font-mono text-xs text-muted-foreground max-w-[8rem] truncate" title={variant.axis_signature || undefined}>
                            {variant.axis_signature || '—'}
                          </TableCell>
                          <TableCell className="text-right">
                            <div className="flex items-center justify-end gap-2">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                  setExpandedVariantId(expandedVariantId === variant.id ? null : variant.id);
                                  if (expandedVariantId !== variant.id) setSelectedVariant(variant);
                                }}
                                title="View details"
                              >
                                {expandedVariantId === variant.id ? (
                                  <ChevronUp className="w-4 h-4" />
                                ) : (
                                  <Eye className="w-4 h-4" />
                                )}
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleEditVariant(variant)}
                                title="Edit variant"
                              >
                                <Edit className="w-4 h-4" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleDeleteVariant(variant)}
                                className="text-destructive hover:text-destructive"
                                title="Delete variant"
                              >
                                <Trash2 className="w-4 h-4" />
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                        {expandedVariantId === variant.id && (
                          <TableRow key={`${variant.id}-details`}>
                            <TableCell colSpan={8} className="bg-muted/30 p-6">
                              <div className="space-y-4">
                                <h4 className="font-semibold text-sm mb-3">Variant Details</h4>
                                
                                {/* Basic info */}
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pb-4 border-b">
                                  <div>
                                    <Label className="text-xs text-muted-foreground">Internal SKU</Label>
                                    <p className="text-sm font-mono">{variant.internal_sku}</p>
                                  </div>
                                  <div>
                                    <Label className="text-xs text-muted-foreground">Product ID</Label>
                                    <p className="text-sm">{variant.product_id}</p>
                                  </div>
                                  <div>
                                    <Label className="text-xs text-muted-foreground">Axis signature</Label>
                                    <p className="text-sm font-mono">{variant.axis_signature || '—'}</p>
                                  </div>
                                  <div>
                                    <Label className="text-xs text-muted-foreground">Created</Label>
                                    <p className="text-sm">{variant.created_at ? new Date(variant.created_at).toLocaleDateString() : '—'}</p>
                                  </div>
                                </div>

                                {/* Source data */}
                                {(variant.source_title || variant.source_description || variant.source_sku || variant.source_supplier || variant.source_locale) && (
                                  <div className="space-y-3 pb-4 border-b">
                                    <h5 className="font-medium text-xs text-muted-foreground uppercase tracking-wide">Source Data</h5>
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                      {variant.source_title && (
                                        <div className="md:col-span-2">
                                          <Label className="text-xs text-muted-foreground">Source Title</Label>
                                          <p className="text-sm">{variant.source_title}</p>
                                        </div>
                                      )}
                                      {variant.source_description && (
                                        <div className="md:col-span-2">
                                          <Label className="text-xs text-muted-foreground">Source Description</Label>
                                          <p className="text-sm text-muted-foreground">{variant.source_description}</p>
                                        </div>
                                      )}
                                      {variant.source_sku && (
                                        <div>
                                          <Label className="text-xs text-muted-foreground">Source SKU</Label>
                                          <p className="text-sm font-mono">{variant.source_sku}</p>
                                        </div>
                                      )}
                                      {variant.source_supplier && (
                                        <div>
                                          <Label className="text-xs text-muted-foreground">Source Supplier</Label>
                                          <p className="text-sm">{variant.source_supplier}</p>
                                        </div>
                                      )}
                                      {variant.source_locale && (
                                        <div>
                                          <Label className="text-xs text-muted-foreground">Source Locale</Label>
                                          <p className="text-sm">{variant.source_locale}</p>
                                        </div>
                                      )}
                                    </div>
                                  </div>
                                )}

                                {/* Variant attributes */}
                                {expandedVariantAttributes && expandedVariantAttributes.length > 0 && (
                                  <div className="space-y-3">
                                    <h5 className="font-medium text-xs text-muted-foreground uppercase tracking-wide">Variant Attributes</h5>
                                    <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                                      {expandedVariantAttributes.map((attr) => {
                                        let displayValue = '—';
                                        if (attr.value_text !== null) displayValue = attr.value_text;
                                        else if (attr.value_number !== null) displayValue = String(attr.value_number);
                                        else if (attr.value_bool !== null) displayValue = attr.value_bool ? 'Yes' : 'No';
                                        else if (attr.attribute_value_id !== null) {
                                          const typeAttr = variantLevelAttributes.find(ta => ta.attribute.id === attr.attribute_id);
                                          const attrValue = typeAttr?.attribute.values?.find(v => v.id === attr.attribute_value_id);
                                          displayValue = attrValue?.code || `ID: ${attr.attribute_value_id}`;
                                        }
                                        
                                        return (
                                          <div key={attr.id}>
                                            <Label className="text-xs text-muted-foreground capitalize">
                                              {attr.attribute_code.replace(/_/g, ' ')}
                                            </Label>
                                            <p className="text-sm font-medium">{displayValue}</p>
                                          </div>
                                        );
                                      })}
                                    </div>
                                  </div>
                                )}

                                {(!expandedVariantAttributes || expandedVariantAttributes.length === 0) && (
                                  <p className="text-sm text-muted-foreground py-2">No variant-level attributes set.</p>
                                )}
                              </div>
                            </TableCell>
                          </TableRow>
                        )}
                      </>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Saved hook terms (for title generation) */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Tag className="w-5 h-5" />
              Saved hook terms
            </CardTitle>
            <CardDescription>
              Hook terms approved for this product (used in title generation). Add or remove terms from Keywords → run → Product maps → Extract terms.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-4 mb-3">
              <Label className="text-sm whitespace-nowrap">Locale</Label>
              <Select
                value={hookTermsLocaleId?.toString() ?? ''}
                onValueChange={(v) => setHookTermsLocaleId(v ? Number(v) : null)}
              >
                <SelectTrigger className="w-48">
                  <SelectValue placeholder="Select locale" />
                </SelectTrigger>
                <SelectContent>
                  {locales.map((loc: { id: number; code: string; name?: string }) => (
                    <SelectItem key={loc.id} value={loc.id.toString()}>
                      {loc.code} {loc.name ? `(${loc.name})` : ''}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {savedHookData?.terms && savedHookData.terms.length > 0 ? (
              <ul className="space-y-2 rounded-md border p-3">
                {savedHookData.terms.map((item: HookTermItem) => (
                  <li key={item.id} className="flex items-center justify-between gap-2 text-sm">
                    <span className="font-medium">{item.term}</span>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 w-7 p-0 text-muted-foreground hover:text-destructive"
                      title="Remove hook term"
                      onClick={() => removeHookTermMutation.mutate({ hookTermId: item.id })}
                      disabled={removeHookTermMutation.isPending}
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted-foreground py-2">
                No saved hook terms for this product and locale. Go to Keywords → open a planner run → Product maps → Extract terms, then approve hook terms to save them here.
              </p>
            )}
          </CardContent>
        </Card>

        {/* Keyword Mappings */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Tag className="w-5 h-5" />
                  Keyword Mappings
                </CardTitle>
                <CardDescription>
                  Keywords mapped to this product for title generation
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {/* Run selector dropdown */}
              <div className="flex items-center gap-4">
                <Label htmlFor="planner-run-select" className="whitespace-nowrap">Select Planner Run:</Label>
                <Select 
                  value={selectedRunId?.toString() || ''} 
                  onValueChange={(v) => setSelectedRunId(v ? Number(v) : null)}
                >
                  <SelectTrigger id="planner-run-select" className="w-64">
                    <SelectValue placeholder="Select a planner run" />
                  </SelectTrigger>
                  <SelectContent>
                    {plannerRunsData?.results && plannerRunsData.results.length > 0 ? (
                      plannerRunsData.results.map((run: any) => (
                        <SelectItem key={run.id} value={run.id.toString()}>
                          Run #{run.id} - {run.locale_code} {run.status}
                        </SelectItem>
                      ))
                    ) : (
                      <SelectItem value="no-runs" disabled>
                        No planner runs available
                      </SelectItem>
                    )}
                  </SelectContent>
                </Select>
              </div>

              {/* Loading state */}
              {keywordMapsLoading && (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
                </div>
              )}

              {/* No run selected */}
              {!selectedRunId && !keywordMapsLoading && (
                <div className="text-center py-8 text-muted-foreground">
                  <Tag className="w-12 h-12 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">Select a planner run to view keyword mappings</p>
                </div>
              )}

              {/* No mappings found */}
              {selectedRunId && !keywordMapsLoading && (!keywordMapsData?.results || keywordMapsData.results.length === 0) && (
                <div className="text-center py-8 text-muted-foreground">
                  <Tag className="w-12 h-12 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">No keyword mappings found for this product in the selected run</p>
                  <p className="text-xs mt-2">Run "Map to Products (AI)" on the Keywords Mappings page to create mappings</p>
                </div>
              )}

              {/* Results table */}
              {selectedRunId && !keywordMapsLoading && keywordMapsData?.results && keywordMapsData.results.length > 0 && (
                <div className="rounded-md border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Keyword</TableHead>
                        <TableHead>Source</TableHead>
                        <TableHead>Match Type</TableHead>
                        <TableHead>Matched Text</TableHead>
                        <TableHead className="text-right">Confidence</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {keywordMapsData.results.map((map: ProductKeywordMap) => (
                        <TableRow key={map.id}>
                          <TableCell className="font-medium">{map.keyword_term}</TableCell>
                          <TableCell>
                            <Badge variant="secondary">{map.source}</Badge>
                          </TableCell>
                          <TableCell className="text-sm">{map.match_kind || '-'}</TableCell>
                          <TableCell className="text-sm text-muted-foreground">
                            {map.matched_text || map.attribute_value_label || '-'}
                          </TableCell>
                          <TableCell className="text-right">
                            {map.confidence ? (
                              <span className="text-sm font-medium">
                                {(map.confidence * 100).toFixed(1)}%
                              </span>
                            ) : (
                              <span className="text-muted-foreground">—</span>
                            )}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                  {keywordMapsData.count > keywordMapsData.results.length && (
                    <div className="px-4 py-3 text-sm text-muted-foreground border-t">
                      Showing {keywordMapsData.results.length} of {keywordMapsData.count} mappings
                    </div>
                  )}
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Available Attributes (Not Linked) */}
        {unlinkedAttributes.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>Available Attributes</CardTitle>
              <CardDescription>
                These attributes exist but are not linked to this product type. Click "Link" to add them.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {unlinkedAttributes.map((attr) => (
                  <div
                    key={attr.id}
                    className="flex items-center justify-between p-3 border rounded-md hover:bg-muted/50 transition-colors"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-sm truncate">{attr.code}</div>
                      <div className="text-xs text-muted-foreground capitalize">{attr.data_type}</div>
                      {attr.unit && <div className="text-xs text-muted-foreground">Unit: {attr.unit}</div>}
                    </div>
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      onClick={() => linkAttributeMutation.mutate(attr.id)}
                      disabled={linkAttributeMutation.isPending}
                      className="ml-2 shrink-0"
                    >
                      {linkAttributeMutation.isPending ? (
                        <Loader2 className="w-3 h-3 animate-spin" />
                      ) : (
                        <>
                          <Plus className="w-3 h-3 mr-1" />
                          Link
                        </>
                      )}
                    </Button>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Add Attribute Dialog */}
        <Dialog open={isAddAttributeOpen} onOpenChange={setIsAddAttributeOpen}>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Add New Attribute</DialogTitle>
              <DialogDescription>
                Create a new attribute and associate it with this product type.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="attr-code">
                  Attribute Code <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="attr-code"
                  value={newAttribute.code}
                  onChange={(e) =>
                    setNewAttribute((prev) => ({
                      ...prev,
                      code: e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, '_'),
                    }))
                  }
                  placeholder="e.g., material_type, weight_kg"
                />
                <p className="text-xs text-muted-foreground">
                  Use lowercase letters, numbers, and underscores only (e.g., material_type)
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="attr-data-type">
                  Data Type <span className="text-red-500">*</span>
                </Label>
                <Select
                  value={newAttribute.data_type}
                  onValueChange={(value: 'text' | 'number' | 'bool' | 'enum' | 'json') =>
                    setNewAttribute((prev) => ({ ...prev, data_type: value }))
                  }
                >
                  <SelectTrigger id="attr-data-type">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="text">Text</SelectItem>
                    <SelectItem value="number">Number</SelectItem>
                    <SelectItem value="bool">Boolean (Yes/No)</SelectItem>
                    <SelectItem value="enum">Enum (Select from list)</SelectItem>
                    <SelectItem value="json">JSON</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="attr-unit">Unit (optional)</Label>
                <Input
                  id="attr-unit"
                  value={newAttribute.unit || ''}
                  onChange={(e) => setNewAttribute((prev) => ({ ...prev, unit: e.target.value }))}
                  placeholder="e.g., kg, cm, m²"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="attr-required"
                    checked={newAttribute.required}
                    onCheckedChange={(checked) =>
                      setNewAttribute((prev) => ({ ...prev, required: Boolean(checked) }))
                    }
                  />
                  <Label htmlFor="attr-required" className="cursor-pointer">
                    Required
                  </Label>
                </div>

                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="attr-filterable"
                    checked={newAttribute.filterable}
                    onCheckedChange={(checked) =>
                      setNewAttribute((prev) => ({ ...prev, filterable: Boolean(checked) }))
                    }
                  />
                  <Label htmlFor="attr-filterable" className="cursor-pointer">
                    Filterable
                  </Label>
                </div>

                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="attr-variant-level"
                    checked={newAttribute.variant_level}
                    onCheckedChange={(checked) =>
                      setNewAttribute((prev) => ({ ...prev, variant_level: Boolean(checked) }))
                    }
                  />
                  <Label htmlFor="attr-variant-level" className="cursor-pointer">
                    Variant Level
                  </Label>
                </div>

                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="attr-translatable"
                    checked={newAttribute.is_value_translatable}
                    onCheckedChange={(checked) =>
                      setNewAttribute((prev) => ({ ...prev, is_value_translatable: Boolean(checked) }))
                    }
                  />
                  <Label htmlFor="attr-translatable" className="cursor-pointer">
                    Translatable
                  </Label>
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsAddAttributeOpen(false)}>
                Cancel
              </Button>
              <Button
                onClick={() => createAttributeMutation.mutate()}
                disabled={!newAttribute.code || createAttributeMutation.isPending}
              >
                {createAttributeMutation.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>
                    <Plus className="w-4 h-4 mr-2" />
                    Create Attribute
                  </>
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Create Variant Dialog */}
        <Dialog open={showCreateVariantDialog} onOpenChange={setShowCreateVariantDialog}>
          <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Create New Variant</DialogTitle>
              <DialogDescription>
                Add a new variant to this product family. Fill in the variant details and attributes.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-6 py-4">
              {/* Basic variant fields */}
              <div className="space-y-4">
                <h4 className="font-semibold text-sm">Basic Information</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="variant-sku">SKU</Label>
                    <Input
                      id="variant-sku"
                      value={variantForm.sku || ''}
                      onChange={(e) => setVariantForm((prev) => ({ ...prev, sku: e.target.value || null }))}
                      placeholder="e.g., BIKE-RED-SM"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="variant-barcode">Barcode</Label>
                    <Input
                      id="variant-barcode"
                      value={variantForm.barcode || ''}
                      onChange={(e) => setVariantForm((prev) => ({ ...prev, barcode: e.target.value || null }))}
                      placeholder="e.g., 123456789012"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="variant-mpn">MPN (Manufacturer Part Number)</Label>
                    <Input
                      id="variant-mpn"
                      value={variantForm.mpn || ''}
                      onChange={(e) => setVariantForm((prev) => ({ ...prev, mpn: e.target.value || null }))}
                      placeholder="e.g., MFG-12345"
                    />
                  </div>
                </div>
              </div>

              {/* Source data fields */}
              <div className="space-y-4">
                <h4 className="font-semibold text-sm">Source Data (from import/supplier)</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2 md:col-span-2">
                    <Label htmlFor="variant-source-title">Source Title</Label>
                    <Input
                      id="variant-source-title"
                      value={variantForm.source_title || ''}
                      onChange={(e) => setVariantForm((prev) => ({ ...prev, source_title: e.target.value }))}
                      placeholder="Original title from supplier"
                    />
                  </div>
                  <div className="space-y-2 md:col-span-2">
                    <Label htmlFor="variant-source-description">Source Description</Label>
                    <Textarea
                      id="variant-source-description"
                      value={variantForm.source_description || ''}
                      onChange={(e) => setVariantForm((prev) => ({ ...prev, source_description: e.target.value }))}
                      placeholder="Original description from supplier"
                      rows={3}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="variant-source-sku">Source SKU</Label>
                    <Input
                      id="variant-source-sku"
                      value={variantForm.source_sku || ''}
                      onChange={(e) => setVariantForm((prev) => ({ ...prev, source_sku: e.target.value }))}
                      placeholder="Supplier's SKU"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="variant-source-supplier">Source Supplier</Label>
                    <Input
                      id="variant-source-supplier"
                      value={variantForm.source_supplier || ''}
                      onChange={(e) => setVariantForm((prev) => ({ ...prev, source_supplier: e.target.value }))}
                      placeholder="Supplier name"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="variant-source-locale">Source Locale</Label>
                    <Input
                      id="variant-source-locale"
                      value={variantForm.source_locale || ''}
                      onChange={(e) => setVariantForm((prev) => ({ ...prev, source_locale: e.target.value }))}
                      placeholder="e.g., en, fr"
                    />
                  </div>
                </div>
              </div>

              {/* Variant-level attributes */}
              {variantLevelAttributes.length > 0 && (
                <div className="space-y-4">
                  <h4 className="font-semibold text-sm">Variant Attributes (specific to this variant)</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {variantLevelAttributes.map((ta) => renderVariantAttributeField(ta))}
                  </div>
                </div>
              )}
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowCreateVariantDialog(false)}>
                Cancel
              </Button>
              <Button onClick={() => createVariantMutation.mutate()} disabled={createVariantMutation.isPending}>
                {createVariantMutation.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>
                    <Plus className="w-4 h-4 mr-2" />
                    Create Variant
                  </>
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Edit Variant Dialog */}
        <Dialog open={showEditVariantDialog} onOpenChange={setShowEditVariantDialog}>
          <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Edit Variant</DialogTitle>
              <DialogDescription>
                Update variant details and attributes. SKU: {selectedVariant?.sku || selectedVariant?.id}
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-6 py-4">
              {/* Basic variant fields */}
              <div className="space-y-4">
                <h4 className="font-semibold text-sm">Basic Information</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="edit-variant-sku">SKU</Label>
                    <Input
                      id="edit-variant-sku"
                      value={variantForm.sku || ''}
                      onChange={(e) => setVariantForm((prev) => ({ ...prev, sku: e.target.value || null }))}
                      placeholder="e.g., BIKE-RED-SM"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="edit-variant-barcode">Barcode</Label>
                    <Input
                      id="edit-variant-barcode"
                      value={variantForm.barcode || ''}
                      onChange={(e) => setVariantForm((prev) => ({ ...prev, barcode: e.target.value || null }))}
                      placeholder="e.g., 123456789012"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="edit-variant-mpn">MPN (Manufacturer Part Number)</Label>
                    <Input
                      id="edit-variant-mpn"
                      value={variantForm.mpn || ''}
                      onChange={(e) => setVariantForm((prev) => ({ ...prev, mpn: e.target.value || null }))}
                      placeholder="e.g., MFG-12345"
                    />
                  </div>
                </div>
              </div>

              {/* Source data fields */}
              <div className="space-y-4">
                <h4 className="font-semibold text-sm">Source Data (from import/supplier)</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2 md:col-span-2">
                    <Label htmlFor="edit-variant-source-title">Source Title</Label>
                    <Input
                      id="edit-variant-source-title"
                      value={variantForm.source_title || ''}
                      onChange={(e) => setVariantForm((prev) => ({ ...prev, source_title: e.target.value }))}
                      placeholder="Original title from supplier"
                    />
                  </div>
                  <div className="space-y-2 md:col-span-2">
                    <Label htmlFor="edit-variant-source-description">Source Description</Label>
                    <Textarea
                      id="edit-variant-source-description"
                      value={variantForm.source_description || ''}
                      onChange={(e) => setVariantForm((prev) => ({ ...prev, source_description: e.target.value }))}
                      placeholder="Original description from supplier"
                      rows={3}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="edit-variant-source-sku">Source SKU</Label>
                    <Input
                      id="edit-variant-source-sku"
                      value={variantForm.source_sku || ''}
                      onChange={(e) => setVariantForm((prev) => ({ ...prev, source_sku: e.target.value }))}
                      placeholder="Supplier's SKU"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="edit-variant-source-supplier">Source Supplier</Label>
                    <Input
                      id="edit-variant-source-supplier"
                      value={variantForm.source_supplier || ''}
                      onChange={(e) => setVariantForm((prev) => ({ ...prev, source_supplier: e.target.value }))}
                      placeholder="Supplier name"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="edit-variant-source-locale">Source Locale</Label>
                    <Input
                      id="edit-variant-source-locale"
                      value={variantForm.source_locale || ''}
                      onChange={(e) => setVariantForm((prev) => ({ ...prev, source_locale: e.target.value }))}
                      placeholder="e.g., en, fr"
                    />
                  </div>
                </div>
              </div>

              {/* Variant-level attributes */}
              {variantLevelAttributes.length > 0 && (
                <div className="space-y-4">
                  <h4 className="font-semibold text-sm">Variant Attributes (specific to this variant)</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {variantLevelAttributes.map((ta) => renderVariantAttributeField(ta))}
                  </div>
                </div>
              )}
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowEditVariantDialog(false)}>
                Cancel
              </Button>
              <Button onClick={() => updateVariantMutation.mutate()} disabled={updateVariantMutation.isPending}>
                {updateVariantMutation.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save className="w-4 h-4 mr-2" />
                    Save Changes
                  </>
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Delete Variant Confirmation */}
        <AlertDialog open={showDeleteVariantDialog} onOpenChange={setShowDeleteVariantDialog}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Delete Variant?</AlertDialogTitle>
              <AlertDialogDescription>
                Are you sure you want to delete variant <strong>{selectedVariant?.sku || `#${selectedVariant?.id}`}</strong>?
                This action cannot be undone.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction
                onClick={() => deleteVariantMutation.mutate()}
                disabled={deleteVariantMutation.isPending}
                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              >
                {deleteVariantMutation.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Deleting...
                  </>
                ) : (
                  'Delete Variant'
                )}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </div>
  );
}
