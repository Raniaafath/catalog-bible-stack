import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Plus, FileText, Pencil, Trash2 } from 'lucide-react';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  getTemplates,
  getProductTypes,
  getChannels,
  getLocales,
  deleteTemplate,
  getApiErrorMessage,
  Template,
  ProductType,
  Channel,
  Locale,
} from '@/lib/api';
import { useToast } from '@/hooks/use-toast';
import { useMutation, useQueryClient } from '@tanstack/react-query';
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

export default function TemplatesList() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [filterProductTypeId, setFilterProductTypeId] = useState<string>('all');
  const [filterChannelCode, setFilterChannelCode] = useState<string>('all');
  const [filterLocaleCode, setFilterLocaleCode] = useState<string>('all');
  const [deleteId, setDeleteId] = useState<number | null>(null);

  const { data: templatesData, isLoading } = useQuery({
    queryKey: ['templates', filterProductTypeId, filterChannelCode, filterLocaleCode],
    queryFn: () =>
      getTemplates({
        page: 1,
        page_size: 200,
        ...(filterProductTypeId !== 'all' && { product_type_id: parseInt(filterProductTypeId) }),
        ...(filterChannelCode !== 'all' && { channel_code: filterChannelCode }),
        ...(filterLocaleCode !== 'all' && { locale_code: filterLocaleCode }),
      }),
  });

  const { data: productTypesData } = useQuery({
    queryKey: ['product-types'],
    queryFn: () => getProductTypes(),
  });
  const { data: channelsData } = useQuery({
    queryKey: ['channels'],
    queryFn: () => getChannels(),
  });
  const { data: localesData } = useQuery({
    queryKey: ['locales'],
    queryFn: () => getLocales(),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteTemplate(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['templates'] });
      setDeleteId(null);
      toast({ title: 'Template deleted' });
    },
    onError: (err: unknown) => {
      toast({
        title: 'Cannot delete template',
        description: getApiErrorMessage(err),
        variant: 'destructive',
      });
    },
  });

  const templates = templatesData?.results ?? [];
  const productTypes = (productTypesData?.results ?? []) as ProductType[];
  const channels = (channelsData?.results ?? []) as Channel[];
  const locales = (localesData?.results ?? []) as Locale[];

  // Client-side filter if backend doesn't filter
  const filtered = templates.filter((t: Template) => {
    if (filterProductTypeId !== 'all' && t.product_type_id !== parseInt(filterProductTypeId)) return false;
    if (filterChannelCode !== 'all' && t.channel_code !== filterChannelCode) return false;
    if (filterLocaleCode !== 'all' && t.locale_code !== filterLocaleCode) return false;
    return true;
  });

  return (
    <div className="page-container">
      <PageHeader
        title="Title templates"
        description="Build templates with head term, hook term, and attributes for title generation."
        breadcrumbs={[
          { label: 'Dashboard', href: '/' },
          { label: 'Templates' },
        ]}
        actions={
          <Button asChild>
            <Link to="/templates/new">
              <Plus className="w-4 h-4 mr-2" />
              Create template
            </Link>
          </Button>
        }
      />

      <Card>
        <CardHeader>
          <CardTitle>Templates</CardTitle>
          <CardDescription>Filter by product type, channel, or locale.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Product type</label>
              <Select value={filterProductTypeId} onValueChange={setFilterProductTypeId}>
                <SelectTrigger className="w-[200px]">
                  <SelectValue placeholder="All" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All</SelectItem>
                  {productTypes.map((pt) => (
                    <SelectItem key={pt.id} value={String(pt.id)}>
                      {pt.code}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Channel</label>
              <Select value={filterChannelCode} onValueChange={setFilterChannelCode}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="All" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All</SelectItem>
                  {channels.map((c) => (
                    <SelectItem key={c.id} value={c.code}>
                      {c.code}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Locale</label>
              <Select value={filterLocaleCode} onValueChange={setFilterLocaleCode}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="All" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All</SelectItem>
                  {locales.map((loc) => (
                    <SelectItem key={loc.code} value={loc.code}>
                      {loc.name || loc.code} ({loc.code})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {isLoading ? (
            <p className="text-sm text-muted-foreground">Loading templates...</p>
          ) : filtered.length === 0 ? (
            <p className="text-sm text-muted-foreground">No templates found. Create one to get started.</p>
          ) : (
            <ul className="divide-y rounded-md border">
              {filtered.map((t: Template) => (
                <li key={t.id} className="flex items-center justify-between px-4 py-3">
                  <div className="flex items-center gap-3">
                    <FileText className="w-4 h-4 text-muted-foreground" />
                    <div>
                      <span className="font-medium">
                        {t.locale_code} / {t.channel_code}
                      </span>
                      <span className="text-muted-foreground ml-2">
                        product type #{t.product_type_id} · v{t.version} · {t.status}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button variant="outline" size="sm" asChild>
                      <Link to={`/templates/${t.id}/edit`}>
                        <Pencil className="w-4 h-4 mr-1" />
                        Edit
                      </Link>
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      asChild
                    >
                      <a
                        href={`/admin/pub/generationrun/?template__id__exact=${t.id}`}
                        target="_blank"
                        rel="noreferrer"
                        title="Open generation runs for this template in admin"
                      >
                        Runs
                      </a>
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-destructive hover:text-destructive"
                      onClick={() => setDeleteId(t.id)}
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <AlertDialog open={deleteId !== null} onOpenChange={(open) => !open && setDeleteId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete template?</AlertDialogTitle>
            <AlertDialogDescription>
              This will delete the template and all its parts. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() => deleteId != null && deleteMutation.mutate(deleteId)}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
