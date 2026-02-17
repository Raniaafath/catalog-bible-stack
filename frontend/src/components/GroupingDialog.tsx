import { useState, useEffect } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { AlertCircle, CheckCircle2, Loader2, TrendingUp } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  compareVariants,
  groupVariantsWithAxes,
  getChannels,
  getProductTypes,
  type VariantComparison,
} from '@/lib/api';
import { useToast } from '@/hooks/use-toast';

interface GroupingDialogProps {
  variantIds: number[];
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function GroupingDialog({ variantIds, open, onClose, onSuccess }: GroupingDialogProps) {
  const { toast } = useToast();
  const [selectedChannelId, setSelectedChannelId] = useState<string>('');
  const [selectedAxes, setSelectedAxes] = useState<number[]>([]);
  const [productCode, setProductCode] = useState('');
  const [comparison, setComparison] = useState<VariantComparison | null>(null);

  // Fetch channels
  const { data: channelsData } = useQuery({
    queryKey: ['channels'],
    queryFn: getChannels,
    enabled: open,
  });

  // Fetch product types
  const { data: productTypesData } = useQuery({
    queryKey: ['product-types'],
    queryFn: getProductTypes,
    enabled: open,
  });

  // Compare variants mutation
  const compareMutation = useMutation({
    mutationFn: () => compareVariants(variantIds),
    onSuccess: (data) => {
      setComparison(data);
      
      // Auto-select recommended axes
      const recommendedAxes = data.differences
        .filter(d => d.is_candidate_axis)
        .map(d => d.attribute_id);
      setSelectedAxes(recommendedAxes);

      // Auto-generate product code from first variant SKU
      if (data.variants.length > 0 && data.variants[0].sku) {
        const baseSku = data.variants[0].sku.split('-')[0] || data.variants[0].sku;
        setProductCode(baseSku.toLowerCase());
      }
    },
    onError: (error: any) => {
      toast({
        title: 'Comparison Failed',
        description: error.response?.data?.detail || error.message,
        variant: 'destructive',
      });
    },
  });

  // Group variants mutation
  const groupMutation = useMutation({
    mutationFn: () => {
      if (!selectedChannelId) {
        throw new Error('Channel is required');
      }

      return groupVariantsWithAxes({
        variant_ids: variantIds,
        channel_id: parseInt(selectedChannelId),
        variation_axes: selectedAxes.map((attributeId, index) => ({
          attribute_id: attributeId,
          position: index,
        })),
        create_new_product: true,
        product_code: productCode || undefined,
      });
    },
    onSuccess: (data) => {
      toast({
        title: 'Product Group Created!',
        description: `${data.variants_grouped} variants grouped under "${data.product.code}"`,
      });
      onSuccess();
    },
    onError: (error: any) => {
      toast({
        title: 'Grouping Failed',
        description: error.response?.data?.detail || error.message,
        variant: 'destructive',
      });
    },
  });

  // Run comparison when dialog opens
  useEffect(() => {
    if (open && variantIds.length >= 2 && !comparison) {
      compareMutation.mutate();
    }
  }, [open, variantIds]);

  // Reset state when closing
  useEffect(() => {
    if (!open) {
      setComparison(null);
      setSelectedChannelId('');
      setSelectedAxes([]);
      setProductCode('');
    }
  }, [open]);

  const handleToggleAxis = (attributeId: number, checked: boolean) => {
    if (checked) {
      setSelectedAxes([...selectedAxes, attributeId]);
    } else {
      setSelectedAxes(selectedAxes.filter(id => id !== attributeId));
    }
  };

  const handleSubmit = () => {
    groupMutation.mutate();
  };

  const channels = channelsData?.results || [];
  const isLoading = compareMutation.isPending;
  const isGrouping = groupMutation.isPending;
  const canSubmit = selectedChannelId && selectedAxes.length > 0 && productCode.trim() && !isGrouping;

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Group {variantIds.length} Variants</DialogTitle>
          <DialogDescription>
            Create a product group by selecting a marketplace and variation axes.
          </DialogDescription>
        </DialogHeader>

        {isLoading && (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
            <span className="ml-2 text-sm text-muted-foreground">
              Analyzing variants...
            </span>
          </div>
        )}

        {comparison && (
          <div className="space-y-6">
            {/* Channel Selection */}
            <div className="space-y-2">
              <Label htmlFor="channel">Marketplace / Channel *</Label>
              <Select value={selectedChannelId} onValueChange={setSelectedChannelId}>
                <SelectTrigger id="channel">
                  <SelectValue placeholder="Select a marketplace" />
                </SelectTrigger>
                <SelectContent>
                  {channels.map(channel => (
                    <SelectItem key={channel.id} value={channel.id.toString()}>
                      {channel.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                Different marketplaces can have different variation axes.
              </p>
            </div>

            {/* Detected Differences */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <Label>Detected Differences</Label>
                <Badge variant="secondary">
                  {comparison.differences.length} attribute{comparison.differences.length !== 1 ? 's' : ''} differ
                </Badge>
              </div>

              {comparison.differences.length === 0 && (
                <Alert>
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    No differences detected. These variants appear to be identical.
                  </AlertDescription>
                </Alert>
              )}

              <div className="space-y-2">
                {comparison.differences.map((diff) => (
                  <div
                    key={diff.attribute_id}
                    className="flex items-start gap-3 p-3 rounded-lg border bg-card"
                  >
                    <Checkbox
                      id={`axis-${diff.attribute_id}`}
                      checked={selectedAxes.includes(diff.attribute_id)}
                      onCheckedChange={(checked) =>
                        handleToggleAxis(diff.attribute_id, !!checked)
                      }
                      disabled={!diff.is_candidate_axis}
                    />
                    <div className="flex-1 space-y-1">
                      <div className="flex items-center gap-2">
                        <Label
                          htmlFor={`axis-${diff.attribute_id}`}
                          className="font-medium cursor-pointer"
                        >
                          {diff.attribute_code}
                        </Label>
                        {diff.is_candidate_axis && (
                          <Badge variant="default" className="text-xs">
                            <TrendingUp className="w-3 h-3 mr-1" />
                            Recommended
                          </Badge>
                        )}
                        <Badge variant="outline" className="text-xs">
                          {diff.unique_values_count} value{diff.unique_values_count !== 1 ? 's' : ''}
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        Values: {diff.unique_values.slice(0, 5).join(', ')}
                        {diff.unique_values.length > 5 && ` +${diff.unique_values.length - 5} more`}
                      </p>
                      {diff.has_missing_values && (
                        <p className="text-xs text-orange-600">
                          ⚠️ Some variants are missing this value
                        </p>
                      )}
                      {!diff.is_candidate_axis && diff.unique_values_count > 10 && (
                        <p className="text-xs text-muted-foreground">
                          Too many values ({diff.unique_values_count}) for variation axis
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Common Attributes */}
            {comparison.common_attributes.length > 0 && (
              <div className="space-y-2">
                <Label>Common Attributes (same for all)</Label>
                <div className="flex flex-wrap gap-2">
                  {comparison.common_attributes.map((attr) => (
                    <Badge key={attr.attribute_id} variant="secondary" className="text-xs">
                      {attr.attribute_code}: {attr.common_value}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {/* Product Code */}
            <div className="space-y-2">
              <Label htmlFor="product-code">Product Code *</Label>
              <Input
                id="product-code"
                value={productCode}
                onChange={(e) => setProductCode(e.target.value)}
                placeholder="e.g., mountain-bike"
              />
              <p className="text-xs text-muted-foreground">
                Unique identifier for this product group.
              </p>
            </div>

            {/* Summary */}
            <Alert className="bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800">
              <CheckCircle2 className="h-4 w-4 text-blue-600" />
              <AlertDescription>
                <strong>Summary:</strong> Create product "{productCode || '(unnamed)'}" 
                with {selectedAxes.length} variation {selectedAxes.length !== 1 ? 'axes' : 'axis'} 
                for {variantIds.length} variants.
              </AlertDescription>
            </Alert>
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={isGrouping}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={!canSubmit || isLoading}>
            {isGrouping && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
            Create Product Group
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
