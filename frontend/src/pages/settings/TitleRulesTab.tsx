import { useState, useMemo } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Plus, Edit, Trash2, Loader2, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { Textarea } from '@/components/ui/textarea';
import { useToast } from '@/components/ui/use-toast';
import {
  getChannelLocalePolicies,
  getChannelPolicySets,
  getChannels,
  getLocales,
  createChannelLocalePolicy,
  updateChannelLocalePolicy,
  deleteChannelLocalePolicy,
  ChannelLocalePolicy,
  ChannelLocalePolicyCreate,
} from '@/lib/api';

const FIELD_LABELS: Record<string, string> = {
  policy_set: 'Policy Set',
  policy_set_id: 'Policy Set',
  locale: 'Locale',
  locale_id: 'Locale',
  title_max_len: 'Title Max Length',
  meta_title_max_len: 'Meta Title Max Length',
  meta_description_max_len: 'Meta Description Max Length',
  description_max_len: 'Description Max Length',
  bullet_count: 'Bullet Count',
  bullet_max_len: 'Bullet Max Length',
  title_separator: 'Title Separator',
  brand_position: 'Brand Position',
  title_mode: 'Title Mode',
  banned_terms: 'Banned Terms',
  non_field_errors: '',
};

function formatApiErrors(error: any): string[] {
  const data = error?.response?.data;
  if (!data) return [error?.message || 'Something went wrong.'];
  if (typeof data === 'string') return [data];
  if (typeof data.detail === 'string') return [data.detail];
  if (typeof data === 'object') {
    return Object.entries(data).flatMap(([field, msgs]) => {
      const label = FIELD_LABELS[field] || field.replace(/_/g, ' ');
      const messages = Array.isArray(msgs) ? msgs : [String(msgs)];
      return messages.map((m) => `${label}: ${m}`);
    });
  }
  return ['Something went wrong.'];
}

