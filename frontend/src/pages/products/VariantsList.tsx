import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Package, Users, Upload, Unlink, Loader2, Filter } from 'lucide-react';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { DataTable, Column } from '@/components/DataTable';
import { getVariants, getProductTypes, ungroupVariants, Variant, ProductType } from '@/lib/api';
import { GroupingDialog } from '@/components/GroupingDialog';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/hooks/use-toast';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

type FilterStatus = 'all' | 'grouped' | 'ungrouped';

// Helper to check if a variant is in a placeholder (ungrouped) product
function isVariantUngrouped(variant: Variant): boolean {
  const productCode = variant.product?.code || '';
  return productCode.startsWith('variant-') || 
         productCode.startsWith('placeholder-') ||
         productCode.includes(variant.sku || '');
}

export default function VariantsList() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [showGroupingDialog, setShowGroupingDialog] = useState(false);
  const [filterStatus, setFilterStatus] = useState<FilterStatus>('all');

  const { data: variants, isLoading, error, refetch } = useQuery({
    queryKey: ['variants'],
    queryFn: () => getVariants({ page: 1, page_size: 100 }),
  });

  // Filter variants based on grouped/ungrouped status
  const filteredVariants = useMemo(() => {
    if (!variants?.results) return [];
    if (filterStatus === 'all') return variants.results;
    
    return variants.results.filter(v => {
      const isUngrouped = isVariantUngrouped(v);
      return filterStatus === 'ungrouped' ? isUngrouped : !isUngrouped;
    });
  }, [variants?.results, filterStatus]);

  // Ungroup mutation
  const ungroupMutation = useMutation({
    mutationFn: (variantIds: number[]) => ungroupVariants(variantIds),
    onSuccess: (data) => {
      toast({
        title: 'Variants Ungrouped',
        description: `${data.ungrouped_count} variant(s) moved to individual products.${data.orphaned_products_deleted > 0 ? ` ${data.orphaned_products_deleted} empty product(s) deleted.` : ''}`,
      });
      setSelectedIds([]);
      queryClient.invalidateQueries({ queryKey: ['variants'] });
      queryClient.invalidateQueries({ queryKey: ['products'] });
    },
    onError: (error: any) => {
      toast({
        title: 'Ungrouping Failed',
        description: error.response?.data?.detail || error.message,
        variant: 'destructive',
      });
    },
  });

  const { data: productTypes } = useQuery({
    queryKey: ['product-types'],
    queryFn: getProductTypes,
  });

  const typeMap = useMemo(() => {
    const map = new Map<number, ProductType>();
    productTypes?.results?.forEach((type) => map.set(type.id, type));
    return map;
  }, [productTypes]);

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      const allIds = filteredVariants.map(v => v.id);
      setSelectedIds(allIds);
    } else {
      setSelectedIds([]);
    }
  };

  const handleSelectRow = (id: number, checked: boolean) => {
    if (checked) {
      setSelectedIds([...selectedIds, id]);
    } else {
      setSelectedIds(selectedIds.filter(i => i !== id));
    }
  };

  const handleGroupClick = () => {
    if (selectedIds.length >= 2) {
      setShowGroupingDialog(true);
    }
  };

  const handleGroupingComplete = () => {
    setShowGroupingDialog(false);
    setSelectedIds([]);
    refetch();
  };

  const handleUngroupClick = () => {
    if (selectedIds.length > 0) {
      ungroupMutation.mutate(selectedIds);
    }
  };

  // Check if any selected variants are in groups (not placeholder products)
  const selectedVariants = useMemo(() => {
    if (!variants?.results) return [];
    return variants.results.filter(v => selectedIds.includes(v.id));
  }, [variants?.results, selectedIds]);

  const hasGroupedVariants = useMemo(() => {
    return selectedVariants.some(v => !isVariantUngrouped(v));
  }, [selectedVariants]);

  // Stats for display
  const stats = useMemo(() => {
    if (!variants?.results) return { total: 0, grouped: 0, ungrouped: 0 };
    const ungrouped = variants.results.filter(isVariantUngrouped).length;
    return {
      total: variants.results.length,
      grouped: variants.results.length - ungrouped,
      ungrouped,
    };
  }, [variants?.results]);

  const columns: Column<Variant>[] = [
    {
      key: 'select',
      header: () => (
        <Checkbox
          checked={selectedIds.length > 0 && selectedIds.length === filteredVariants.length}
          onCheckedChange={handleSelectAll}
        />
      ),
      render: (item) => (
        <Checkbox
          checked={selectedIds.includes(item.id)}
          onCheckedChange={(checked) => handleSelectRow(item.id, !!checked)}
        />
      ),
    },
    {
      key: 'sku',
      header: 'Variant',
      render: (item) => (
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-muted">
            <Package className="w-4 h-4 text-muted-foreground" />
          </div>
          <div>
            <div className="font-medium">{item.sku || item.internal_sku}</div>
            {item.source_title && (
              <div className="text-xs text-muted-foreground line-clamp-1">
                {item.source_title}
              </div>
            )}
          </div>
        </div>
      ),
    },
    {
      key: 'product_id',
      header: 'Product Group',
      render: (item) => {
        const isUngrouped = isVariantUngrouped(item);
        return (
          <div className="flex items-center gap-2">
            <span className={`text-sm ${isUngrouped ? 'text-muted-foreground' : 'font-medium'}`}>
              {item.product?.code || `#${item.product_id}`}
            </span>
            {isUngrouped ? (
              <Badge variant="outline" className="text-xs">
                Ungrouped
              </Badge>
            ) : (
              <Badge variant="default" className="text-xs">
                Grouped
              </Badge>
            )}
          </div>
        );
      },
    },
    {
      key: 'barcode',
      header: 'Barcode',
      render: (item) => (
        <span className="text-sm font-mono">{item.barcode || '—'}</span>
      ),
    },
    {
      key: 'mpn',
      header: 'MPN',
      render: (item) => (
        <span className="text-sm font-mono">{item.mpn || '—'}</span>
      ),
    },
    {
      key: 'internal_sku',
      header: 'Internal SKU',
      render: (item) => (
        <span className="text-sm font-mono text-muted-foreground">{item.internal_sku || '—'}</span>
      ),
    },
    {
      key: 'source_supplier',
      header: 'Source Supplier',
      render: (item) => (
        <span className="text-sm">{item.source_supplier || '—'}</span>
      ),
    },
    {
      key: 'product_type',
      header: 'Product Type',
      render: (item) => {
        const pt = item.product?.product_type_id != null ? typeMap.get(item.product.product_type_id) : null;
        return (
          <span className="text-sm text-muted-foreground">
            {pt ? (pt.code || pt.default_label || `#${pt.id}`) : '—'}
          </span>
        );
      },
    },
    {
      key: 'created_at',
      header: 'Created',
      render: (item) => (
        <span className="text-sm text-muted-foreground">
          {item.created_at ? new Date(item.created_at).toLocaleDateString(undefined, { year: 'numeric', month: '2-digit', day: '2-digit' }) : '—'}
        </span>
      ),
    },
  ];

  return (
    <>
      <div className="page-container">
        <PageHeader
          title="Variants"
          description="Select variants to group them into products."
          breadcrumbs={[
            { label: 'Dashboard', href: '/' },
            { label: 'Products', href: '/products' },
            { label: 'Variants' }
          ]}
          actions={
            <div className="flex gap-2">
              <Select value={filterStatus} onValueChange={(v) => setFilterStatus(v as FilterStatus)}>
                <SelectTrigger className="w-40">
                  <Filter className="w-4 h-4 mr-2" />
                  <SelectValue placeholder="Filter" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All ({stats.total})</SelectItem>
                  <SelectItem value="grouped">Grouped ({stats.grouped})</SelectItem>
                  <SelectItem value="ungrouped">Ungrouped ({stats.ungrouped})</SelectItem>
                </SelectContent>
              </Select>
              <Button variant="outline" onClick={() => navigate('/imports/new')}>
                <Upload className="w-4 h-4 mr-2" />
                Import Variants
              </Button>
              {selectedIds.length > 0 && hasGroupedVariants && (
                <Button
                  variant="outline"
                  onClick={handleUngroupClick}
                  disabled={ungroupMutation.isPending}
                >
                  {ungroupMutation.isPending ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <Unlink className="w-4 h-4 mr-2" />
                  )}
                  Ungroup Selected
                </Button>
              )}
              <Button
                onClick={handleGroupClick}
                disabled={selectedIds.length < 2}
                variant={selectedIds.length >= 2 ? 'default' : 'outline'}
              >
                <Users className="w-4 h-4 mr-2" />
                Group Selected {selectedIds.length > 0 && `(${selectedIds.length})`}
              </Button>
            </div>
          }
        />

        {selectedIds.length > 0 && (
          <div className="mb-4 p-4 rounded-lg bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Checkbox
                  checked={true}
                  onCheckedChange={() => setSelectedIds([])}
                />
                <span className="text-sm font-medium">
                  {selectedIds.length} variant{selectedIds.length !== 1 ? 's' : ''} selected
                </span>
              </div>
              <div className="flex items-center gap-2">
                {hasGroupedVariants && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={handleUngroupClick}
                    disabled={ungroupMutation.isPending}
                  >
                    {ungroupMutation.isPending ? (
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    ) : (
                      <Unlink className="w-4 h-4 mr-2" />
                    )}
                    Ungroup
                  </Button>
                )}
                <Button
                  size="sm"
                  onClick={handleGroupClick}
                  disabled={selectedIds.length < 2}
                >
                  <Users className="w-4 h-4 mr-2" />
                  Group into Product
                </Button>
              </div>
            </div>
          </div>
        )}

        <DataTable
          columns={columns}
          data={filteredVariants}
          keyExtractor={(item) => item.id}
          isLoading={isLoading}
          error={error as Error}
          emptyTitle={filterStatus === 'all' ? "No variants yet" : `No ${filterStatus} variants`}
          emptyDescription={filterStatus === 'all' ? "Import variants from CSV/XLSX to get started." : `No variants match the "${filterStatus}" filter.`}
          sortable={false}
        />
      </div>

      {showGroupingDialog && (
        <GroupingDialog
          variantIds={selectedIds}
          open={showGroupingDialog}
          onClose={() => setShowGroupingDialog(false)}
          onSuccess={handleGroupingComplete}
        />
      )}
    </>
  );
}
