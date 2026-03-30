import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Plus, Edit, Trash2, Loader2, Layers } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { DataTable, Column } from '@/components/DataTable';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { useToast } from '@/components/ui/use-toast';
import {
  getChannels,
  createChannel,
  updateChannel,
  deleteChannel,
  getChannelPolicySets,
  createChannelPolicySet,
  deleteChannelPolicySet,
  Channel,
  ChannelPolicySet,
  ChannelPolicySetCreate,
} from '@/lib/api';

export default function MarketplacesTab() {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  // Channel state
  const [channelDialogOpen, setChannelDialogOpen] = useState(false);
  const [editingChannel, setEditingChannel] = useState<Channel | null>(null);
  const [deleteChannelDialogOpen, setDeleteChannelDialogOpen] = useState(false);
  const [channelToDelete, setChannelToDelete] = useState<Channel | null>(null);
  const [channelFormData, setChannelFormData] = useState<Partial<Channel>>({
    code: '',
    name: '',
    is_active: true,
    priority: 0,
  });

  // Policy Set state
  const [policySetDialogOpen, setPolicySetDialogOpen] = useState(false);
  const [deletePolicySetDialogOpen, setDeletePolicySetDialogOpen] = useState(false);
  const [policySetToDelete, setPolicySetToDelete] = useState<ChannelPolicySet | null>(null);
  const [policySetFormData, setPolicySetFormData] = useState<ChannelPolicySetCreate>({
    channel: 0,
    version: 1,
    status: 'active',
    notes: '',
  });

  // Queries
  const { data: channels, isLoading: channelsLoading } = useQuery({
    queryKey: ['channels'],
    queryFn: () => getChannels({ page: 1, page_size: 100 }),
  });

  const { data: policySets, isLoading: policySetsLoading } = useQuery({
    queryKey: ['channel-policy-sets'],
    queryFn: () => getChannelPolicySets({ page: 1, page_size: 100 }),
  });

  // Channel mutations
  const saveChannelMutation = useMutation({
    mutationFn: async () => {
      if (editingChannel) {
        return updateChannel(editingChannel.id, channelFormData);
      } else {
        return createChannel(channelFormData as Omit<Channel, 'id' | 'created_at'>);
      }
    },
    onSuccess: () => {
      toast({
        title: editingChannel ? 'Channel updated' : 'Channel created',
        description: `The channel has been ${editingChannel ? 'updated' : 'created'} successfully.`,
      });
      queryClient.invalidateQueries({ queryKey: ['channels'] });
      setChannelDialogOpen(false);
      resetChannelForm();
    },
    onError: (error: any) => {
      toast({
        title: `Failed to ${editingChannel ? 'update' : 'create'} channel`,
        description: error?.response?.data?.detail || error?.message || 'Something went wrong.',
        variant: 'destructive',
      });
    },
  });

  const deleteChannelMutation = useMutation({
    mutationFn: (id: number) => deleteChannel(id),
    onSuccess: () => {
      toast({ title: 'Channel deleted' });
      queryClient.invalidateQueries({ queryKey: ['channels'] });
      setDeleteChannelDialogOpen(false);
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

  // Policy Set mutations
  const createPolicySetMutation = useMutation({
    mutationFn: () => createChannelPolicySet(policySetFormData),
    onSuccess: () => {
      toast({
        title: 'Policy set created',
        description: 'The policy set has been created. You can now add title rules to it.',
      });
      queryClient.invalidateQueries({ queryKey: ['channel-policy-sets'] });
      setPolicySetDialogOpen(false);
      resetPolicySetForm();
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to create policy set',
        description: error?.response?.data?.detail || error?.message || 'Something went wrong.',
        variant: 'destructive',
      });
    },
  });

  const deletePolicySetMutation = useMutation({
    mutationFn: (id: number) => deleteChannelPolicySet(id),
    onSuccess: () => {
      toast({ title: 'Policy set deleted' });
      queryClient.invalidateQueries({ queryKey: ['channel-policy-sets'] });
      setDeletePolicySetDialogOpen(false);
      setPolicySetToDelete(null);
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to delete policy set',
        description: error?.response?.data?.detail || error?.message || 'Something went wrong.',
        variant: 'destructive',
      });
    },
  });

  const resetChannelForm = () => {
    setChannelFormData({ code: '', name: '', is_active: true, priority: 0 });
    setEditingChannel(null);
  };

  const resetPolicySetForm = () => {
    setPolicySetFormData({ channel: 0, version: 1, status: 'active', notes: '' });
  };

  const handleEditChannel = (channel: Channel) => {
    setEditingChannel(channel);
    setChannelFormData({ code: channel.code, name: channel.name, is_active: channel.is_active, priority: channel.priority });
    setChannelDialogOpen(true);
  };

  const handleDeleteChannel = (channel: Channel) => {
    setChannelToDelete(channel);
    setDeleteChannelDialogOpen(true);
  };

  const handleDeletePolicySet = (ps: ChannelPolicySet) => {
    setPolicySetToDelete(ps);
    setDeletePolicySetDialogOpen(true);
  };

  const handleChannelSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!channelFormData.code?.trim()) {
      toast({ title: 'Validation error', description: 'Code is required.', variant: 'destructive' });
      return;
    }
    saveChannelMutation.mutate();
  };

  const handlePolicySetSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!policySetFormData.channel) {
      toast({ title: 'Validation error', description: 'Channel is required.', variant: 'destructive' });
      return;
    }
    createPolicySetMutation.mutate();
  };

  const channelColumns: Column<Channel>[] = [
    {
      key: 'code',
      header: 'Code',
      render: (item) => <div className="font-medium font-mono text-sm">{item.code}</div>,
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
      render: (item) => <span className="text-sm text-muted-foreground">{item.priority}</span>,
    },
    {
      key: 'actions',
      header: '',
      render: (item) => (
        <div className="flex items-center gap-1 justify-end">
          <Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={() => handleEditChannel(item)}>
            <Edit className="w-4 h-4" />
          </Button>
          <Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={() => handleDeleteChannel(item)}>
            <Trash2 className="w-4 h-4 text-destructive" />
          </Button>
        </div>
      ),
    },
  ];

  const policySetColumns: Column<ChannelPolicySet>[] = [
    {
      key: 'channel_code',
      header: 'Channel',
      render: (item) => (
        <span className="font-medium font-mono text-sm">{item.channel_code || `#${item.channel}`}</span>
      ),
    },
    {
      key: 'version',
      header: 'Version',
      render: (item) => <span className="text-sm">v{item.version}</span>,
    },
    {
      key: 'status',
      header: 'Status',
      render: (item) => (
        <Badge variant={item.status === 'active' ? 'default' : item.status === 'draft' ? 'secondary' : 'outline'}>
          {item.status}
        </Badge>
      ),
    },
    {
      key: 'notes',
      header: 'Notes',
      render: (item) => (
        <span className="text-sm text-muted-foreground truncate max-w-xs">{item.notes || '—'}</span>
      ),
    },
    {
      key: 'actions',
      header: '',
      render: (item) => (
        <div className="flex items-center gap-1 justify-end">
          <Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={() => handleDeletePolicySet(item)}>
            <Trash2 className="w-4 h-4 text-destructive" />
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-8">
      {/* Channels */}
      <Card>
        <CardHeader className="flex flex-row items-start justify-between">
          <div>
            <CardTitle>Marketplaces</CardTitle>
            <CardDescription>Manage sales channels (Amazon, eBay, Shopify, etc.)</CardDescription>
          </div>
          <Button size="sm" onClick={() => { resetChannelForm(); setChannelDialogOpen(true); }}>
            <Plus className="w-4 h-4 mr-2" />
            Add Marketplace
          </Button>
        </CardHeader>
        <CardContent>
          <DataTable
            data={channels?.results || []}
            columns={channelColumns}
            keyExtractor={(item) => item.id.toString()}
            isLoading={channelsLoading}
            emptyTitle="No marketplaces found"
            emptyDescription="Create your first marketplace to get started."
          />
        </CardContent>
      </Card>

      {/* Policy Sets */}
      <Card>
        <CardHeader className="flex flex-row items-start justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Layers className="w-4 h-4" />
              Policy Sets
            </CardTitle>
            <CardDescription>
              A policy set is required before you can add title rules to a channel.
              Create one here first, then go to the Title Rules tab.
            </CardDescription>
          </div>
          <Button size="sm" onClick={() => { resetPolicySetForm(); setPolicySetDialogOpen(true); }}>
            <Plus className="w-4 h-4 mr-2" />
            New Policy Set
          </Button>
        </CardHeader>
        <CardContent>
          <DataTable
            data={policySets?.results || []}
            columns={policySetColumns}
            keyExtractor={(item) => item.id.toString()}
            isLoading={policySetsLoading}
            emptyTitle="No policy sets yet"
            emptyDescription="Create a policy set for a channel, then add title rules to it in the Title Rules tab."
          />
        </CardContent>
      </Card>

      {/* Channel Dialog */}
      <Dialog open={channelDialogOpen} onOpenChange={setChannelDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingChannel ? 'Edit Marketplace' : 'Add Marketplace'}</DialogTitle>
            <DialogDescription>
              {editingChannel ? 'Update marketplace details.' : 'Create a new sales channel marketplace.'}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleChannelSubmit}>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="code">Code <span className="text-red-500">*</span></Label>
                <Input
                  id="code"
                  value={channelFormData.code || ''}
                  onChange={(e) => setChannelFormData({ ...channelFormData, code: e.target.value })}
                  placeholder="e.g., amazon, ebay, shopify"
                  disabled={!!editingChannel}
                  required
                />
                <p className="text-xs text-muted-foreground">Unique identifier (lowercase, no spaces)</p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="name">Name</Label>
                <Input
                  id="name"
                  value={channelFormData.name || ''}
                  onChange={(e) => setChannelFormData({ ...channelFormData, name: e.target.value })}
                  placeholder="e.g., Amazon, eBay, Shopify"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="priority">Priority</Label>
                <Input
                  id="priority"
                  type="number"
                  value={channelFormData.priority || 0}
                  onChange={(e) => setChannelFormData({ ...channelFormData, priority: parseInt(e.target.value) || 0 })}
                />
                <p className="text-xs text-muted-foreground">Higher priority channels appear first in lists</p>
              </div>
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="is_active"
                  checked={channelFormData.is_active || false}
                  onCheckedChange={(checked) => setChannelFormData({ ...channelFormData, is_active: Boolean(checked) })}
                />
                <Label htmlFor="is_active" className="cursor-pointer">Active</Label>
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => { setChannelDialogOpen(false); resetChannelForm(); }}>Cancel</Button>
              <Button type="submit" disabled={saveChannelMutation.isPending}>
                {saveChannelMutation.isPending ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Saving...</> : 'Save'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Policy Set Create Dialog */}
      <Dialog open={policySetDialogOpen} onOpenChange={setPolicySetDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New Policy Set</DialogTitle>
            <DialogDescription>
              Create a policy set for a channel. After creating it, go to Title Rules to add locale-specific rules.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handlePolicySetSubmit}>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label>Channel <span className="text-red-500">*</span></Label>
                <Select
                  value={policySetFormData.channel?.toString() || ''}
                  onValueChange={(val) => setPolicySetFormData({ ...policySetFormData, channel: parseInt(val) })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select a channel" />
                  </SelectTrigger>
                  <SelectContent>
                    {channels?.results?.map((ch) => (
                      <SelectItem key={ch.id} value={ch.id.toString()}>
                        {ch.name || ch.code}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="ps_version">Version</Label>
                  <Input
                    id="ps_version"
                    type="number"
                    min={1}
                    value={policySetFormData.version}
                    onChange={(e) => setPolicySetFormData({ ...policySetFormData, version: parseInt(e.target.value) || 1 })}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Status</Label>
                  <Select
                    value={policySetFormData.status || 'active'}
                    onValueChange={(val: 'draft' | 'active' | 'archived') =>
                      setPolicySetFormData({ ...policySetFormData, status: val })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="active">Active</SelectItem>
                      <SelectItem value="draft">Draft</SelectItem>
                      <SelectItem value="archived">Archived</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="ps_notes">Notes (optional)</Label>
                <Textarea
                  id="ps_notes"
                  value={policySetFormData.notes || ''}
                  onChange={(e) => setPolicySetFormData({ ...policySetFormData, notes: e.target.value })}
                  placeholder="e.g., Initial ruleset for Amazon EU"
                  rows={2}
                />
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => { setPolicySetDialogOpen(false); resetPolicySetForm(); }}>Cancel</Button>
              <Button type="submit" disabled={createPolicySetMutation.isPending}>
                {createPolicySetMutation.isPending ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Creating...</> : 'Create Policy Set'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Channel Dialog */}
      <Dialog open={deleteChannelDialogOpen} onOpenChange={setDeleteChannelDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Marketplace</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete "{channelToDelete?.code}"? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteChannelDialogOpen(false)}>Cancel</Button>
            <Button variant="destructive" onClick={() => channelToDelete && deleteChannelMutation.mutate(channelToDelete.id)} disabled={deleteChannelMutation.isPending}>
              {deleteChannelMutation.isPending ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Deleting...</> : 'Delete'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Policy Set Dialog */}
      <Dialog open={deletePolicySetDialogOpen} onOpenChange={setDeletePolicySetDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Policy Set</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this policy set? All title rules linked to it will also be removed.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeletePolicySetDialogOpen(false)}>Cancel</Button>
            <Button variant="destructive" onClick={() => policySetToDelete && deletePolicySetMutation.mutate(policySetToDelete.id)} disabled={deletePolicySetMutation.isPending}>
              {deletePolicySetMutation.isPending ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Deleting...</> : 'Delete'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