export default function TitleRulesTab() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingPolicy, setEditingPolicy] = useState<ChannelLocalePolicy | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [policyToDelete, setPolicyToDelete] = useState<ChannelLocalePolicy | null>(null);
  const [selectedChannelId, setSelectedChannelId] = useState<number | null>(null);

  const [formData, setFormData] = useState<ChannelLocalePolicyCreate>({
    policy_set_id: 0,
    locale_id: 0,
    country_code: '',
    currency_code: '',
    title_max_len: 150,
    meta_title_max_len: 70,
    meta_description_max_len: 160,
    description_max_len: 5000,
    bullet_count: 5,
    bullet_max_len: 200,
    title_separator: ' – ',
    brand_position: 'end',
    title_mode: 'auto',
    auto_create_selection: false,
    auto_approve_selection: false,
    selection_scope: 'product',
    context: 'title',
    normalize_whitespace: true,
    dedupe_words: true,
    banned_terms: [],
    rules_json: {},
  });

  const { data: policies, isLoading } = useQuery({
    queryKey: ['channel-locale-policies'],
    queryFn: () => getChannelLocalePolicies({ page: 1, page_size: 100 }),
  });

  const { data: channels } = useQuery({
    queryKey: ['channels'],
    queryFn: () => getChannels({ page: 1, page_size: 100 }),
  });

  const { data: locales } = useQuery({
    queryKey: ['locales'],
    queryFn: () => getLocales({ page: 1, page_size: 100 }),
  });

  const { data: policySets } = useQuery({
    queryKey: ['channel-policy-sets', selectedChannelId],
    queryFn: () => getChannelPolicySets({
      page: 1,
      page_size: 100,
      ...(selectedChannelId && { channel_id: selectedChannelId }),
    }),
    enabled: !!selectedChannelId || dialogOpen,
  });

  const filteredPolicySets = useMemo(() => {
    if (!policySets?.results) return [];
    return policySets.results;
  }, [policySets?.results]);

  const channelMap = useMemo(() => {
    const map = new Map<number, string>();
    channels?.results?.forEach((ch) => map.set(ch.id, ch.code));
    return map;
  }, [channels]);

  const localeMap = useMemo(() => {
    const map = new Map<number, string>();
    locales?.results?.forEach((loc) => map.set(loc.id, loc.code));
    return map;
  }, [locales]);

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (editingPolicy) {
        return updateChannelLocalePolicy(editingPolicy.id, formData);
      } else {
        return createChannelLocalePolicy(formData);
      }
    },
    onSuccess: () => {
      toast({
        title: editingPolicy ? 'Title rule updated' : 'Title rule created',
        description: `The title rule has been ${editingPolicy ? 'updated' : 'created'} successfully.`,
      });
      queryClient.invalidateQueries({ queryKey: ['channel-locale-policies'] });
      setDialogOpen(false);
      resetForm();
    },
    onError: () => {
      // errors are shown inline in the form
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteChannelLocalePolicy(id),
    onSuccess: () => {
      toast({
        title: 'Title rule deleted',
        description: 'The title rule has been deleted successfully.',
      });
      queryClient.invalidateQueries({ queryKey: ['channel-locale-policies'] });
      setDeleteDialogOpen(false);
      setPolicyToDelete(null);
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to delete title rule',
        description: formatApiErrors(error).join(' · '),
        variant: 'destructive',
      });
    },
  });

  const resetForm = () => {
    setFormData({
      policy_set_id: 0,
      locale_id: 0,
      country_code: '',
      currency_code: '',
      title_max_len: 150,
      meta_title_max_len: 70,
      meta_description_max_len: 160,
      description_max_len: 5000,
      bullet_count: 5,
      bullet_max_len: 200,
      title_separator: ' – ',
      brand_position: 'end',
      title_mode: 'auto',
      auto_create_selection: false,
      auto_approve_selection: false,
      selection_scope: 'product',
      context: 'title',
      normalize_whitespace: true,
      dedupe_words: true,
      banned_terms: [],
      rules_json: {},
    });
    setSelectedChannelId(null);
    setEditingPolicy(null);
  };

  const handleEdit = async (policy: ChannelLocalePolicy) => {
    setEditingPolicy(policy);
    // Find channel from policy set
    const policySet = policySets?.results?.find((ps) => ps.id === policy.policy_set);
    if (policySet) {
      setSelectedChannelId(policySet.channel);
    }
    setFormData({
      policy_set_id: policy.policy_set,
      locale_id: policy.locale,
      country_code: policy.country_code,
      currency_code: policy.currency_code,
      title_max_len: policy.title_max_len,
      meta_title_max_len: policy.meta_title_max_len,
      meta_description_max_len: policy.meta_description_max_len,
      description_max_len: policy.description_max_len,
      bullet_count: policy.bullet_count,
      bullet_max_len: policy.bullet_max_len,
      title_separator: policy.title_separator,
      brand_position: policy.brand_position,
      title_mode: policy.title_mode,
      auto_create_selection: policy.auto_create_selection,
      auto_approve_selection: policy.auto_approve_selection,
      selection_scope: policy.selection_scope,
      context: policy.context,
      normalize_whitespace: policy.normalize_whitespace,
      dedupe_words: policy.dedupe_words,
      banned_terms: policy.banned_terms,
      rules_json: policy.rules_json,
    });
    setDialogOpen(true);
  };

  const handleDelete = (policy: ChannelLocalePolicy) => {
    setPolicyToDelete(policy);
    setDeleteDialogOpen(true);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.policy_set_id || !formData.locale_id) {
      toast({
        title: 'Validation error',
        description: 'Policy set and locale are required.',
        variant: 'destructive',
      });
      return;
    }
    saveMutation.mutate();
  };

  const columns: Column<ChannelLocalePolicy>[] = [
    {
      key: 'channel',
      header: 'Channel',
      render: (item) => (
        <span className="font-medium">{item.channel_code || `#${item.policy_set}`}</span>
      ),
    },
    {
      key: 'locale',
      header: 'Locale',
      render: (item) => (
        <span className="text-sm">{item.locale_code || `#${item.locale}`}</span>
      ),
    },
    {
      key: 'title_max_len',
      header: 'Title Max',
      render: (item) => <span className="text-sm">{item.title_max_len}</span>,
    },
    {
      key: 'title_mode',
      header: 'Mode',
      render: (item) => (
        <Badge variant="outline">{item.title_mode === 'auto' ? 'Auto' : 'Review'}</Badge>
      ),
    },
    {
      key: 'brand_position',
      header: 'Brand',
      render: (item) => (
        <span className="text-sm capitalize">{item.brand_position}</span>
      ),
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
          <h2 className="text-2xl font-semibold">Title Rules</h2>
          <p className="text-sm text-muted-foreground">
            Configure title generation rules per channel and locale
          </p>
        </div>
        <Button onClick={() => { resetForm(); setDialogOpen(true); }}>
          <Plus className="w-4 h-4 mr-2" />
          Add Title Rule
        </Button>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <DataTable
          data={policies?.results || []}
          columns={columns}
          keyExtractor={(item) => item.id.toString()}
          emptyTitle="No title rules found"
          emptyDescription="Create your first title rule to get started."
        />
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen} className="max-w-2xl">
        <DialogContent className="max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingPolicy ? 'Edit Title Rule' : 'Add Title Rule'}</DialogTitle>
            <DialogDescription>
              {editingPolicy
                ? 'Update title generation rules.'
                : 'Configure title generation rules for a channel and locale combination.'}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit}>
            <div className="space-y-4 py-4">
              {/* Inline API errors */}
              {saveMutation.isError && (
                <div className="flex gap-2.5 rounded-lg border border-destructive/40 bg-destructive/5 px-3 py-3">
                  <AlertCircle className="h-4 w-4 text-destructive flex-shrink-0 mt-0.5" />
                  <div className="space-y-0.5">
                    {formatApiErrors(saveMutation.error).map((msg, i) => (
                      <p key={i} className="text-sm text-destructive">{msg}</p>
                    ))}
                  </div>
                </div>
              )}

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="channel_select">Channel</Label>
                  <Select
                    value={selectedChannelId?.toString() || ''}
                    onValueChange={(value) => {
                      const channelId = value ? parseInt(value) : null;
                      setSelectedChannelId(channelId);
                      setFormData({ ...formData, policy_set_id: 0 });
                    }}
                  >
                    <SelectTrigger id="channel_select">
                      <SelectValue placeholder="Select channel" />
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

                <div className="space-y-2">
                  <Label htmlFor="policy_set_id">
                    Policy Set <span className="text-red-500">*</span>
                  </Label>
                  <Select
                    value={formData.policy_set_id?.toString() || ''}
                    onValueChange={(value) => setFormData({ ...formData, policy_set_id: parseInt(value) })}
                    disabled={!selectedChannelId || filteredPolicySets.length === 0}
                  >
                    <SelectTrigger id="policy_set_id">
                      <SelectValue placeholder={!selectedChannelId ? "Select channel first" : "Select policy set"} />
                    </SelectTrigger>
                    <SelectContent>
                      {filteredPolicySets.map((ps) => (
                        <SelectItem key={ps.id} value={ps.id.toString()}>
                          {ps.channel_code} v{ps.version} ({ps.status})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {selectedChannelId && filteredPolicySets.length === 0 && (
                    <p className="text-xs text-muted-foreground">
                      No policy sets found for this channel. Create one first.
                    </p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="locale_id">
                    Locale <span className="text-red-500">*</span>
                  </Label>
                  <Select
                    value={formData.locale_id?.toString() || ''}
                    onValueChange={(value) => setFormData({ ...formData, locale_id: parseInt(value) })}
                  >
                    <SelectTrigger id="locale_id">
                      <SelectValue placeholder="Select locale" />
                    </SelectTrigger>
                    <SelectContent>
                      {locales?.results?.map((loc) => (
                        <SelectItem key={loc.id} value={loc.id.toString()}>
                          {loc.name || loc.code} ({loc.code})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="country_code">Country Code</Label>
                  <Input
                    id="country_code"
                    value={formData.country_code || ''}
                    onChange={(e) => setFormData({ ...formData, country_code: e.target.value })}
                    placeholder="e.g., US, FR, DE"
                    maxLength={2}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="currency_code">Currency Code</Label>
                  <Input
                    id="currency_code"
                    value={formData.currency_code || ''}
                    onChange={(e) => setFormData({ ...formData, currency_code: e.target.value })}
                    placeholder="e.g., USD, EUR, GBP"
                    maxLength={3}
                  />
                </div>
              </div>

              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Length Constraints</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="title_max_len">Title Max Length</Label>
                      <Input
                        id="title_max_len"
                        type="number"
                        value={formData.title_max_len || 150}
                        onChange={(e) => setFormData({ ...formData, title_max_len: parseInt(e.target.value) || 150 })}
                        min={1}
                        max={500}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="meta_title_max_len">Meta Title Max Length</Label>
                      <Input
                        id="meta_title_max_len"
                        type="number"
                        value={formData.meta_title_max_len || 70}
                        onChange={(e) => setFormData({ ...formData, meta_title_max_len: parseInt(e.target.value) || 70 })}
                        min={1}
                        max={200}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="meta_description_max_len">Meta Description Max Length</Label>
                      <Input
                        id="meta_description_max_len"
                        type="number"
                        value={formData.meta_description_max_len || 160}
                        onChange={(e) => setFormData({ ...formData, meta_description_max_len: parseInt(e.target.value) || 160 })}
                        min={1}
                        max={500}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="description_max_len">Description Max Length</Label>
                      <Input
                        id="description_max_len"
                        type="number"
                        value={formData.description_max_len || 5000}
                        onChange={(e) => setFormData({ ...formData, description_max_len: parseInt(e.target.value) || 5000 })}
                        min={1}
                        max={20000}
                      />
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Bullet Points</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="bullet_count">Bullet Count</Label>
                      <Input
                        id="bullet_count"
                        type="number"
                        value={formData.bullet_count || 5}
                        onChange={(e) => setFormData({ ...formData, bullet_count: parseInt(e.target.value) || 5 })}
                        min={0}
                        max={20}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="bullet_max_len">Bullet Max Length</Label>
                      <Input
                        id="bullet_max_len"
                        type="number"
                        value={formData.bullet_max_len || 200}
                        onChange={(e) => setFormData({ ...formData, bullet_max_len: parseInt(e.target.value) || 200 })}
                        min={1}
                        max={1000}
                      />
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Title Settings</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="title_separator">Title Separator</Label>
                    <Input
                      id="title_separator"
                      value={formData.title_separator || ' – '}
                      onChange={(e) => setFormData({ ...formData, title_separator: e.target.value })}
                      maxLength={20}
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="brand_position">Brand Position</Label>
                      <Select
                        value={formData.brand_position || 'end'}
                        onValueChange={(value: 'start' | 'end' | 'none') =>
                          setFormData({ ...formData, brand_position: value })
                        }
                      >
                        <SelectTrigger id="brand_position">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="start">Start</SelectItem>
                          <SelectItem value="end">End</SelectItem>
                          <SelectItem value="none">None</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="title_mode">Title Mode</Label>
                      <Select
                        value={formData.title_mode || 'auto'}
                        onValueChange={(value: 'auto' | 'review') =>
                          setFormData({ ...formData, title_mode: value })
                        }
                      >
                        <SelectTrigger id="title_mode">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="auto">Auto</SelectItem>
                          <SelectItem value="review">Review</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Behavior</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="selection_scope">Selection Scope</Label>
                    <Select
                      value={formData.selection_scope || 'product'}
                      onValueChange={(value: 'product' | 'variant') =>
                        setFormData({ ...formData, selection_scope: value })
                      }
                    >
                      <SelectTrigger id="selection_scope">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="product">Product</SelectItem>
                        <SelectItem value="variant">Variant</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="auto_create_selection"
                      checked={formData.auto_create_selection || false}
                      onCheckedChange={(checked) =>
                        setFormData({ ...formData, auto_create_selection: Boolean(checked) })
                      }
                    />
                    <Label htmlFor="auto_create_selection" className="cursor-pointer">
                      Auto Create Selection
                    </Label>
                  </div>

                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="auto_approve_selection"
                      checked={formData.auto_approve_selection || false}
                      onCheckedChange={(checked) =>
                        setFormData({ ...formData, auto_approve_selection: Boolean(checked) })
                      }
                    />
                    <Label htmlFor="auto_approve_selection" className="cursor-pointer">
                      Auto Approve Selection
                    </Label>
                  </div>

                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="normalize_whitespace"
                      checked={formData.normalize_whitespace !== false}
                      onCheckedChange={(checked) =>
                        setFormData({ ...formData, normalize_whitespace: Boolean(checked) })
                      }
                    />
                    <Label htmlFor="normalize_whitespace" className="cursor-pointer">
                      Normalize Whitespace
                    </Label>
                  </div>

                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="dedupe_words"
                      checked={formData.dedupe_words !== false}
                      onCheckedChange={(checked) =>
                        setFormData({ ...formData, dedupe_words: Boolean(checked) })
                      }
                    />
                    <Label htmlFor="dedupe_words" className="cursor-pointer">
                      Dedupe Words
                    </Label>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Advanced</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="banned_terms">Banned Terms (JSON array)</Label>
                    <Textarea
                      id="banned_terms"
                      value={JSON.stringify(formData.banned_terms || [], null, 2)}
                      onChange={(e) => {
                        try {
                          const parsed = JSON.parse(e.target.value);
                          if (Array.isArray(parsed)) {
                            setFormData({ ...formData, banned_terms: parsed });
                          }
                        } catch {
                          // Invalid JSON, ignore
                        }
                      }}
                      rows={3}
                      placeholder='["term1", "term2"]'
                    />
                    <p className="text-xs text-muted-foreground">
                      Array of terms to exclude from titles
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="rules_json">Rules JSON (Advanced)</Label>
                    <Textarea
                      id="rules_json"
                      value={JSON.stringify(formData.rules_json || {}, null, 2)}
                      onChange={(e) => {
                        try {
                          const parsed = JSON.parse(e.target.value);
                          if (typeof parsed === 'object') {
                            setFormData({ ...formData, rules_json: parsed });
                          }
                        } catch {
                          // Invalid JSON, ignore
                        }
                      }}
                      rows={5}
                      placeholder='{"key": "value"}'
                    />
                    <p className="text-xs text-muted-foreground">
                      Advanced rules configuration (JSON object)
                    </p>
                  </div>
                </CardContent>
              </Card>
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
            <DialogTitle>Delete Title Rule</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this title rule? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => policyToDelete && deleteMutation.mutate(policyToDelete.id)}
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
