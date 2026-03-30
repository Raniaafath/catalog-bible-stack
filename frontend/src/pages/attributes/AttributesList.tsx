import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Plus, Edit, Trash2, Loader2, Languages, Type } from 'lucide-react';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { DataTable, Column } from '@/components/DataTable';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { useToast } from '@/components/ui/use-toast';
import {
  getAttributes,
  deleteAttribute,
  bulkUpdateAttributes,
  Attribute,
} from '@/lib/api';

const dataTypeLabels: Record<string, string> = {
  text: 'Text',
  number: 'Number',
  bool: 'Boolean',
  enum: 'Enum',
  json: 'JSON',
};

export default function AttributesList() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [attributeToDelete, setAttributeToDelete] = useState<Attribute | null>(null);
  const [filterTranslatable, setFilterTranslatable] = useState<string>('all');

  const { data: attributes, isLoading, error } = useQuery({
    queryKey: ['attributes', filterTranslatable],
    queryFn: () => getAttributes({ page: 1, page_size: 100 }),
  });

  const filteredAttributes = useMemo(() => {
    if (!attributes?.results) return [];
    if (filterTranslatable === 'all') return attributes.results;
    if (filterTranslatable === 'translatable') {
      return attributes.results.filter((attr) => attr.is_value_translatable);
    }
    return attributes.results.filter((attr) => !attr.is_value_translatable);
  }, [attributes?.results, filterTranslatable]);

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteAttribute(id),
    onSuccess: () => {
      toast({
        title: 'Attribute deleted',
        description: 'The attribute has been deleted successfully.',
      });
      queryClient.invalidateQueries({ queryKey: ['attributes'] });
      setDeleteDialogOpen(false);
      setAttributeToDelete(null);
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to delete attribute',
        description: error?.response?.data?.detail || error?.message || 'Something went wrong.',
        variant: 'destructive',
      });
    },
  });

  const bulkUpdateMutation = useMutation({
    mutationFn: ({ ids, updates }: { ids: number[]; updates: Partial<Attribute> }) =>
      bulkUpdateAttributes(ids, updates),
    onSuccess: (data) => {
      toast({
        title: 'Attributes updated',
        description: data.message,
      });
      queryClient.invalidateQueries({ queryKey: ['attributes'] });
      setSelectedIds([]);
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to update attributes',
        description: error?.response?.data?.detail || error?.message || 'Something went wrong.',
        variant: 'destructive',
      });
    },
  });

  const handleDelete = (attribute: Attribute) => {
    setAttributeToDelete(attribute);
    setDeleteDialogOpen(true);
  };

  const handleBulkToggleTranslatable = (value: boolean) => {
    if (selectedIds.length === 0) {
      toast({ title: 'No attributes selected', description: 'Please select at least one attribute.', variant: 'destructive' });
      return;
    }
    bulkUpdateMutation.mutate({ ids: selectedIds, updates: { is_value_translatable: value } });
  };

  const handleBulkToggleUseInTitle = (value: boolean) => {
    if (selectedIds.length === 0) {
      toast({ title: 'No attributes selected', description: 'Please select at least one attribute.', variant: 'destructive' });
      return;
    }
    bulkUpdateMutation.mutate({ ids: selectedIds, updates: { use_in_title: value } });
  };

  const columns: Column<Attribute>[] = [
    {
      key: 'select',
      header: '',
      render: (item) => (
        <Checkbox
          checked={selectedIds.includes(item.id)}
          onCheckedChange={(checked) => {
            if (checked) {
              setSelectedIds([...selectedIds, item.id]);
            } else {
              setSelectedIds(selectedIds.filter((id) => id !== item.id));
            }
          }}
        />
      ),
    },
    {
      key: 'code',
      header: 'Code',
      render: (item) => (
        <div className="font-medium">{item.code}</div>
      ),
    },
    {
      key: 'data_type',
      header: 'Data Type',
      render: (item) => (
        <Badge variant="outline">{dataTypeLabels[item.data_type] || item.data_type}</Badge>
      ),
    },
    {
      key: 'is_value_translatable',
      header: 'Translatable',
      render: (item) => (
        <div className="flex items-center gap-2">
          <Checkbox
            checked={item.is_value_translatable || false}
            onCheckedChange={(checked) => {
              bulkUpdateMutation.mutate({
                ids: [item.id],
                updates: { is_value_translatable: Boolean(checked) },
              });
            }}
            disabled={bulkUpdateMutation.isPending}
          />
          {item.is_value_translatable && (
            <Languages className="w-4 h-4 text-primary" />
          )}
        </div>
      ),
    },
    {
      key: 'use_in_title',
      header: 'Use in title',
      render: (item) => (
        <div className="flex items-center gap-2">
          <Checkbox
            checked={item.use_in_title !== false}
            onCheckedChange={(checked) => {
              bulkUpdateMutation.mutate({ ids: [item.id], updates: { use_in_title: Boolean(checked) } });
            }}
            disabled={bulkUpdateMutation.isPending}
          />
          {item.use_in_title !== false && <Type className="w-4 h-4 text-primary" />}
        </div>
      ),
    },
    {
      key: 'unit',
      header: 'Unit',
      render: (item) => <span className="text-sm text-muted-foreground">{item.unit || '—'}</span>,
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (item) => (
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate(`/attributes/${item.id}/edit`)}
          >
            <Edit className="w-4 h-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => handleDelete(item)}
          >
            <Trash2 className="w-4 h-4 text-destructive" />
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div className="page-container">
      <PageHeader
        title="Attributes"
        description="Manage product attributes and configure which ones are translatable."
        breadcrumbs={[
          { label: 'Dashboard', href: '/' },
          { label: 'Attributes' },
        ]}
      />

      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button
              variant="outline"
              onClick={() => setFilterTranslatable('all')}
              className={filterTranslatable === 'all' ? 'bg-primary text-primary-foreground' : ''}
            >
              All
            </Button>
            <Button
              variant="outline"
              onClick={() => setFilterTranslatable('translatable')}
              className={filterTranslatable === 'translatable' ? 'bg-primary text-primary-foreground' : ''}
            >
              Translatable
            </Button>
            <Button
              variant="outline"
              onClick={() => setFilterTranslatable('non-translatable')}
              className={filterTranslatable === 'non-translatable' ? 'bg-primary text-primary-foreground' : ''}
            >
              Non-translatable
            </Button>
          </div>
          <div className="flex items-center gap-2">
            {selectedIds.length > 0 && (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleBulkToggleTranslatable(true)}
                  disabled={bulkUpdateMutation.isPending}
                >
                  {bulkUpdateMutation.isPending ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <Languages className="w-4 h-4 mr-2" />
                  )}
                  Mark as Translatable
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleBulkToggleTranslatable(false)}
                  disabled={bulkUpdateMutation.isPending}
                >
                  Mark as Non-translatable
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleBulkToggleUseInTitle(true)}
                  disabled={bulkUpdateMutation.isPending}
                >
                  <Type className="w-4 h-4 mr-2" />
                  Use in title
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleBulkToggleUseInTitle(false)}
                  disabled={bulkUpdateMutation.isPending}
                >
                  Exclude from title
                </Button>
                <span className="text-sm text-muted-foreground">{selectedIds.length} selected</span>
              </>
            )}
            <Button onClick={() => navigate('/attributes/new')}>
              <Plus className="w-4 h-4 mr-2" />
              Create Attribute
            </Button>
          </div>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
          </div>
        ) : error ? (
          <div className="text-center py-12 text-destructive">
            Failed to load attributes. Please try again.
          </div>
        ) : (
          <DataTable
            data={filteredAttributes}
            columns={columns}
            keyExtractor={(item) => item.id.toString()}
            emptyTitle="No attributes found"
            emptyDescription="Create your first attribute to get started."
          />
        )}
      </div>

      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Attribute</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete the attribute "{attributeToDelete?.code}"? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => attributeToDelete && deleteMutation.mutate(attributeToDelete.id)}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Deleting...
                </>
              ) : (
                'Delete'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
