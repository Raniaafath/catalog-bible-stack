import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowRight, Tag, Loader2 } from 'lucide-react';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { getImport, getProductTypes, assignCategory } from '@/lib/api';

export default function ImportAssignCategory() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const importId = Number(id);

  const [category, setCategory] = useState('');
  const [customCategory, setCustomCategory] = useState('');

  const { data: importData, isLoading: importLoading } = useQuery({
    queryKey: ['import', importId],
    queryFn: () => getImport(importId),
    enabled: !!importId,
  });

  const { data: productTypes, isLoading: typesLoading } = useQuery({
    queryKey: ['product-types'],
    queryFn: getProductTypes,
  });

  const assignMutation = useMutation({
    mutationFn: (cat: string) => assignCategory(importId, cat),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['import', importId] });
      navigate(`/imports/${id}/map-attributes`);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const finalCategory = category === 'custom' ? customCategory : category;
    if (finalCategory) {
      assignMutation.mutate(finalCategory);
    }
  };

  const isLoading = importLoading || typesLoading;

  if (isLoading) {
    return (
      <div className="page-container flex items-center justify-center min-h-[50vh]">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="page-container">
      <PageHeader
        title="Assign Category"
        description="Select or create a product category for this import"
        breadcrumbs={[
          { label: 'Dashboard', href: '/' },
          { label: 'Imports', href: '/imports' },
          { label: importData?.filename || `Import #${id}`, href: `/imports/${id}` },
          { label: 'Assign Category' },
        ]}
      />

      <div className="max-w-xl mx-auto">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Tag className="w-5 h-5" />
              Product Category
            </CardTitle>
            <CardDescription>
              Choose an existing product type or create a new one for the imported products.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="category">Category</Label>
                <Select value={category} onValueChange={setCategory}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select a category..." />
                  </SelectTrigger>
                  <SelectContent>
                    {productTypes?.results?.map((type) => (
                      <SelectItem key={type.id} value={type.slug}>
                        {type.name}
                      </SelectItem>
                    ))}
                    <SelectItem value="custom">+ Create new category</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {category === 'custom' && (
                <div className="space-y-2">
                  <Label htmlFor="customCategory">New Category Name</Label>
                  <Input
                    id="customCategory"
                    value={customCategory}
                    onChange={(e) => setCustomCategory(e.target.value)}
                    placeholder="e.g., Electronics, Clothing, Furniture..."
                  />
                </div>
              )}

              <div className="flex justify-end gap-3">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => navigate(`/imports/${id}`)}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={!category || (category === 'custom' && !customCategory) || assignMutation.isPending}
                >
                  {assignMutation.isPending ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : null}
                  Continue to Mapping
                  <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
