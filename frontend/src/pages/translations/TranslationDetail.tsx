import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, Check, Loader2, Save, X, RefreshCw, Clock, CheckCircle, AlertCircle, Play, Info, Pencil } from 'lucide-react';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Progress } from '@/components/ui/progress';
import { useToast } from '@/components/ui/use-toast';
import {
  getProductTranslation,
  getTranslationTask,
  getTranslationTaskResults,
  updateProductTranslation,
  retryTranslationTask,
  updateTranslation,
  ProductTranslationUpdate,
  TranslationResults,
  TranslationResultItem,
  TranslationScope,
} from '@/lib/api';

const scopeLabels: Record<string, string> = {
  product_attribute_value: 'Product Attributes',
  attribute: 'Attribute Names',
  attribute_value: 'Attribute Values',
  product_type: 'Product Types',
};

const scopeDescriptions: Record<string, string> = {
  product_attribute_value: 'Translates the actual values of product attributes (e.g., "Blue", "Large", "Cotton"). These are the specific values assigned to products.',
  attribute: 'Translates the names/labels of attributes (e.g., "Color" -> "Couleur", "Size" -> "Taille"). This helps internationalize your attribute schema.',
  attribute_value: 'Translates the predefined options for enum attributes (e.g., color options like "Red", "Blue", "Green").',
  product_type: 'Translates product type names and category labels used in your catalog structure.',
};

function formatDuration(seconds: number | null): string {
  if (seconds === null || seconds === undefined) return '-';
  if (seconds < 60) return `${seconds} seconds`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  if (minutes < 60) return `${minutes}m ${remainingSeconds}s`;
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return `${hours}h ${remainingMinutes}m`;
}

function formatDateTime(dateStr: string | null): string {
  if (!dateStr) return '-';
  return new Date(dateStr).toLocaleString();
}

