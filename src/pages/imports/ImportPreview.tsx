import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowRight, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { PageHeader } from '@/components/PageHeader';
import { StatusBadge } from '@/components/StatusBadge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { getImport, getImportPreview, Import, ImportPreview as ImportPreviewType } from '@/lib/api';
import { Loader2 } from 'lucide-react';

export default function ImportPreview() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const importId = Number(id);

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

  const isLoading = importLoading || previewLoading;

  if (isLoading) {
    return (
      <div className="page-container flex items-center justify-center min-h-[50vh]">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  const hasErrors = (previewData?.errors?.length ?? 0) > 0;

  return (
    <div className="page-container">
      <PageHeader
        title={`Preview: ${importData?.filename || 'Import'}`}
        description="Review the imported data before proceeding"
        breadcrumbs={[
          { label: 'Dashboard', href: '/' },
          { label: 'Imports', href: '/imports' },
          { label: importData?.filename || `Import #${id}` },
        ]}
        actions={
          <div className="flex gap-3">
            {importData?.status === 'awaiting_mapping' && (
              <Button onClick={() => navigate(`/imports/${id}/assign-category`)}>
                Assign Category
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            )}
          </div>
        }
      />

      {/* Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Status</p>
                <div className="mt-1">
                  <StatusBadge status={importData?.status || 'pending'} size="lg" />
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Rows</p>
                <p className="text-2xl font-bold font-display">
                  {importData?.row_count.toLocaleString() ?? 0}
                </p>
              </div>
              <CheckCircle2 className="w-8 h-8 text-status-success opacity-50" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Errors</p>
                <p className={`text-2xl font-bold font-display ${hasErrors ? 'text-status-error' : ''}`}>
                  {importData?.error_count ?? 0}
                </p>
              </div>
              {hasErrors && <AlertTriangle className="w-8 h-8 text-status-warning opacity-50" />}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Errors */}
      {hasErrors && (
        <Card className="mb-6 border-status-warning/50">
          <CardHeader className="pb-3">
            <CardTitle className="text-status-warning flex items-center gap-2">
              <AlertTriangle className="w-5 h-5" />
              Import Errors
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {previewData?.errors.map((err, i) => (
                <div key={i} className="text-sm p-2 rounded bg-status-error-bg text-status-error-foreground">
                  <span className="font-medium">Row {err.row}:</span> {err.message}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Data Preview */}
      <Card>
        <CardHeader>
          <CardTitle>Data Preview</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  {previewData?.headers.map((header, i) => (
                    <th key={i}>{header}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {previewData?.rows.slice(0, 20).map((row, i) => (
                  <tr key={i}>
                    {previewData?.headers.map((header, j) => (
                      <td key={j} className="max-w-[200px] truncate">
                        {String(row[header] ?? '')}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            {(previewData?.rows.length ?? 0) > 20 && (
              <div className="text-center py-4 text-sm text-muted-foreground border-t">
                Showing 20 of {previewData?.rows.length} rows
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
