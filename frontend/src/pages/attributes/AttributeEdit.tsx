import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useMutation, useQuery } from '@tanstack/react-query';
import { ArrowLeft, Save, Loader2 } from 'lucide-react';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { useToast } from '@/components/ui/use-toast';
import {
  getAttribute,
  createAttribute,
  updateAttribute,
  Attribute,
} from '@/lib/api';

const dataTypeOptions = [
  { value: 'text', label: 'Text' },
  { value: 'number', label: 'Number' },
  { value: 'bool', label: 'Boolean' },
  { value: 'enum', label: 'Enum' },
  { value: 'json', label: 'JSON' },
];

export default function AttributeEdit() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const { toast } = useToast();
  const isNew = id === 'new';

  const [formData, setFormData] = useState<Partial<Attribute>>({
    code: '',
    data_type: 'text',
    unit: '',
    is_multi: false,
    is_value_translatable: false,
  });

  const { data: attribute, isLoading } = useQuery({
    queryKey: ['attribute', id],
    queryFn: () => getAttribute(Number(id)),
    enabled: !isNew && !!id,
  });

  useEffect(() => {
    if (attribute) {
      setFormData({
        code: attribute.code,
        data_type: attribute.data_type,
        unit: attribute.unit || '',
        is_multi: attribute.is_multi || false,
        is_value_translatable: attribute.is_value_translatable || false,
      });
    }
  }, [attribute]);

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (isNew) {
        return createAttribute(formData as Omit<Attribute, 'id' | 'created_at'>);
      } else {
        return updateAttribute(Number(id), formData);
      }
    },
    onSuccess: () => {
      toast({
        title: isNew ? 'Attribute created' : 'Attribute updated',
        description: `The attribute has been ${isNew ? 'created' : 'updated'} successfully.`,
      });
      navigate('/attributes');
    },
    onError: (error: any) => {
      toast({
        title: `Failed to ${isNew ? 'create' : 'update'} attribute`,
        description: error?.response?.data?.detail || error?.message || 'Something went wrong.',
        variant: 'destructive',
      });
    },
  });

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

  if (!isNew && isLoading) {
    return (
      <div className="page-container">
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <PageHeader
        title={isNew ? 'Create Attribute' : 'Edit Attribute'}
        description={isNew ? 'Create a new product attribute.' : 'Edit attribute details.'}
        breadcrumbs={[
          { label: 'Dashboard', href: '/' },
          { label: 'Attributes', href: '/attributes' },
          { label: isNew ? 'New' : 'Edit' },
        ]}
      />

      <form onSubmit={handleSubmit} className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Attribute Details</CardTitle>
            <CardDescription>Configure the attribute properties.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="code">
                Code <span className="text-red-500">*</span>
              </Label>
              <Input
                id="code"
                value={formData.code || ''}
                onChange={(e) => setFormData({ ...formData, code: e.target.value })}
                placeholder="e.g., color, material, size"
                disabled={!isNew}
                required
              />
              <p className="text-xs text-muted-foreground">
                Unique identifier for the attribute (slug format, lowercase, no spaces)
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="data_type">
                Data Type <span className="text-red-500">*</span>
              </Label>
              <Select
                value={formData.data_type}
                onValueChange={(value: Attribute['data_type']) =>
                  setFormData({ ...formData, data_type: value })
                }
                disabled={!isNew}
              >
                <SelectTrigger id="data_type">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {dataTypeOptions.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="unit">Unit (Optional)</Label>
              <Input
                id="unit"
                value={formData.unit || ''}
                onChange={(e) => setFormData({ ...formData, unit: e.target.value })}
                placeholder="e.g., kg, cm, ml"
              />
              <p className="text-xs text-muted-foreground">
                Unit of measurement for numeric attributes
              </p>
            </div>

            <div className="flex items-center space-x-2">
              <Checkbox
                id="is_multi"
                checked={formData.is_multi || false}
                onCheckedChange={(checked) =>
                  setFormData({ ...formData, is_multi: Boolean(checked) })
                }
              />
              <Label htmlFor="is_multi" className="cursor-pointer">
                Allow multiple values
              </Label>
            </div>

            <div className="flex items-center space-x-2">
              <Checkbox
                id="is_value_translatable"
                checked={formData.is_value_translatable || false}
                onCheckedChange={(checked) =>
                  setFormData({ ...formData, is_value_translatable: Boolean(checked) })
                }
              />
              <Label htmlFor="is_value_translatable" className="cursor-pointer">
                Translatable (values can be translated to other languages)
              </Label>
            </div>
          </CardContent>
        </Card>

        <div className="flex justify-end gap-3">
          <Button type="button" variant="outline" onClick={() => navigate('/attributes')}>
            <ArrowLeft className="w-4 h-4 mr-2" />
            Cancel
          </Button>
          <Button type="submit" disabled={saveMutation.isPending}>
            {saveMutation.isPending ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save className="w-4 h-4 mr-2" />
                Save
              </>
            )}
          </Button>
        </div>
      </form>
    </div>
  );
}
