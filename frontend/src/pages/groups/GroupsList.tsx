import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Layers, Store, Trash2, MoreHorizontal, CheckSquare } from 'lucide-react';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { DataTable, Column } from '@/components/DataTable';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  getChannelListings,
  getChannels,
  getProducts,
  createChannelListing,
  deleteChannelListing,
  ChannelListing,
  Channel,
  Product,
} from '@/lib/api';
import { useToast } from '@/hooks/use-toast';

export default function GroupsList() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [filterChannelId, setFilterChannelId] = useState<string>('all');
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());

  // Form state
  const [selectedProductId, setSelectedProductId] = useState<string>('');
  const [selectedChannelId, setSelectedChannelId] = useState<string>('');
  const [listingName, setListingName] = useState('');

  // Fetch listings
  const { data: listings, isLoading, error } = useQuery({
    queryKey: ['channel-listings', filterChannelId],
    queryFn: () => getChannelListings({
      page: 1,
      page_size: 100,
      ...(filterChannelId !== 'all' && { channel_id: parseInt(filterChannelId) }),
    }),
  });

  // Fetch channels for filter and form
  const { data: channelsData } = useQuery({
    queryKey: ['channels'],
    queryFn: getChannels,
  });

  // Fetch products for form
  const { data: productsData } = useQuery({
    queryKey: ['products'],
    queryFn: () => getProducts({ page: 1, page_size: 200 }),
    enabled: showCreateDialog,
  });

  // Create mutation
  const createMutation = useMutation({
    mutationFn: () => {
      const payload: any = { channel_id: parseInt(selectedChannelId), name: listingName, is_default: true };
      if (selectedProductId) {
        payload.product_id = parseInt(selectedProductId);
      }
      return createChannelListing(payload);
    },
    onSuccess: (data) => {
      toast({
        title: 'Marketplace listing created',
        description: `Created marketplace listing for ${data.product_code} on ${data.channel_code}`,
      });
      queryClient.invalidateQueries({ queryKey: ['channel-listings'] });
      setShowCreateDialog(false);
      resetForm();
      // Navigate to the new listing
      navigate(`/groups/${data.id}`);
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to create listing',
        variant: 'destructive',
      });
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteChannelListing(id),
    onSuccess: () => {
      toast({ title: 'Listing deleted' });
      queryClient.invalidateQueries({ queryKey: ['channel-listings'] });
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to delete listing',
        variant: 'destructive',
      });
    },
  });

  const allIds = (listings?.results || []).map((l) => l.id);
  const allSelected = allIds.length > 0 && allIds.every((id) => selectedIds.has(id));
  const someSelected = selectedIds.size > 0;

  const toggleSelect = (id: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (allSelected) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(allIds));
    }
  };

  const deleteSelected = async () => {
    if (!confirm(`Delete ${selectedIds.size} listing(s)?`)) return;
    for (const id of selectedIds) {
      await deleteChannelListing(id);
    }
    toast({ title: `${selectedIds.size} listing(s) deleted` });
    setSelectedIds(new Set());
    queryClient.invalidateQueries({ queryKey: ['channel-listings'] });
  };

  const resetForm = () => {
    setSelectedProductId('');
    setSelectedChannelId('');
    setListingName('');
  };

  const channels = channelsData?.results || [];
  const products = productsData?.results || [];

  const columns: Column<ChannelListing>[] = [
    {
      key: 'select',
      header: (
        <Checkbox
          checked={allSelected}
          onCheckedChange={toggleSelectAll}
          aria-label="Select all"
        />
      ),
      render: (item) => (
        <Checkbox
          checked={selectedIds.has(item.id)}
          onCheckedChange={() => toggleSelect(item.id)}
          onClick={(e) => e.stopPropagation()}
          aria-label="Select row"
        />
      ),
      className: 'w-12',
    },
    {
      key: 'name',
      header: 'Marketplace listing',
      render: (item) => (
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-muted">
            <Layers className="w-4 h-4 text-muted-foreground" />
          </div>
          <div>
            <div className="font-medium">
              {item.name || `${item.product_code} @ ${item.channel_code}`}
            </div>
            <div className="text-xs text-muted-foreground">
              Product: {item.product_code}
            </div>
          </div>
        </div>
      ),
    },
    {
      key: 'channel',
      header: 'Channel',
      render: (item) => (
        <div className="flex items-center gap-2">
          <Store className="w-4 h-4 text-muted-foreground" />
          <span className="text-sm">{item.channel_code}</span>
          {item.locale_code && (
            <Badge variant="outline" className="text-xs">
              {item.locale_code}
            </Badge>
          )}
        </div>
      ),
    },
    {
      key: 'variant_count',
      header: 'Variants',
      render: (item) => (
        <Badge variant="secondary">
          {item.variant_count ?? 0} variant{(item.variant_count ?? 0) !== 1 ? 's' : ''}
        </Badge>
      ),
    },
    {
      key: 'is_default',
      header: 'Status',
      render: (item) => (
        <div className="flex items-center gap-2">
          {item.is_default ? (
            <Badge variant="default">Default</Badge>
          ) : (
            <Badge variant="outline">Custom</Badge>
          )}
        </div>
      ),
    },
    {
      key: 'actions',
      header: '',
      render: (item) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => navigate(`/groups/${item.id}`)}>
              View Details
            </DropdownMenuItem>
            <DropdownMenuItem
              className="text-destructive"
              onClick={() => {
                if (confirm('Delete this listing group?')) {
                  deleteMutation.mutate(item.id);
                }
              }}
            >
              <Trash2 className="w-4 h-4 mr-2" />
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ];

  return (
    <>
      <div className="page-container">
        <PageHeader
          title="Marketplace listings"
          description="Marketplace listings define which products are published together on a marketplace and which variation axes apply for that marketplace."
          breadcrumbs={[{ label: 'Dashboard', href: '/' }, { label: 'Marketplace listings' }]}
          actions={
            <div className="flex gap-2 items-center">
              {someSelected && (
                <Button
                  variant="outline"
                  size="sm"
                  className="text-destructive border-destructive/40"
                  onClick={deleteSelected}
                >
                  <Trash2 className="w-4 h-4 mr-1.5" />
                  Delete {selectedIds.size} selected
                </Button>
              )}
              <Select value={filterChannelId} onValueChange={setFilterChannelId}>
                <SelectTrigger className="w-40">
                  <SelectValue placeholder="All Channels" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Channels</SelectItem>
                  {channels.map((ch) => (
                    <SelectItem key={ch.id} value={ch.id.toString()}>
                      {ch.name || ch.code}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button onClick={() => setShowCreateDialog(true)}>
                <Plus className="w-4 h-4 mr-2" />
                New marketplace listing
              </Button>
            </div>
          }
        />

        <DataTable
          columns={columns}
          data={listings?.results || []}
          keyExtractor={(item) => item.id}
          isLoading={isLoading}
          error={error as Error}
          emptyTitle="No marketplace listings yet"
          emptyDescription="Create a marketplace listing to bundle products for a marketplace and set variation axes."
          sortable
          onRowClick={(listing) => navigate(`/groups/${listing.id}`)}
        />
      </div>

      {/* Create Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create marketplace listing</DialogTitle>
            <DialogDescription>
              Create a marketplace listing for a product on a channel. You can add products and set variation axes (e.g. color, size) for this listing.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="product">Product family (optional)</Label>
              <Select value={selectedProductId || "none"} onValueChange={(value) => setSelectedProductId(value === "none" ? "" : value)}>
                <SelectTrigger id="product">
                  <SelectValue placeholder="Select a product (optional)" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">No product (will be assigned when adding variants)</SelectItem>
                  {products.map((p) => (
                    <SelectItem key={p.id} value={p.id.toString()}>
                      {p.code} {p.brand && `(${p.brand})`}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                Leave empty to create a listing without a product family. It will be set when you add variants.
                If variants belong to different product families, a new combined product will be created.
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="channel">Channel / Marketplace *</Label>
              <Select value={selectedChannelId} onValueChange={setSelectedChannelId}>
                <SelectTrigger id="channel">
                  <SelectValue placeholder="Select a channel" />
                </SelectTrigger>
                <SelectContent>
                  {channels.map((ch) => (
                    <SelectItem key={ch.id} value={ch.id.toString()}>
                      {ch.name || ch.code}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="name">Listing Name (optional)</Label>
              <Input
                id="name"
                value={listingName}
                onChange={(e) => setListingName(e.target.value)}
                placeholder="e.g., Color variants only"
              />
              <p className="text-xs text-muted-foreground">
                Optional label to distinguish multiple listings per product.
              </p>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreateDialog(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => createMutation.mutate()}
              disabled={!selectedChannelId || createMutation.isPending}
            >
              Create marketplace listing
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
