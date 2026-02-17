import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Upload, Package, Trash2 } from 'lucide-react';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { DataTable, Column } from '@/components/DataTable';
import { Badge } from '@/components/ui/badge';
import { getProducts, getProductTypes, deleteProduct, Product, ProductType } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';

const statusLabels: Record<string, string> = {
  draft: 'Draft',
  active: 'Active',
  discontinued: 'Discontinued',
};

export default function ProductsList() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [filterEmpty, setFilterEmpty] = useState<boolean>(false);

  const { data: products, isLoading, error } = useQuery({
    queryKey: ['products'],
    queryFn: () => getProducts({ page: 1, page_size: 200 }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteProduct(id),
    onSuccess: (_, id) => {
      toast({ title: 'Product deleted' });
      queryClient.invalidateQueries({ queryKey: ['products'] });
      queryClient.invalidateQueries({ queryKey: ['variants'] });
    },
    onError: (err: unknown) => {
      const msg = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : null;
      toast({
        title: 'Delete failed',
        description: msg || 'Product may have listings or other links.',
        variant: 'destructive',
      });
    },
  });

  const rows = useMemo(() => {
    const list = products?.results ?? [];
    if (filterEmpty) return list.filter((p) => (p.variant_count ?? 0) > 0);
    return list;
  }, [products?.results, filterEmpty]);

  const { data: productTypes } = useQuery({
    queryKey: ['product-types'],
    queryFn: getProductTypes,
  });

  const typeMap = useMemo(() => {
    const map = new Map<number, ProductType>();
    productTypes?.results?.forEach((type) => map.set(type.id, type));
    return map;
  }, [productTypes]);

  const columns: Column<Product>[] = [
    {
      key: 'code',
      header: 'Product family',
      render: (item) => (
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-muted">
            <Package className="w-4 h-4 text-muted-foreground" />
          </div>
          <div>
            <div className="font-medium">{item.code}</div>
            <div className="text-xs text-muted-foreground">
              {item.default_label || '—'}
            </div>
          </div>
        </div>
      ),
    },
    {
      key: 'product_type_id',
      header: 'Product Type',
      render: (item) => {
        const type = typeMap.get(item.product_type_id);
        return (
          <span className="text-sm text-muted-foreground">
            {type?.category_path || type?.default_label || type?.code || `#${item.product_type_id}`}
          </span>
        );
      },
    },
    {
      key: 'brand',
      header: 'Brand',
      render: (item) => <span className="text-sm">{item.brand || '—'}</span>,
    },
    {
      key: 'status',
      header: 'Status',
      render: (item) => (
        <span className="text-sm font-medium">{statusLabels[item.status] || item.status}</span>
      ),
    },
    {
      key: 'variant_count',
      header: 'Variants',
      render: (item) => {
        const n = item.variant_count ?? 0;
        return (
          <Badge variant={n === 0 ? 'destructive' : 'secondary'}>
            {n} variant{n !== 1 ? 's' : ''}
          </Badge>
        );
      },
    },
    {
      key: 'actions',
      header: '',
      render: (item) => {
        const empty = (item.variant_count ?? 0) === 0;
        return empty ? (
          <Button
            variant="ghost"
            size="sm"
            className="text-destructive hover:text-destructive"
            onClick={(e) => {
              e.stopPropagation();
              if (confirm(`Delete empty product "${item.code}"?`)) deleteMutation.mutate(item.id);
            }}
            disabled={deleteMutation.isPending}
          >
            <Trash2 className="w-4 h-4" />
          </Button>
        ) : null;
      },
    },
  ];

  return (
    <div className="page-container">
      <PageHeader
        title="Products"
        description="Each product has one or more variants (SKUs). Easiest: import a CSV. Or add a product with at least one variant."
        breadcrumbs={[{ label: 'Dashboard', href: '/' }, { label: 'Products' }]}
        actions={
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => setFilterEmpty((v) => !v)}>
              {filterEmpty ? 'Show all' : 'With variants only'}
            </Button>
            <Button variant="outline" onClick={() => navigate('/imports/new')}>
              <Upload className="w-4 h-4 mr-2" />
              Import CSV
            </Button>
            <Button onClick={() => navigate('/products/new')}>
              <Plus className="w-4 h-4 mr-2" />
              Add product
            </Button>
          </div>
        }
      />

      <DataTable
        columns={columns}
        data={rows}
        keyExtractor={(item) => item.id}
        isLoading={isLoading}
        error={error as Error}
        emptyTitle="No products yet"
        emptyDescription="Import a CSV (one row per variant) or add a product with at least one variant. You can also group variants from the Variants page."
        sortable
        onRowClick={(product) => navigate(`/products/${product.id}`)}
      />
    </div>
  );
}
