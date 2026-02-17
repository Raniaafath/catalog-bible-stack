import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Plus, Edit, Trash2, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { DataTable, Column } from '@/components/DataTable';
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
import { useToast } from '@/components/ui/use-toast';
import {
  getLocales,
  createLocale,
  updateLocale,
  deleteLocale,
  Locale,
} from '@/lib/api';

export default function LocalesTab() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingLocale, setEditingLocale] = useState<Locale | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [localeToDelete, setLocaleToDelete] = useState<Locale | null>(null);

  const [formData, setFormData] = useState<{ code: string; name: string }>({
    code: '',
    name: '',
  });

  const { data: locales, isLoading } = useQuery({
    queryKey: ['locales'],
    queryFn: () => getLocales({ page: 1, page_size: 100 }),
  });

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (editingLocale) {
        return updateLocale(editingLocale.id, formData);
      } else {
        return createLocale(formData);
      }
    },
    onSuccess: () => {
      toast({
        title: editingLocale ? 'Locale updated' : 'Locale created',
        description: `The locale has been ${editingLocale ? 'updated' : 'created'} successfully.`,
      });
      queryClient.invalidateQueries({ queryKey: ['locales'] });
      setDialogOpen(false);
      resetForm();
    },
    onError: (error: any) => {
      toast({
        title: `Failed to ${editingLocale ? 'update' : 'create'} locale`,
        description: error?.response?.data?.detail || error?.message || 'Something went wrong.',
        variant: 'destructive',
      });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteLocale(id),
    onSuccess: () => {
      toast({
        title: 'Locale deleted',
        description: 'The locale has been deleted successfully.',
      });
      queryClient.invalidateQueries({ queryKey: ['locales'] });
      setDeleteDialogOpen(false);
      setLocaleToDelete(null);
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to delete locale',
        description: error?.response?.data?.detail || error?.message || 'Something went wrong.',
        variant: 'destructive',
      });
    },
  });

  const resetForm = () => {
    setFormData({ code: '', name: '' });
    setEditingLocale(null);
  };

  const handleEdit = (locale: Locale) => {
    setEditingLocale(locale);
    setFormData({ code: locale.code, name: locale.name || '' });
    setDialogOpen(true);
  };

  const handleDelete = (locale: Locale) => {
    setLocaleToDelete(locale);
    setDeleteDialogOpen(true);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.code?.trim()) {
      toast({
        title: 'Validation error',
        description: 'Locale code is required.',
        variant: 'destructive',
      });
      return;
    }
    saveMutation.mutate();
  };

  const columns: Column<Locale>[] = [
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
          <h2 className="text-2xl font-semibold">Locales</h2>
          <p className="text-sm text-muted-foreground">
            Manage languages and locales for translations
          </p>
        </div>
        <Button onClick={() => { resetForm(); setDialogOpen(true); }}>
          <Plus className="w-4 h-4 mr-2" />
          Add Locale
        </Button>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <DataTable
          data={locales?.results || []}
          columns={columns}
          keyExtractor={(item) => item.id.toString()}
          emptyTitle="No locales found"
          emptyDescription="Create your first locale to get started."
        />
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingLocale ? 'Edit Locale' : 'Add Locale'}</DialogTitle>
            <DialogDescription>
              {editingLocale
                ? 'Update locale details.'
                : 'Create a new language locale (e.g., en, fr, de).'}
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
                  value={formData.code}
                  onChange={(e) => setFormData({ ...formData, code: e.target.value.toLowerCase().trim() })}
                  placeholder="e.g., en, fr, de, es"
                  disabled={!!editingLocale}
                  required
                />
                <p className="text-xs text-muted-foreground">
                  ISO 639-1 language code (2-5 characters, lowercase)
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="name">Name (Optional)</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g., English, French, German"
                />
                <p className="text-xs text-muted-foreground">
                  Human-readable name for the language
                </p>
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
            <DialogTitle>Delete Locale</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete the locale "{localeToDelete?.code}"? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => localeToDelete && deleteMutation.mutate(localeToDelete.id)}
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