export default function TranslationDetail() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const taskId = id;
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const [selectedProductId, setSelectedProductId] = useState<number | null>(null);
  const [editedTitle, setEditedTitle] = useState('');
  const [editedDescription, setEditedDescription] = useState('');
  const [editedMetaTitle, setEditedMetaTitle] = useState('');
  const [editedMetaDescription, setEditedMetaDescription] = useState('');
  const [editedSlug, setEditedSlug] = useState('');
  const [editedAttributes, setEditedAttributes] = useState<Record<number, string>>({});
  
  // Inline editing state for translation results
  const [editingItemId, setEditingItemId] = useState<number | null>(null);
  const [editingValue, setEditingValue] = useState('');
  const [editingCategory, setEditingCategory] = useState('');

  const { data: task, isLoading: isLoadingTask, refetch } = useQuery({
    queryKey: ['translation-task', taskId],
    queryFn: () => getTranslationTask(Number(taskId)),
    enabled: !!taskId,
    // Auto-refresh for pending/in_progress tasks
    refetchInterval: (data) => {
      if (data?.status === 'pending' || data?.status === 'in_progress') {
        return 2000; // Refresh every 2 seconds while processing
      }
      return false;
    },
  });

  const retryMutation = useMutation({
    mutationFn: () => retryTranslationTask(Number(taskId)),
    onSuccess: () => {
      toast({
        title: 'Translation restarted',
        description: 'The translation task has been queued for retry.',
      });
      queryClient.invalidateQueries({ queryKey: ['translation-task', taskId] });
    },
    onError: (error) => {
      toast({
        title: 'Failed to retry translation',
        description: error instanceof Error ? error.message : 'Something went wrong.',
        variant: 'destructive',
      });
    },
  });

  // Mutation for updating individual translation items
  const updateTranslationItemMutation = useMutation({
    mutationFn: async ({ itemId, value, category }: { itemId: number; value: string; category?: string }) => {
      if (!task) throw new Error('Task not found');
      return updateTranslation(
        task.scope as TranslationScope, 
        itemId, 
        { translated_value: value, main_category: category }
      );
    },
    onSuccess: () => {
      toast({
        title: 'Translation updated',
        description: 'The translation has been saved successfully.',
      });
      setEditingItemId(null);
      setEditingValue('');
      setEditingCategory('');
      queryClient.invalidateQueries({ queryKey: ['translation-results', taskId] });
    },
    onError: (error) => {
      toast({
        title: 'Failed to update translation',
        description: error instanceof Error ? error.message : 'Something went wrong.',
        variant: 'destructive',
      });
    },
  });

  const handleStartEdit = (item: TranslationResultItem) => {
    setEditingItemId(item.id);
    setEditingValue(item.translated_value);
    setEditingCategory(item.main_category || '');
  };

  const handleCancelEdit = () => {
    setEditingItemId(null);
    setEditingValue('');
    setEditingCategory('');
  };

  const handleSaveEdit = () => {
    if (editingItemId === null) return;
    updateTranslationItemMutation.mutate({
      itemId: editingItemId,
      value: editingValue,
      category: task?.scope === 'product_type' ? editingCategory : undefined,
    });
  };

  // For product attribute translations, fetch the first product
  const firstProductId = task?.scope === 'product_attribute_value' && task?.target_ids?.[0];

  const { data: productTranslation, isLoading: isLoadingTranslation } = useQuery({
    queryKey: ['product-translation', task?.locale, selectedProductId || firstProductId],
    queryFn: () => getProductTranslation(task!.locale, selectedProductId || firstProductId!),
    enabled: !!task && !!task.locale && !!(selectedProductId || firstProductId),
  });

  // Fetch translation results for non-product scopes (or for any completed task)
  const { data: translationResults, isLoading: isLoadingResults } = useQuery({
    queryKey: ['translation-results', taskId],
    queryFn: () => getTranslationTaskResults(Number(taskId)),
    enabled: !!task && task.status === 'done',
  });

  // Load translation data into edit fields when it arrives
  if (productTranslation && Object.keys(editedAttributes).length === 0 && editedTitle === '') {
    setEditedTitle(productTranslation.title || '');
    setEditedDescription(productTranslation.description || '');
    setEditedMetaTitle(productTranslation.meta_title || '');
    setEditedMetaDescription(productTranslation.meta_description || '');
    setEditedSlug(productTranslation.slug || '');
    
    const attrMap: Record<number, string> = {};
    productTranslation.attributes.forEach((attr) => {
      attrMap[attr.product_attribute_value_id] = attr.translated_value || '';
    });
    setEditedAttributes(attrMap);
  }

  const updateMutation = useMutation({
    mutationFn: async () => {
      if (!task || !productTranslation) return;

      const payload: ProductTranslationUpdate = {
        title: editedTitle,
        description: editedDescription,
        meta_title: editedMetaTitle,
        meta_description: editedMetaDescription,
        slug: editedSlug,
        attribute_values: Object.entries(editedAttributes).map(([id, value]) => ({
          product_attribute_value_id: Number(id),
          value_text: value,
        })),
      };

      return updateProductTranslation(task.locale, productTranslation.product_id, payload);
    },
    onSuccess: () => {
      toast({
        title: 'Translation saved',
        description: 'Your changes have been saved successfully.',
      });
    },
    onError: (error) => {
      toast({
        title: 'Failed to save translation',
        description: error instanceof Error ? error.message : 'Something went wrong.',
        variant: 'destructive',
      });
    },
  });

  const handleAttributeChange = (pavId: number, value: string) => {
    setEditedAttributes((prev) => ({
      ...prev,
      [pavId]: value,
    }));
  };

  if (isLoadingTask) {
    return (
      <div className="page-container flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!task) {
    return (
      <div className="page-container">
        <div className="text-center py-12">
          <h2 className="text-2xl font-bold">Translation task not found</h2>
          <Button className="mt-4" onClick={() => navigate('/translations')}>
            Back to Translations
          </Button>
        </div>
      </div>
    );
  }

  const statusColors: Record<string, string> = {
    pending: 'bg-yellow-100 text-yellow-800',
    in_progress: 'bg-blue-100 text-blue-800',
    done: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800',
  };

  const statusIcons: Record<string, React.ReactNode> = {
    pending: <Clock className="w-4 h-4 mr-1" />,
    in_progress: <Loader2 className="w-4 h-4 mr-1 animate-spin" />,
    done: <CheckCircle className="w-4 h-4 mr-1" />,
    failed: <AlertCircle className="w-4 h-4 mr-1" />,
  };

  return (
    <div className="page-container">
      <PageHeader
        title={`Translation Task #${task.id}`}
        description={`${scopeLabels[task.scope] || task.scope} to ${task.locale}`}
        breadcrumbs={[
          { label: 'Dashboard', href: '/' },
          { label: 'Translations', href: '/translations' },
          { label: `Task #${task.id}` },
        ]}
        actions={
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => navigate('/translations')}>
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back
            </Button>
            <Button variant="outline" onClick={() => refetch()}>
              <RefreshCw className="w-4 h-4 mr-2" />
              Refresh
            </Button>
            {(task.status === 'failed' || task.status === 'done') && (
              <Button 
                variant="outline" 
                onClick={() => retryMutation.mutate()}
                disabled={retryMutation.isPending}
              >
                {retryMutation.isPending ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Play className="w-4 h-4 mr-2" />
                )}
                Retry
              </Button>
            )}
            {productTranslation && (
              <Button onClick={() => updateMutation.mutate()} disabled={updateMutation.isPending}>
                {updateMutation.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save className="w-4 h-4 mr-2" />
                    Save Changes
                  </>
                )}
              </Button>
            )}
          </div>
        }
      />

      {/* What this task does - explanation */}
      <Card className="mb-6 border-blue-200 bg-blue-50">
        <CardHeader className="pb-2">
          <CardTitle className="text-blue-800 flex items-center text-base">
            <Info className="w-4 h-4 mr-2" />
            What this task translates
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-blue-700 text-sm">{scopeDescriptions[task.scope] || 'Translates content.'}</p>
        </CardContent>
      </Card>

      {/* Progress Section */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>Progress</span>
            <span
              className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
                statusColors[task.status] || 'bg-gray-100 text-gray-800'
              }`}
            >
              {statusIcons[task.status]}
              {task.status.replace('_', ' ')}
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* Progress bar */}
            <div>
              <div className="flex items-center justify-between text-sm mb-2">
                <span>
                  {task.items_completed ?? 0} of {task.items_total || '?'} items translated
                </span>
                <span className="font-medium">{task.progress_percent ?? 0}%</span>
              </div>
              <Progress value={task.progress_percent ?? 0} className="h-3" />
            </div>

            {/* Timing info */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4 border-t">
              <div>
                <p className="text-xs text-muted-foreground uppercase tracking-wide">Created</p>
                <p className="text-sm font-medium">{formatDateTime(task.created_at)}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground uppercase tracking-wide">Started</p>
                <p className="text-sm font-medium">{formatDateTime(task.started_at)}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground uppercase tracking-wide">Finished</p>
                <p className="text-sm font-medium">{formatDateTime(task.finished_at)}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground uppercase tracking-wide">Duration</p>
                <p className="text-sm font-medium">{formatDuration(task.duration_seconds)}</p>
              </div>
            </div>

            {/* Model info */}
            <div className="pt-4 border-t">
              <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">AI Model</p>
              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-800">
                {task.model || 'gpt-4o-mini'}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Error display */}
      {task.error && task.status === 'failed' && (
        <Card className="mb-6 border-red-200 bg-red-50">
          <CardHeader>
            <CardTitle className="text-red-800 flex items-center">
              <AlertCircle className="w-5 h-5 mr-2" />
              Translation Failed
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-red-700 mb-4">{task.error}</p>
            <Button 
              variant="outline" 
              className="border-red-300 text-red-700 hover:bg-red-100"
              onClick={() => retryMutation.mutate()}
              disabled={retryMutation.isPending}
            >
              {retryMutation.isPending ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Play className="w-4 h-4 mr-2" />
              )}
              Retry Translation
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Warning display (for done tasks with warnings) */}
      {task.error && task.status === 'done' && (
        <Card className="mb-6 border-yellow-200 bg-yellow-50">
          <CardHeader>
            <CardTitle className="text-yellow-800 flex items-center">
              <AlertCircle className="w-5 h-5 mr-2" />
              Completed with Warnings
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-yellow-700">{task.error}</p>
          </CardContent>
        </Card>
      )}

      {task.status === 'done' && productTranslation && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Product Information</CardTitle>
              <CardDescription>
                Edit the translated product title, description, and metadata.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="title">Title</Label>
                <Input
                  id="title"
                  value={editedTitle}
                  onChange={(e) => setEditedTitle(e.target.value)}
                  placeholder="Product title"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  value={editedDescription}
                  onChange={(e) => setEditedDescription(e.target.value)}
                  placeholder="Product description"
                  rows={4}
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="metaTitle">Meta Title (SEO)</Label>
                  <Input
                    id="metaTitle"
                    value={editedMetaTitle}
                    onChange={(e) => setEditedMetaTitle(e.target.value)}
                    placeholder="SEO meta title"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="slug">URL Slug</Label>
                  <Input
                    id="slug"
                    value={editedSlug}
                    onChange={(e) => setEditedSlug(e.target.value)}
                    placeholder="product-slug"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="metaDescription">Meta Description (SEO)</Label>
                <Textarea
                  id="metaDescription"
                  value={editedMetaDescription}
                  onChange={(e) => setEditedMetaDescription(e.target.value)}
                  placeholder="SEO meta description"
                  rows={2}
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Translated Attributes</CardTitle>
              <CardDescription>
                Review and edit the translated attribute values.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {productTranslation.attributes.map((attr) => (
                  <div key={attr.product_attribute_value_id} className="grid grid-cols-1 md:grid-cols-3 gap-4 items-start pb-4 border-b last:border-b-0">
                    <div>
                      <Label className="text-sm font-medium text-muted-foreground">
                        {attr.attribute_code}
                      </Label>
                      <p className="text-sm mt-1">{attr.source_value}</p>
                    </div>
                    <div className="md:col-span-2">
                      <Label htmlFor={`attr-${attr.product_attribute_value_id}`}>
                        Translated Value
                      </Label>
                      <Input
                        id={`attr-${attr.product_attribute_value_id}`}
                        value={editedAttributes[attr.product_attribute_value_id] || ''}
                        onChange={(e) =>
                          handleAttributeChange(attr.product_attribute_value_id, e.target.value)
                        }
                        placeholder="Translation"
                      />
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {task.status === 'pending' && (
        <Card>
          <CardContent className="py-12 text-center">
            <Clock className="w-12 h-12 text-yellow-500 mx-auto mb-4" />
            <h3 className="text-lg font-semibold">Translation Starting</h3>
            <p className="text-muted-foreground mb-4">
              This translation task is being queued for processing.
            </p>
            <div className="text-sm text-muted-foreground space-y-1">
              <p>Step 1: Task created and queued</p>
              <p>Step 2: Fetching items to translate...</p>
              <p>Step 3: Calling AI translation API...</p>
              <p>Step 4: Saving translated content...</p>
            </div>
          </CardContent>
        </Card>
      )}

      {task.status === 'in_progress' && (
        <Card>
          <CardContent className="py-12 text-center">
            <Loader2 className="w-12 h-12 animate-spin text-blue-500 mx-auto mb-4" />
            <h3 className="text-lg font-semibold">Translation in Progress</h3>
            <p className="text-muted-foreground mb-4">
              AI is currently translating your content using {task.model || 'gpt-4o-mini'}.
            </p>
            <div className="max-w-md mx-auto">
              <div className="flex items-center justify-between text-sm mb-2">
                <span>{task.items_completed ?? 0} / {task.items_total || '?'} items</span>
                <span className="font-medium">{task.progress_percent ?? 0}%</span>
              </div>
              <Progress value={task.progress_percent ?? 0} className="h-2" />
            </div>
            <p className="text-xs text-muted-foreground mt-4">
              This page auto-refreshes every 2 seconds.
            </p>
          </CardContent>
        </Card>
      )}

      {task.status === 'done' && translationResults && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <CheckCircle className="w-5 h-5 text-green-500 mr-2" />
              Translated Items ({translationResults.count})
            </CardTitle>
            <CardDescription>
              {task.scope === 'attribute' && 'Attribute names translated to ' + task.locale}
              {task.scope === 'attribute_value' && 'Attribute value options translated to ' + task.locale}
              {task.scope === 'product_type' && 'Product type names translated to ' + task.locale}
              {task.scope === 'product_attribute_value' && 'Product attribute values translated to ' + task.locale}
              {translationResults.truncated && ` (showing first 100 of ${translationResults.count})`}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isLoadingResults ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
                <span className="ml-2">Loading translations...</span>
              </div>
            ) : translationResults.items.length > 0 ? (
              <div className="border rounded-lg overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-muted">
                    <tr>
                      {(task.scope === 'attribute_value' || task.scope === 'product_attribute_value') && (
                        <th className="px-4 py-2 text-left font-medium">Attribute</th>
                      )}
                      <th className="px-4 py-2 text-left font-medium">Original</th>
                      <th className="px-4 py-2 text-left font-medium">Translated ({task.locale})</th>
                      {task.scope === 'product_type' && (
                        <th className="px-4 py-2 text-left font-medium">Category</th>
                      )}
                      <th className="px-4 py-2 text-right font-medium w-24">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {translationResults.items.map((item) => (
                      <tr key={item.id} className="hover:bg-muted/50">
                        {(task.scope === 'attribute_value' || task.scope === 'product_attribute_value') && (
                          <td className="px-4 py-2 text-muted-foreground font-mono text-xs">
                            {item.attribute_code}
                          </td>
                        )}
                        <td className="px-4 py-2">
                          {item.source_code && item.source_code !== item.source_value ? (
                            <div>
                              <span className="font-mono text-xs text-muted-foreground">{item.source_code}</span>
                              <span className="block">{item.source_value}</span>
                            </div>
                          ) : (
                            item.source_value
                          )}
                        </td>
                        <td className="px-4 py-2">
                          {editingItemId === item.id ? (
                            <Input
                              value={editingValue}
                              onChange={(e) => setEditingValue(e.target.value)}
                              className="h-8"
                              autoFocus
                              onKeyDown={(e) => {
                                if (e.key === 'Enter') handleSaveEdit();
                                if (e.key === 'Escape') handleCancelEdit();
                              }}
                            />
                          ) : (
                            <span className="font-medium text-green-700 dark:text-green-400">
                              {item.translated_value}
                            </span>
                          )}
                        </td>
                        {task.scope === 'product_type' && (
                          <td className="px-4 py-2">
                            {editingItemId === item.id ? (
                              <Input
                                value={editingCategory}
                                onChange={(e) => setEditingCategory(e.target.value)}
                                className="h-8"
                                placeholder="Category"
                                onKeyDown={(e) => {
                                  if (e.key === 'Enter') handleSaveEdit();
                                  if (e.key === 'Escape') handleCancelEdit();
                                }}
                              />
                            ) : (
                              <span className="text-muted-foreground">
                                {item.main_category || '-'}
                              </span>
                            )}
                          </td>
                        )}
                        <td className="px-4 py-2 text-right">
                          {editingItemId === item.id ? (
                            <div className="flex items-center justify-end gap-1">
                              <Button
                                size="sm"
                                variant="ghost"
                                className="h-7 w-7 p-0"
                                onClick={handleSaveEdit}
                                disabled={updateTranslationItemMutation.isPending}
                              >
                                {updateTranslationItemMutation.isPending ? (
                                  <Loader2 className="h-4 w-4 animate-spin" />
                                ) : (
                                  <Check className="h-4 w-4 text-green-600" />
                                )}
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                className="h-7 w-7 p-0"
                                onClick={handleCancelEdit}
                                disabled={updateTranslationItemMutation.isPending}
                              >
                                <X className="h-4 w-4 text-red-600" />
                              </Button>
                            </div>
                          ) : (
                            <Button
                              size="sm"
                              variant="ghost"
                              className="h-7 w-7 p-0"
                              onClick={() => handleStartEdit(item)}
                            >
                              <Pencil className="h-4 w-4 text-muted-foreground" />
                            </Button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <p>No translations found for this task.</p>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {task.status === 'done' && !translationResults && !isLoadingResults && task.scope !== 'product_attribute_value' && (
        <Card>
          <CardContent className="py-12 text-center">
            <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-4" />
            <h3 className="text-lg font-semibold">Translation Complete</h3>
            <p className="text-muted-foreground mb-4">
              Successfully translated {task.items_completed} items to {task.locale}.
            </p>
            <div className="text-sm text-muted-foreground">
              <p>The translations have been saved and are now available in the system.</p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
