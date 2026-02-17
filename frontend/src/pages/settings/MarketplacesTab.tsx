import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Plus, Edit, Trash2, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { DataTable, Column } from '@/components/DataTable';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { useToast } from '@/components/ui/use-toast';
import {
  getChannels,
  createChannel,
  updateChannel,
  deleteChannel,
  Channel,
} from '@/lib/api';

export default function MarketplacesTab() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingChannel, setEditingChannel] = useState<Channel | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [channelToDelete, setChannelToDelete] = useState<Channel | null>(null);

  const [formData, setFormData] = useState<Partial<Channel>>({
    code: '',
    name: '',
    is_active: true,
    priority: 0,
  });

  const { data: channels, isLoading } = useQuery({
    queryKey: ['channels'],
    queryFn: () => getChannels({ page: 1, page_size: 100 }),
  });

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (editingChannel) {
        return updateChannel(editingChannel.id, formData);
      } else {
        return createChannel(formData as Omit<Channel, 'id' | 'created_at'>);
      }
    },
    onSuccess: () => {
      toast({
        title: editingChannel ? 'Channel updated' : 'Channel created',
        description: `The channel has been ${editingChannel ? 'updated' : 'created'} successfully.`,
      });
      queryClient.invalidateQueries({ queryKey: ['channels'] });
      setDialogOpen(false);
      resetForm();
    },
    onError: (error: any) => {
      toast({
        title: `Failed to ${editingChannel ? 'update' : 'create'} channel`,
        description: error?.response?.data?.detail || error?.message || 'Something went wrong.',
        variant: 'destructive',
      });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteChannel(id),
    onSuccess: () => {
      toast({
        title: 'Channel deleted',
        description: 'The channel has been deleted successfully.',
      });
      queryClient.invalidateQueries({ queryKey: ['channels'] });
      setDeleteDialogOpen(false);
      setChannelToDelete(null);
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to delete channel',
        description: error?.response?.data?.detail || error?.message || 'Something went wrong.',
        variant: 'destructive',
      });
    },
  });

  const resetForm = () => {
    setFormData({ code: '', name: '', is_active: true, priority: 0 });
    setEditingChannel(null);
  };

  const handleEdit = (channel: Channel) => {
    setEditingChannel(channel);
    setFormData({
      code: channel.code,
      name: channel.name,
      is_active: channel.is_active,
      priority: channel.priority,
    });
    setDialogOpen(true);
  };

  const handleDelete = (channel: Channel) => {
    setChannelToDelete(channel);
    setDeleteDialogOpen(true);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.code?.trim()) {
      toast({
        title: 'Validation error',
        description: 'Code is required.',
        variant: 'destructive',
      });
      return;
    }
    saveMutation.mutate();
  };

  const columns: Column<Channel>[] = [
    {
      key: 'code',
      header: 'Code',
      render: (item) => <div className="font-medium">{item.code}</div>,
    },
    {
      key: 'name',
      header: 'Name',
      render: (item) => <span className="text-sm">{item.name || '—'}</span>,
    },
    {
      key: 'is_active',
      header: 'Status',
      render: (item) => (
        <Badge variant={item.is_active ? 'default' : 'secondary'}>
          {item.is_active ? 'Active' : 'Inactive'}
        </Badge>
      ),
    },
    {
      key: 'priority',
      header: 'Priority',
      render: (item) => <span className="text-sm">{item.priority}</span>,
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (item) => (
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" onClick={() => handleEdit(item)}>
            <Edit className="w-4 h-4" />
          </Button>
          <Button variant="ghost" size="sm" onClick={() => handleDelete(item)}>
            <Trash2 className="w-4 h-4 text-destructive" />
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-semibold">Marketplaces</h2>
          <p className="text-sm text-muted-foreground">
            Manage sales channels (Amazon, eBay, Shopify, etc.)
          </p>
        </div>
        <Button onClick={() => { resetForm(); setDialogOpen(true); }}>
          <Plus className="w-4 h-4 mr-2" />
          Add Marketplace
        </Button>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <DataTable
          data={channels?.results || []}
          columns={columns}
          keyExtractor={(item) => item.id.toString()}
          emptyTitle="No marketplaces found"
          emptyDescription="Create your first marketplace to get started."
        />
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingChannel ? 'Edit Marketplace' : 'Add Marketplace'}</DialogTitle>
            <DialogDescription>
              {editingChannel
                ? 'Update marketplace details.'
                : 'Create a new sales channel marketplace.'}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit}>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="code">
                  Code <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="code"
                  value={formData.code || ''}
                  onChange={(e) => setFormData({ ...formData, code: e.target.value })}
                  placeholder="e.g., amazon, ebay, shopify"
                  disabled={!!editingChannel}
                  required
                />
                <p className="text-xs text-muted-foreground">
                  Unique identifier (lowercase, no spaces)
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="name">Name</Label>
                <Input
                  id="name"
                  value={formData.name || ''}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g., Amazon, eBay, Shopify"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="priority">Priority</Label>
                <Input
                  id="priority"
                  type="number"
                  value={formData.priority || 0}
                  onChange={(e) => setFormData({ ...formData, priority: parseInt(e.target.value) || 0 })}
                />
                <p className="text-xs text-muted-foreground">
                  Higher priority channels appear first in lists
                </p>
              </div>

              <div className="flex items-center space-x-2">
                <Checkbox
                  id="is_active"
                  checked={formData.is_active || false}
                  onCheckedChange={(checked) => setFormData({ ...formData, is_active: Boolean(checked) })}
                />
                <Label htmlFor="is_active" className="cursor-pointer">
                  Active
                </Label>
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => { setDialogOpen(false); resetForm(); }}>
                Cancel
              </Button>
              <Button type="submit" disabled={saveMutation.isPending}>
                {saveMutation.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Saving...
                  </>
                ) : (
                  'Save'
                )}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Marketplace</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete the marketplace "{channelToDelete?.code}"? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => channelToDelete && deleteMutation.mutate(channelToDelete.id)}
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
