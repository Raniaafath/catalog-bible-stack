import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Plus, Trash2, Upload, Loader2 } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
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
  createProduct,
  createVariant,
  getProductTypes,
  getProductTypeAttributes,
  createProductType,
  ProductCreate,
  ProductStatus,
  ProductTypeAttribute,
  VariantCreate,
  ProductTypeCreate,
} from '@/lib/api';

type VariantDraft = {
  sku: string;
  barcode: string;
  mpn: string;
  source_title: string;
  source_description: string;
  source_locale: string;
  source_supplier: string;
  source_sku: string;
};

const statusOptions: Array<{ value: ProductStatus; label: string }> = [
  { value: 'draft', label: 'Draft' },
  { value: 'active', label: 'Active' },
  { value: 'discontinued', label: 'Discontinued' },
];

export default function ProductNew() {
  const navigate = useNavigate();
  const { toast } = useToast();

  const [productTypeId, setProductTypeId] = useState('');
  const [code, setCode] = useState('');
  const [status, setStatus] = useState<ProductStatus>('draft');
  const [defaultLabel, setDefaultLabel] = useState('');
  const [brand, setBrand] = useState('');
  const [model, setModel] = useState('');
  const [series, setSeries] = useState('');
  const [variants, setVariants] = useState<VariantDraft[]>([{ 
    sku: '', 
    barcode: '', 
    mpn: '',
    source_title: '',
    source_description: '',
    source_locale: '',
    source_supplier: '',
    source_sku: '',
  }]);
  const [attributes, setAttributes] = useState<Record<string, string | number | boolean>>({});
  const [showCreateTypeDialog, setShowCreateTypeDialog] = useState(false);
  const [newTypeCode, setNewTypeCode] = useState('');
  const [newTypeLabel, setNewTypeLabel] = useState('');

  const { data: productTypes, refetch: refetchProductTypes } = useQuery({
    queryKey: ['product-types'],
    queryFn: getProductTypes,
  });

  const createTypeMutation = useMutation({
    mutationFn: (data: ProductTypeCreate) => createProductType(data),
    onSuccess: (newType) => {
      toast({
        title: 'Product Type Created',
        description: `Product type "${newType.code}" has been created.`,
      });
      setProductTypeId(String(newType.id));
      setShowCreateTypeDialog(false);
      setNewTypeCode('');
      setNewTypeLabel('');
      refetchProductTypes();
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to create product type',
        description: error.response?.data?.detail || error.message || 'Something went wrong.',
        variant: 'destructive',
      });
    },
  });

  const { data: typeAttributes, isLoading: isLoadingAttributes } = useQuery({
    queryKey: ['product-type-attributes', productTypeId],
    queryFn: () => getProductTypeAttributes(Number(productTypeId)),
    enabled: !!productTypeId && productTypeId !== '',
  });

  // Reset attributes when product type changes
  useEffect(() => {
    setAttributes({});
  }, [productTypeId]);

  const createMutation = useMutation({
    mutationFn: async () => {
      const payload: ProductCreate = {
        product_type_id: Number(productTypeId),
        code: code.trim(),
        status,
        default_label: defaultLabel.trim(),
        brand: brand.trim() || null,
        model: model.trim() || null,
        series: series.trim() || null,
        attributes: Object.keys(attributes).length > 0 ? attributes : undefined,
      };

      const product = await createProduct(payload);

      const trimmedVariants = variants
        .map((variant) => ({
          sku: variant.sku.trim(),
          barcode: variant.barcode.trim(),
          mpn: variant.mpn.trim(),
          source_title: variant.source_title.trim(),
          source_description: variant.source_description.trim(),
          source_locale: variant.source_locale.trim(),
          source_supplier: variant.source_supplier.trim(),
          source_sku: variant.source_sku.trim(),
        }))
        .filter((variant) => variant.sku || variant.barcode || variant.mpn);

      const variantsToCreate =
        trimmedVariants.length > 0
          ? trimmedVariants
          : [
              {
                sku: product.code,
                barcode: '',
                mpn: '',
                source_title: '',
                source_description: '',
                source_locale: '',
                source_supplier: '',
                source_sku: '',
              },
            ];

      for (const variant of variantsToCreate) {
        const variantPayload: VariantCreate = {
          product_id: product.id,
          sku: variant.sku || null,
          barcode: variant.barcode || null,
          mpn: variant.mpn || null,
          source_title: variant.source_title || null,
          source_description: variant.source_description || null,
          source_locale: variant.source_locale || null,
          source_supplier: variant.source_supplier || null,
          source_sku: variant.source_sku || null,
        };
        await createVariant(variantPayload);
      }

      return product;
    },
    onSuccess: (product) => {
      toast({
        title: 'Product created',
        description: `Product ${product.code} is ready.`,
      });
      navigate('/products');
    },
    onError: (error) => {
      toast({
        title: 'Failed to create group',
        description: error instanceof Error ? error.message : 'Something went wrong.',
        variant: 'destructive',
      });
    },
  });

  const canSubmit = useMemo(() => {
    if (!productTypeId || code.trim().length === 0) {
      return false;
    }

    // Check required attributes
    if (typeAttributes) {
      const requiredAttrs = typeAttributes.filter((ta) => ta.required && !ta.variant_level);
      for (const ta of requiredAttrs) {
        const value = attributes[ta.attribute.code];
        if (value === undefined || value === null || value === '') {
          return false;
        }
      }
    }

    return true;
  }, [productTypeId, code, attributes, typeAttributes]);

  const handleAddVariant = () => {
    setVariants((prev) => [...prev, { 
      sku: '', 
      barcode: '', 
      mpn: '',
      source_title: '',
      source_description: '',
      source_locale: '',
      source_supplier: '',
      source_sku: '',
    }]);
  };

  const handleRemoveVariant = (index: number) => {
    setVariants((prev) => prev.filter((_, idx) => idx !== index));
  };

  const handleVariantChange = (index: number, key: keyof VariantDraft, value: string) => {
    setVariants((prev) =>
      prev.map((variant, idx) => (idx === index ? { ...variant, [key]: value } : variant))
    );
  };

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!canSubmit || createMutation.isPending) {
      return;
    }
    createMutation.mutate();
  };

  const handleAttributeChange = (attrCode: string, value: string | number | boolean) => {
    setAttributes((prev) => ({
      ...prev,
      [attrCode]: value,
    }));
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
              placeholder={typeAttr.required ? `Requis: ${attr.code}` : `Enter ${attr.code}`}
              rows={3}
              className={typeAttr.required && !value ? 'border-red-300' : ''}
            />
            {attr.unit && <span className="text-sm text-muted-foreground">Unit: {attr.unit}</span>}
            {typeAttr.required && !value && (
              <span className="text-xs text-red-500">Ce champ est obligatoire</span>
            )}
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
              placeholder={typeAttr.required ? `Requis: ${attr.code}` : `Enter ${attr.code}`}
              className={typeAttr.required && !value ? 'border-red-300' : ''}
            />
            {attr.unit && <span className="text-sm text-muted-foreground">Unité: {attr.unit}</span>}
            {typeAttr.required && !value && (
              <span className="text-xs text-red-500">Ce champ est obligatoire</span>
            )}
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
              {typeAttr.required && <span className="text-red-500 ml-1">*</span>}
            </Label>
          </div>
        );

      case 'enum':
        return (
          <div key={attr.code} className="space-y-2">
            <Label htmlFor={`attr-${attr.code}`} className={typeAttr.required ? 'font-semibold' : ''}>
              {attr.code.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
              {typeAttr.required && <span className="text-red-500 ml-1 text-lg">*</span>}
            </Label>
            <Select value={String(value)} onValueChange={(val) => handleAttributeChange(attr.code, parseInt(val))}>
              <SelectTrigger id={`attr-${attr.code}`} className={typeAttr.required && !value ? 'border-red-300' : ''}>
                <SelectValue placeholder={typeAttr.required ? `Requis: Sélectionner ${attr.code}...` : `Sélectionner ${attr.code}...`} />
              </SelectTrigger>
              <SelectContent>
                {attr.values?.map((v) => (
                  <SelectItem key={v.id} value={String(v.id)}>
                    {v.code}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {typeAttr.required && !value && (
              <span className="text-xs text-red-500">Ce champ est obligatoire</span>
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
              placeholder={typeAttr.required ? `Requis: JSON valide` : `Entrer JSON valide`}
              rows={4}
              className={typeAttr.required && !value ? 'border-red-300' : ''}
            />
            <span className="text-sm text-muted-foreground">Entrer du JSON valide</span>
            {typeAttr.required && !value && (
              <span className="text-xs text-red-500">Ce champ est obligatoire</span>
            )}
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="page-container">
      <PageHeader
        title="Add Product Group"
        description="Create a product group manually. Groups contain multiple variants and can be linked to marketplaces."
        breadcrumbs={[
          { label: 'Dashboard', href: '/' },
          { label: 'Groups', href: '/products' },
          { label: 'Add Group' },
        ]}
        actions={
          <Button variant="outline" onClick={() => navigate('/imports/new')}>
            <Upload className="w-4 h-4 mr-2" />
            Import Products
          </Button>
        }
      />

      <form onSubmit={handleSubmit} className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Group Details</CardTitle>
            <CardDescription>Define the core group information. This group will contain variants.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="productType">Product Type</Label>
                <div className="flex gap-2">
                  <Select value={productTypeId} onValueChange={setProductTypeId} className="flex-1">
                    <SelectTrigger id="productType">
                      <SelectValue placeholder="Select a product type..." />
                    </SelectTrigger>
                    <SelectContent>
                      {productTypes?.results?.map((type) => (
                        <SelectItem key={type.id} value={String(type.id)}>
                          {type.category_path || type.default_label || type.code}
                        </SelectItem>
                      ))}
                      {(!productTypes || productTypes.results.length === 0) && (
                        <SelectItem value="__empty__" disabled>
                          No product types available
                        </SelectItem>
                      )}
                    </SelectContent>
                  </Select>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => setShowCreateTypeDialog(true)}
                    title="Create new product type"
                  >
                    <Plus className="w-4 h-4" />
                  </Button>
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="code">Product Code</Label>
                <Input
                  id="code"
                  value={code}
                  onChange={(event) => setCode(event.target.value)}
                  placeholder="e.g. PROD-001"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="status">Status</Label>
                <Select value={status} onValueChange={(value) => setStatus(value as ProductStatus)}>
                  <SelectTrigger id="status">
                    <SelectValue placeholder="Select status..." />
                  </SelectTrigger>
                  <SelectContent>
                    {statusOptions.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="defaultLabel">Default Label</Label>
                <Input
                  id="defaultLabel"
                  value={defaultLabel}
                  onChange={(event) => setDefaultLabel(event.target.value)}
                  placeholder="Optional display label"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label htmlFor="brand">Brand</Label>
                <Input id="brand" value={brand} onChange={(event) => setBrand(event.target.value)} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="model">Model</Label>
                <Input id="model" value={model} onChange={(event) => setModel(event.target.value)} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="series">Series</Label>
                <Input id="series" value={series} onChange={(event) => setSeries(event.target.value)} />
              </div>
            </div>
          </CardContent>
        </Card>


        {productTypeId && typeAttributes && typeAttributes.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>Product Attributes</CardTitle>
              <CardDescription>
                {isLoadingAttributes
                  ? 'Loading attributes...'
                  : `Fill in the specific attributes for this product type.`}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {typeAttributes
                  .filter((ta) => !ta.variant_level)
                  .map((ta) => renderAttributeField(ta))}
              </div>
              {typeAttributes.filter((ta) => !ta.variant_level).length === 0 && (
                <p className="text-sm text-muted-foreground">No product-level attributes defined for this type.</p>
              )}
            </CardContent>
          </Card>
        )}

        <Card>
          <CardHeader>
            <CardTitle>Variants</CardTitle>
            <CardDescription>Add one or more variants for this product. Source fields are variant-specific.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {variants.map((variant, index) => (
              <div key={index} className="space-y-4 p-4 border rounded-lg">
                <div className="flex items-center justify-between mb-4">
                  <h4 className="font-medium">Variant {index + 1}</h4>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    disabled={variants.length === 1}
                    onClick={() => handleRemoveVariant(index)}
                  >
                    <Trash2 className="w-4 h-4 mr-2" />
                    Remove
                  </Button>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor={`variant-sku-${index}`}>SKU *</Label>
                    <Input
                      id={`variant-sku-${index}`}
                      value={variant.sku}
                      onChange={(event) => handleVariantChange(index, 'sku', event.target.value)}
                      placeholder="Variant SKU"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor={`variant-barcode-${index}`}>Barcode</Label>
                    <Input
                      id={`variant-barcode-${index}`}
                      value={variant.barcode}
                      onChange={(event) => handleVariantChange(index, 'barcode', event.target.value)}
                      placeholder="EAN/GTIN"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor={`variant-mpn-${index}`}>MPN</Label>
                    <Input
                      id={`variant-mpn-${index}`}
                      value={variant.mpn}
                      onChange={(event) => handleVariantChange(index, 'mpn', event.target.value)}
                      placeholder="Manufacturer Part Number"
                    />
                  </div>
                </div>

                <div className="border-t pt-4">
                  <h5 className="text-sm font-medium mb-3 text-muted-foreground">Source Fields (Optional)</h5>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor={`variant-source-title-${index}`}>Source Title</Label>
                      <Input
                        id={`variant-source-title-${index}`}
                        value={variant.source_title}
                        onChange={(event) => handleVariantChange(index, 'source_title', event.target.value)}
                        placeholder="Title from source"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor={`variant-source-locale-${index}`}>Source Locale</Label>
                      <Input
                        id={`variant-source-locale-${index}`}
                        value={variant.source_locale}
                        onChange={(event) => handleVariantChange(index, 'source_locale', event.target.value)}
                        placeholder="e.g. fr, en-US"
                      />
                    </div>
                    <div className="space-y-2 md:col-span-2">
                      <Label htmlFor={`variant-source-description-${index}`}>Source Description</Label>
                      <Textarea
                        id={`variant-source-description-${index}`}
                        value={variant.source_description}
                        onChange={(event) => handleVariantChange(index, 'source_description', event.target.value)}
                        placeholder="Description from source"
                        rows={2}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor={`variant-source-supplier-${index}`}>Source Supplier</Label>
                      <Input
                        id={`variant-source-supplier-${index}`}
                        value={variant.source_supplier}
                        onChange={(event) => handleVariantChange(index, 'source_supplier', event.target.value)}
                        placeholder="Supplier name"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor={`variant-source-sku-${index}`}>Source SKU</Label>
                      <Input
                        id={`variant-source-sku-${index}`}
                        value={variant.source_sku}
                        onChange={(event) => handleVariantChange(index, 'source_sku', event.target.value)}
                        placeholder="SKU from source"
                      />
                    </div>
                  </div>
                </div>
              </div>
            ))}

            <Button type="button" variant="outline" onClick={handleAddVariant}>
              <Plus className="w-4 h-4 mr-2" />
              Add Variant
            </Button>
          </CardContent>
        </Card>

        <div className="flex justify-end gap-3">
          <Button type="button" variant="outline" onClick={() => navigate('/products')}>
            Cancel
          </Button>
          <Button type="submit" disabled={!canSubmit || createMutation.isPending}>
            {createMutation.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
            Create Product
          </Button>
        </div>
      </form>

      {/* Create Product Type Dialog */}
      <Dialog open={showCreateTypeDialog} onOpenChange={setShowCreateTypeDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create New Product Type</DialogTitle>
            <DialogDescription>
              Create a new product category/type. The code will be used as a unique identifier.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="newTypeCode">Code *</Label>
              <Input
                id="newTypeCode"
                value={newTypeCode}
                onChange={(e) => setNewTypeCode(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '-'))}
                placeholder="e.g., electronics, clothing, furniture"
              />
              <p className="text-xs text-muted-foreground">
                Lowercase letters, numbers, and hyphens only. Used as unique identifier.
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="newTypeLabel">Label</Label>
              <Input
                id="newTypeLabel"
                value={newTypeLabel}
                onChange={(e) => setNewTypeLabel(e.target.value)}
                placeholder="e.g., Electronics, Clothing, Furniture"
              />
              <p className="text-xs text-muted-foreground">
                Display name for this product type (optional).
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setShowCreateTypeDialog(false);
                setNewTypeCode('');
                setNewTypeLabel('');
              }}
            >
              Cancel
            </Button>
            <Button
              onClick={() => {
                if (newTypeCode.trim()) {
                  createTypeMutation.mutate({
                    code: newTypeCode.trim(),
                    default_label: newTypeLabel.trim() || newTypeCode.trim(),
                    is_active: true,
                  });
                }
              }}
              disabled={!newTypeCode.trim() || createTypeMutation.isPending}
            >
              {createTypeMutation.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
              Create Type
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
