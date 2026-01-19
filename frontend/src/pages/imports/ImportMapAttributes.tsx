import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowRight, Link2, Plus, Loader2, CheckCircle2 } from 'lucide-react';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { getImport, getImportPreview, getAttributes, mapAttributes, AttributeMapping } from '@/lib/api';

export default function ImportMapAttributes() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const importId = Number(id);

  const [mappings, setMappings] = useState<Record<string, AttributeMapping>>({});

  const { data: importData, isLoading: importLoading } = useQuery({
    queryKey: ['import', importId],
    queryFn: () => getImport(importId),
    enabled: !!importId,
  });

  const { data: previewData, isLoading: previewLoading } = useQuery({
    queryKey: ['import-preview', importId],
    queryFn: () => getImportPreview(importId),
    enabled: !!importId,
  });

  const { data: attributes, isLoading: attributesLoading } = useQuery({
    queryKey: ['attributes'],
    queryFn: getAttributes,
  });

  const mapMutation = useMutation({
    mutationFn: (mappingsList: AttributeMapping[]) => mapAttributes(importId, mappingsList),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['import', importId] });
      navigate(`/imports/${id}`);
    },
  });

  const handleMappingChange = (column: string, field: keyof AttributeMapping, value: unknown) => {
    setMappings((prev) => ({
      ...prev,
      [column]: {
        ...prev[column],
        file_column: column,
        [field]: value,
      },
    }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const mappingsList = Object.values(mappings).filter(
      (m) => m.db_attribute || m.create_new
    );
    mapMutation.mutate(mappingsList);
  };

  const isLoading = importLoading || previewLoading || attributesLoading;

  if (isLoading) {
    return (
      <div className="page-container flex items-center justify-center min-h-[50vh]">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  const headers = previewData?.headers || [];

  return (
    <div className="page-container">
      <PageHeader
        title="Map Attributes"
        description="Connect file columns to database attributes"
        breadcrumbs={[
          { label: 'Dashboard', href: '/' },
          { label: 'Imports', href: '/imports' },
          { label: importData?.filename || `Import #${id}`, href: `/imports/${id}` },
          { label: 'Map Attributes' },
        ]}
      />

      <form onSubmit={handleSubmit}>
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Link2 className="w-5 h-5" />
              Column Mapping
            </CardTitle>
            <CardDescription>
              Map each file column to an existing database attribute or create a new one.
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>File Column</th>
                    <th>Sample Data</th>
                    <th>Database Attribute</th>
                    <th>Create New</th>
                  </tr>
                </thead>
                <tbody>
                  {headers.map((header, i) => {
                    const mapping = mappings[header] || { file_column: header, db_attribute: null, create_new: false };
                    const sampleValues = previewData?.rows
                      .slice(0, 3)
                      .map((r) => r[header])
                      .filter(Boolean)
                      .join(', ');

                    return (
                      <tr key={i}>
                        <td className="font-medium">{header}</td>
                        <td className="text-muted-foreground text-sm max-w-[200px] truncate">
                          {sampleValues || '—'}
                        </td>
                        <td>
                          <Select
                            value={mapping.db_attribute?.toString() || ''}
                            onValueChange={(val) =>
                              handleMappingChange(header, 'db_attribute', val ? Number(val) : null)
                            }
                            disabled={mapping.create_new}
                          >
                            <SelectTrigger className="w-[200px]">
                              <SelectValue placeholder="Select attribute..." />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="">— Skip —</SelectItem>
                              {attributes?.results.map((attr) => (
                                <SelectItem key={attr.id} value={attr.id.toString()}>
                                  {attr.name}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </td>
                        <td>
                          <div className="flex items-center gap-3">
                            <Checkbox
                              id={`create-${i}`}
                              checked={mapping.create_new}
                              onCheckedChange={(checked) =>
                                handleMappingChange(header, 'create_new', !!checked)
                              }
                            />
                            {mapping.create_new && (
                              <Input
                                placeholder="New attribute name"
                                className="w-[160px]"
                                value={mapping.new_attribute_name || ''}
                                onChange={(e) =>
                                  handleMappingChange(header, 'new_attribute_name', e.target.value)
                                }
                              />
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        <div className="flex justify-end gap-3">
          <Button
            type="button"
            variant="outline"
            onClick={() => navigate(`/imports/${id}/assign-category`)}
          >
            Back
          </Button>
          <Button type="submit" disabled={mapMutation.isPending}>
            {mapMutation.isPending ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <CheckCircle2 className="w-4 h-4 mr-2" />
            )}
            Complete Import
          </Button>
        </div>
      </form>
    </div>
  );
}
