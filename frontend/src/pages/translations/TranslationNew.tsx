import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Languages, Loader2, Play, CheckCircle2, Plus, RefreshCw, Info, Zap, Clock, CheckCircle } from 'lucide-react';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { useToast } from '@/components/ui/use-toast';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import {
  createTranslationTask,
  getLocales,
  getTranslatableAttributes,
  getChannels,
  createLocale,
  getTranslationStatus,
  TranslationScope,
  TranslationTaskCreate,
} from '@/lib/api';

type ExtendedScope = TranslationScope | 'everything';

const scopeOptions: Array<{ value: ExtendedScope; label: string; description: string; example: string; highlight?: boolean }> = [
  {
    value: 'everything',
    label: 'Translate Everything',
    description: 'Translate all untranslated attribute names AND product attribute values in one go',
    example: 'Recommended for new languages - translates all missing content',
    highlight: true,
  },
  {
    value: 'product_attribute_value',
    label: 'Product Attributes',
    description: 'Translate the actual values assigned to products (e.g., color names, materials, sizes)',
    example: 'Example: "Blue" -> "Bleu", "Cotton" -> "Coton"',
  },
  {
    value: 'attribute',
    label: 'Attribute Names',
    description: 'Translate attribute labels/names used in your schema',
    example: 'Example: "Color" -> "Couleur", "Size" -> "Taille"',
  },
  {
    value: 'attribute_value',
    label: 'Attribute Value Options',
    description: 'Translate predefined options for enum/select attributes',
    example: 'Example: Color options "Red", "Blue", "Green"',
  },
  {
    value: 'product_type',
    label: 'Product Types',
    description: 'Translate product category and type names',
    example: 'Example: "T-Shirts" -> "T-shirts", "Running Shoes" -> "Chaussures de course"',
  },
];

const modelOptions = [
  {
    value: 'gpt-4o-mini',
    label: 'GPT-4o Mini',
    description: 'Fastest and most cost-effective. Best for large batches.',
    speed: '~100 items/min',
    badge: 'Recommended',
    badgeVariant: 'default' as const,
  },
  {
    value: 'gpt-4o',
    label: 'GPT-4o',
    description: 'Balanced performance and quality. Good for mixed content.',
    speed: '~50 items/min',
    badge: 'Balanced',
    badgeVariant: 'secondary' as const,
  },
  {
    value: 'gpt-4-turbo',
    label: 'GPT-4 Turbo',
    description: 'Highest quality translations. Best for marketing content.',
    speed: '~30 items/min',
    badge: 'Premium',
    badgeVariant: 'outline' as const,
  },
];

export default function TranslationNew() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const [scope, setScope] = useState<ExtendedScope>('everything');
  const [locale, setLocale] = useState('');
  const [model, setModel] = useState('gpt-4o-mini');
  const [selectedAttributeIds, setSelectedAttributeIds] = useState<number[]>([]);
  const [selectAll, setSelectAll] = useState(false);
  const [channelId, setChannelId] = useState<number | null>(null);
  const [showAddLocaleDialog, setShowAddLocaleDialog] = useState(false);
  const [newLocaleCode, setNewLocaleCode] = useState('');
  const [newLocaleName, setNewLocaleName] = useState('');

  const { data: locales } = useQuery({
    queryKey: ['locales'],
    queryFn: getLocales,
  });

  const { data: channels } = useQuery({
    queryKey: ['channels'],
    queryFn: getChannels,
  });

  const { data: translatableAttributes, isLoading: attributesLoading, refetch: refetchAttributes } = useQuery({
    queryKey: ['translatable-attributes'],
    queryFn: getTranslatableAttributes,
    enabled: scope === 'product_attribute_value',
  });

  // Fetch translation status when "everything" scope is selected and locale is chosen
  const { data: translationStatus, isLoading: statusLoading, refetch: refetchStatus } = useQuery({
    queryKey: ['translation-status', locale],
    queryFn: () => getTranslationStatus(locale),
    enabled: scope === 'everything' && !!locale,
  });

  const createMutation = useMutation({
    mutationFn: async () => {
      if (!locale) {
        throw new Error('Please select a target language');
      }

      // Handle "everything" scope - create multiple tasks
      if (scope === 'everything') {
        const tasks = [];
        
        // Create task for attribute names (if any untranslated)
        if (!translationStatus || translationStatus.attributes.untranslated > 0) {
          tasks.push(createTranslationTask({
            scope: 'attribute',
            locale,
            target_ids: [],
            model,
            channel_id: channelId || null,
          }));
        }
        
        // Create task for product attribute values (if any untranslated)
        if (!translationStatus || translationStatus.product_attribute_values.untranslated > 0) {
          tasks.push(createTranslationTask({
            scope: 'product_attribute_value',
            locale,
            target_ids: [],
            model,
            channel_id: channelId || null,
          }));
        }
        
        if (tasks.length === 0) {
          throw new Error('Everything is already translated for this language!');
        }
        
        // Execute all tasks in parallel
        const results = await Promise.all(tasks);
        return results[0]; // Return the first task for navigation
      }

      let targetIds: number[] = [];
      
      if (scope === 'product_attribute_value') {
        if (!selectAll && selectedAttributeIds.length === 0) {
          throw new Error('Please select at least one attribute or choose "Select All"');
        }
        // For product attributes, we don't specify target_ids to translate all values
        // The backend will handle filtering by attribute
        targetIds = selectAll ? [] : selectedAttributeIds;
      }

      const payload: TranslationTaskCreate = {
        scope: scope as TranslationScope,
        locale,
        target_ids: targetIds,
        model,
        channel_id: channelId || null,
      };

      return createTranslationTask(payload);
    },
    onSuccess: (task) => {
      const message = scope === 'everything' 
        ? 'Translation tasks created for all untranslated content. Processing will start automatically.'
        : `Task #${task.id} is now ${task.status}. Processing will start automatically.`;
      toast({
        title: scope === 'everything' ? 'Translation tasks created' : 'Translation task created',
        description: message,
      });
      navigate('/translations');
    },
    onError: (error) => {
      toast({
        title: 'Failed to create translation task',
        description: error instanceof Error ? error.message : 'Something went wrong.',
        variant: 'destructive',
      });
    },
  });

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    createMutation.mutate();
  };

  const handleToggleAttribute = (attributeId: number, checked: boolean) => {
    if (checked) {
      setSelectedAttributeIds([...selectedAttributeIds, attributeId]);
    } else {
      setSelectedAttributeIds(selectedAttributeIds.filter(id => id !== attributeId));
      setSelectAll(false);
    }
  };

  const handleSelectAll = (checked: boolean) => {
    setSelectAll(checked);
    if (checked && translatableAttributes?.results) {
      setSelectedAttributeIds(translatableAttributes.results.map(attr => attr.id));
    } else {
      setSelectedAttributeIds([]);
    }
  };

  const getTotalValueCount = () => {
    if (!translatableAttributes?.results) return 0;
    if (selectAll) {
      return translatableAttributes.results.reduce((sum, attr) => sum + attr.translatable_value_count, 0);
    }
    return translatableAttributes.results
      .filter(attr => selectedAttributeIds.includes(attr.id))
      .reduce((sum, attr) => sum + attr.translatable_value_count, 0);
  };

  const createLocaleMutation = useMutation({
    mutationFn: async () => {
      if (!newLocaleCode.trim()) {
        throw new Error('Locale code is required');
      }
      return createLocale({
        code: newLocaleCode.trim().toLowerCase(),
        name: newLocaleName.trim() || undefined,
      });
    },
    onSuccess: (newLocale) => {
      queryClient.invalidateQueries({ queryKey: ['locales'] });
      setLocale(newLocale.code);
      setShowAddLocaleDialog(false);
      setNewLocaleCode('');
      setNewLocaleName('');
      toast({
        title: 'Language added',
        description: `Language "${newLocale.code}" has been added successfully.`,
      });
    },
    onError: (error) => {
      toast({
        title: 'Failed to add language',
        description: error instanceof Error ? error.message : 'Something went wrong.',
        variant: 'destructive',
      });
    },
  });

  return (
    <div className="page-container">
      <PageHeader
        title="New Translation Task"
        description="Translate attributes, values, or product types into any language using AI. Select attributes to translate all related values automatically."
        breadcrumbs={[
          { label: 'Dashboard', href: '/' },
          { label: 'Translations', href: '/translations' },
          { label: 'New Task' },
        ]}
      />

      {/* How it works - info section */}
      <Alert className="border-blue-200 bg-blue-50 dark:bg-blue-950/20">
        <Info className="h-4 w-4 text-blue-600" />
        <AlertTitle className="text-blue-800 dark:text-blue-200">How Translation Works</AlertTitle>
        <AlertDescription className="text-blue-700 dark:text-blue-300">
          <div className="mt-2 space-y-2 text-sm">
            <div className="flex items-start gap-2">
              <span className="flex-shrink-0 w-5 h-5 rounded-full bg-blue-200 dark:bg-blue-800 flex items-center justify-center text-xs font-medium">1</span>
              <span>Create a task by selecting what to translate and the target language</span>
            </div>
            <div className="flex items-start gap-2">
              <span className="flex-shrink-0 w-5 h-5 rounded-full bg-blue-200 dark:bg-blue-800 flex items-center justify-center text-xs font-medium">2</span>
              <span>Translation starts automatically in the background using AI</span>
            </div>
            <div className="flex items-start gap-2">
              <span className="flex-shrink-0 w-5 h-5 rounded-full bg-blue-200 dark:bg-blue-800 flex items-center justify-center text-xs font-medium">3</span>
              <span>Monitor progress in real-time on the task detail page</span>
            </div>
            <div className="flex items-start gap-2">
              <span className="flex-shrink-0 w-5 h-5 rounded-full bg-blue-200 dark:bg-blue-800 flex items-center justify-center text-xs font-medium">4</span>
              <span>Translations are saved and immediately available in the system</span>
            </div>
          </div>
        </AlertDescription>
      </Alert>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Step 1: Translation Scope */}
        <Card>
          <CardHeader>
            <CardTitle>Step 1: What to Translate</CardTitle>
            <CardDescription>Choose what type of content you want to translate.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {scopeOptions.map((option) => (
                <div
                  key={option.value}
                  className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
                    scope === option.value
                      ? option.highlight 
                        ? 'border-green-500 bg-green-50 dark:bg-green-950/20'
                        : 'border-primary bg-primary/5'
                      : option.highlight
                        ? 'border-green-200 hover:border-green-400 bg-green-50/50 dark:bg-green-950/10'
                        : 'border-border hover:border-primary/50'
                  } ${option.highlight ? 'md:col-span-2' : ''}`}
                  onClick={() => setScope(option.value)}
                >
                  <div className="flex items-start gap-3">
                    {option.highlight && (
                      <Zap className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
                    )}
                    <div className="mt-0.5">
                      <div
                        className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${
                          scope === option.value ? 'border-primary' : 'border-border'
                        }`}
                      >
                        {scope === option.value && (
                          <div className="w-3 h-3 rounded-full bg-primary" />
                        )}
                      </div>
                    </div>
                    <div className="flex-1">
                      <div className="font-medium mb-1">{option.label}</div>
                      <div className="text-sm text-muted-foreground">{option.description}</div>
                      <div className="text-xs text-muted-foreground mt-1 italic">{option.example}</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Step 2: Translation Status (only for everything scope) */}
        {scope === 'everything' && locale && (
          <Card className="border-green-200">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CheckCircle className="w-5 h-5 text-green-600" />
                Step 2: Translation Status for {locale.toUpperCase()}
              </CardTitle>
              <CardDescription>
                Overview of what needs to be translated. Tasks will only be created for content that hasn't been translated yet.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {statusLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
                  <span className="ml-2">Checking translation status...</span>
                </div>
              ) : translationStatus ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Attribute Names */}
                    <div className="p-4 border rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium">Attribute Names</span>
                        {translationStatus.attributes.untranslated > 0 ? (
                          <Badge variant="destructive">{translationStatus.attributes.untranslated} to translate</Badge>
                        ) : (
                          <Badge variant="outline" className="text-green-600 border-green-600">All done</Badge>
                        )}
                      </div>
                      <div className="text-sm text-muted-foreground">
                        {translationStatus.attributes.translated} / {translationStatus.attributes.total} translated
                      </div>
                      <Progress 
                        value={translationStatus.attributes.total > 0 
                          ? (translationStatus.attributes.translated / translationStatus.attributes.total) * 100 
                          : 100
                        } 
                        className="h-2 mt-2" 
                      />
                    </div>

                    {/* Product Attribute Values */}
                    <div className="p-4 border rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium">Product Attribute Values</span>
                        {translationStatus.product_attribute_values.untranslated > 0 ? (
                          <Badge variant="destructive">{translationStatus.product_attribute_values.untranslated} to translate</Badge>
                        ) : (
                          <Badge variant="outline" className="text-green-600 border-green-600">All done</Badge>
                        )}
                      </div>
                      <div className="text-sm text-muted-foreground">
                        {translationStatus.product_attribute_values.translated} / {translationStatus.product_attribute_values.total} translated
                      </div>
                      <Progress 
                        value={translationStatus.product_attribute_values.total > 0 
                          ? (translationStatus.product_attribute_values.translated / translationStatus.product_attribute_values.total) * 100 
                          : 100
                        } 
                        className="h-2 mt-2" 
                      />
                    </div>
                  </div>

                  {/* Summary */}
                  <div className="p-4 bg-muted/50 rounded-lg">
                    <div className="flex items-center gap-2 mb-2">
                      <Info className="w-4 h-4 text-muted-foreground" />
                      <span className="font-medium">What will be translated:</span>
                    </div>
                    <ul className="text-sm text-muted-foreground space-y-1 ml-6">
                      {translationStatus.attributes.untranslated > 0 && (
                        <li>• {translationStatus.attributes.untranslated} attribute names (Color, Size, Material, etc.)</li>
                      )}
                      {translationStatus.product_attribute_values.untranslated > 0 && (
                        <li>• {translationStatus.product_attribute_values.untranslated} product attribute values (Blue, Large, Cotton, etc.)</li>
                      )}
                      {translationStatus.attributes.untranslated === 0 && translationStatus.product_attribute_values.untranslated === 0 && (
                        <li className="text-green-600">Everything is already translated for this language!</li>
                      )}
                    </ul>
                  </div>

                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => refetchStatus()}
                  >
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Refresh Status
                  </Button>
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <p>Select a language to see translation status.</p>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Step 2: Select Attributes (only for product_attribute_value scope) */}
        {scope === 'product_attribute_value' && (
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Step 2: Select Attributes</CardTitle>
                  <CardDescription>
                    Choose which attributes to translate. All product attribute values for the selected attributes will be translated automatically across all products.
                  </CardDescription>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => refetchAttributes()}
                    disabled={attributesLoading}
                  >
                    <RefreshCw className={`w-4 h-4 mr-2 ${attributesLoading ? 'animate-spin' : ''}`} />
                    Refresh
                  </Button>
                  <Checkbox
                    id="select-all"
                    checked={selectAll}
                    onCheckedChange={handleSelectAll}
                  />
                  <Label htmlFor="select-all" className="cursor-pointer">
                    Select All
                  </Label>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="mb-4 p-3 bg-blue-50 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                <p className="text-sm text-blue-900 dark:text-blue-200">
                  <strong>How it works:</strong> Select the attributes you want to translate. The system will automatically find and translate all product attribute values for these attributes across all products. No need to manually select individual products.
                </p>
              </div>
              {attributesLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
                  <span className="ml-2 text-sm text-muted-foreground">Loading attributes...</span>
                </div>
              ) : translatableAttributes?.results && translatableAttributes.results.length > 0 ? (
                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {translatableAttributes.results.map((attr) => (
                    <div
                      key={attr.id}
                      className="flex items-start gap-3 p-3 rounded-lg border bg-card hover:bg-accent/50 transition-colors"
                    >
                      <Checkbox
                        id={`attr-${attr.id}`}
                        checked={selectedAttributeIds.includes(attr.id)}
                        onCheckedChange={(checked) => handleToggleAttribute(attr.id, !!checked)}
                      />
                      <div className="flex-1 space-y-1">
                        <Label htmlFor={`attr-${attr.id}`} className="font-medium cursor-pointer">
                          {attr.code}
                        </Label>
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className="text-xs">
                            {attr.translatable_value_count} value{attr.translatable_value_count !== 1 ? 's' : ''}
                          </Badge>
                          {attr.product_types.length > 0 && (
                            <span className="text-xs text-muted-foreground">
                              Used in: {attr.product_types.map(pt => pt.code).join(', ')}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <Languages className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p className="font-medium mb-2">No translatable attributes found.</p>
                  <p className="text-sm mb-4">
                    To translate attributes, you need to mark them as translatable first.
                  </p>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => navigate('/attributes')}
                    className="mt-2"
                  >
                    Go to Attributes Page
                  </Button>
                  <p className="text-xs mt-4 text-muted-foreground">
                    On the Attributes page, toggle the "Translatable" checkbox for attributes you want to translate.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Step 3: Target Language */}
        <Card>
          <CardHeader>
            <CardTitle>Step {scope === 'product_attribute_value' ? '3' : '2'}: Target Language</CardTitle>
            <CardDescription>Select the language to translate into.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <Label htmlFor="locale" className="font-semibold">
                Language <span className="text-red-500">*</span>
              </Label>
              <div className="flex gap-2">
                <Select value={locale} onValueChange={setLocale}>
                  <SelectTrigger id="locale" className={!locale ? 'border-red-300' : ''}>
                    <SelectValue placeholder="Select target language..." />
                  </SelectTrigger>
                  <SelectContent>
                    {locales?.results?.map((loc) => (
                      <SelectItem key={loc.code} value={loc.code}>
                        {loc.name || loc.code} ({loc.code})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setShowAddLocaleDialog(true)}
                  className="shrink-0"
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Add Language
                </Button>
              </div>
              {!locale && <span className="text-xs text-red-500">This field is required</span>}
            </div>
          </CardContent>
        </Card>

        {/* Step 3.5: Target Channel (Optional) */}
        <Card>
          <CardHeader>
            <CardTitle>Step {scope === 'product_attribute_value' ? '3.5' : '2.5'}: Target Channel (Optional)</CardTitle>
            <CardDescription>Select a specific sales channel if needed.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <Label htmlFor="channel">Channel</Label>
              <Select
                value={channelId?.toString() || 'none'}
                onValueChange={(value) => setChannelId(value === 'none' ? null : parseInt(value))}
              >
                <SelectTrigger id="channel">
                  <SelectValue placeholder="Select a channel (optional)" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">No specific channel</SelectItem>
                  {channels?.results?.map((channel) => (
                    <SelectItem key={channel.id} value={channel.id.toString()}>
                      {channel.name || channel.code} ({channel.code})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                Specify if targeting a specific sales channel (Amazon, eBay, Shopify, etc.)
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Step 4: AI Model Selection */}
        <Card>
          <CardHeader>
            <CardTitle>Step {scope === 'product_attribute_value' ? '4' : '3'}: AI Model</CardTitle>
            <CardDescription>Choose the AI model for translation quality and speed.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {modelOptions.map((option) => (
              <div
                key={option.value}
                className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
                  model === option.value
                    ? 'border-primary bg-primary/5'
                    : 'border-border hover:border-primary/50'
                }`}
                onClick={() => setModel(option.value)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5">
                      <div
                        className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${
                          model === option.value ? 'border-primary' : 'border-border'
                        }`}
                      >
                        {model === option.value && (
                          <div className="w-3 h-3 rounded-full bg-primary" />
                        )}
                      </div>
                    </div>
                    <div>
                      <div className="font-medium mb-1">{option.label}</div>
                      <div className="text-sm text-muted-foreground">{option.description}</div>
                      <div className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
                        <Zap className="w-3 h-3" />
                        Speed: {option.speed}
                      </div>
                    </div>
                  </div>
                  <Badge variant={option.badgeVariant}>
                    {option.badge}
                  </Badge>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Step 5: Review & Submit */}
        <Card className="border-primary/20">
          <CardHeader>
            <CardTitle>Review & Start Translation</CardTitle>
            <CardDescription>Confirm your translation settings.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <div className="text-sm text-muted-foreground mb-1">Scope</div>
                <div className="font-medium">{scopeOptions.find(s => s.value === scope)?.label}</div>
              </div>
              {scope === 'everything' && translationStatus && (
                <>
                  <div>
                    <div className="text-sm text-muted-foreground mb-1">Attribute Names</div>
                    <div className="font-medium">
                      {translationStatus.attributes.untranslated} to translate
                    </div>
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground mb-1">Product Values</div>
                    <div className="font-medium">
                      {translationStatus.product_attribute_values.untranslated} to translate
                    </div>
                  </div>
                </>
              )}
              {scope === 'product_attribute_value' && (
                <>
                  <div>
                    <div className="text-sm text-muted-foreground mb-1">Attributes</div>
                    <div className="font-medium">
                      {selectAll ? 'All' : selectedAttributeIds.length} selected
                    </div>
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground mb-1">Total Values</div>
                    <div className="font-medium">{getTotalValueCount()}</div>
                  </div>
                </>
              )}
              <div>
                <div className="text-sm text-muted-foreground mb-1">Language</div>
                <div className="font-medium">{locale || '—'}</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground mb-1">Channel</div>
                <div className="font-medium">
                  {channelId
                    ? channels?.results?.find((c) => c.id === channelId)?.name || channels?.results?.find((c) => c.id === channelId)?.code || '—'
                    : 'All channels'}
                </div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground mb-1">AI Model</div>
                <div className="font-medium">{modelOptions.find(m => m.value === model)?.label}</div>
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-4 border-t">
              <Button type="button" variant="outline" onClick={() => navigate('/translations')}>
                Cancel
              </Button>
              <Button 
                type="submit" 
                disabled={
                  !locale || 
                  createMutation.isPending || 
                  (scope === 'everything' && translationStatus && 
                    translationStatus.attributes.untranslated === 0 && 
                    translationStatus.product_attribute_values.untranslated === 0)
                }
              >
                {createMutation.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Creating...
                  </>
                ) : scope === 'everything' ? (
                  <>
                    <Zap className="w-4 h-4 mr-2" />
                    Translate Everything
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 mr-2" />
                    Start Translation
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      </form>

      {/* Add Locale Dialog */}
      <Dialog open={showAddLocaleDialog} onOpenChange={setShowAddLocaleDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add a New Language</DialogTitle>
            <DialogDescription>
              Create a new locale for translation. Enter the language code (e.g., "de" for German, "es" for Spanish).
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="locale-code">
                Language Code <span className="text-red-500">*</span>
              </Label>
              <Input
                id="locale-code"
                placeholder="e.g., de, es, it"
                value={newLocaleCode}
                onChange={(e) => setNewLocaleCode(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && newLocaleCode.trim()) {
                    createLocaleMutation.mutate();
                  }
                }}
              />
              <p className="text-xs text-muted-foreground">
                ISO 639-1 language code (2-5 characters, lowercase)
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="locale-name">Language Name (Optional)</Label>
              <Input
                id="locale-name"
                placeholder="e.g., German, Spanish, Italian"
                value={newLocaleName}
                onChange={(e) => setNewLocaleName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && newLocaleCode.trim()) {
                    createLocaleMutation.mutate();
                  }
                }}
              />
              <p className="text-xs text-muted-foreground">
                Human-readable name for the language
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setShowAddLocaleDialog(false);
                setNewLocaleCode('');
                setNewLocaleName('');
              }}
            >
              Cancel
            </Button>
            <Button
              type="button"
              onClick={() => createLocaleMutation.mutate()}
              disabled={!newLocaleCode.trim() || createLocaleMutation.isPending}
            >
              {createLocaleMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Adding...
                </>
              ) : (
                <>
                  <Plus className="w-4 h-4 mr-2" />
                  Add Language
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
