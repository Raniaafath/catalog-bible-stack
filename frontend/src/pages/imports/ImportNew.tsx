import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { Upload, ArrowRight, FileSpreadsheet, CheckCircle2, Info, AlertCircle } from 'lucide-react';
import { PageHeader } from '@/components/PageHeader';
import { FileUpload } from '@/components/FileUpload';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { uploadImportFile, Import } from '@/lib/api';

export default function ImportNew() {
  const navigate = useNavigate();
  const [uploadedImport, setUploadedImport] = useState<Import | null>(null);
  const [manualGrouping, setManualGrouping] = useState(true);  // Default to manual

  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadImportFile(file, { 
      group_by_product_key: !manualGrouping 
    }),
    onSuccess: (data) => {
      setUploadedImport(data);
    },
  });

  const handleUpload = async (file: File) => {
    await uploadMutation.mutateAsync(file);
  };

  return (
    <div className="page-container">
      <PageHeader
        title="New Import"
        description="Upload a CSV or XLSX file to import product data"
        breadcrumbs={[
          { label: 'Dashboard', href: '/' },
          { label: 'Imports', href: '/imports' },
          { label: 'New Import' },
        ]}
      />

      <div className="max-w-2xl mx-auto">
        {!uploadedImport ? (
          <>
            {/* Grouping Mode Selection */}
            <Card className="mb-6">
              <CardHeader>
                <CardTitle className="text-base">Import Mode</CardTitle>
                <CardDescription>
                  Choose how variants should be grouped into products.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5 flex-1">
                    <Label htmlFor="manual-grouping" className="text-base font-medium">
                      Manual Grouping (Recommended)
                    </Label>
                    <p className="text-sm text-muted-foreground">
                      Import variants first, then group them manually with full control over variation axes per channel.
                    </p>
                  </div>
                  <Switch
                    id="manual-grouping"
                    checked={manualGrouping}
                    onCheckedChange={setManualGrouping}
                  />
                </div>
                
                <Alert>
                  <Info className="h-4 w-4" />
                  <AlertDescription>
                    {manualGrouping ? (
                      <>
                        <strong>Manual mode:</strong> Each CSV row creates a variant. After import, 
                        you can select variants and group them into products with channel-specific variation axes.
                      </>
                    ) : (
                      <>
                        <strong>Automatic mode:</strong> Variants with the same PRODUCT_KEY column 
                        will be automatically grouped. Requires a PRODUCT_KEY column in your CSV.
                      </>
                    )}
                  </AlertDescription>
                </Alert>
              </CardContent>
            </Card>

            {/* File Upload */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Upload className="w-5 h-5" />
                  Upload File
                </CardTitle>
                <CardDescription>
                  Drag and drop your file or click to browse. Supported formats: CSV, XLSX, XLS.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <FileUpload
                  accept=".csv,.xlsx,.xls"
                  maxSize={50 * 1024 * 1024}
                  onUpload={handleUpload}
                />
              </CardContent>
            </Card>
          </>
        ) : (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <Card>
              <CardContent className="pt-6">
                <div className="flex flex-col items-center text-center">
                  {uploadedImport.row_count === 0 ? (
                    <>
                      <div className="p-4 rounded-full bg-status-error-bg mb-4">
                        <AlertCircle className="w-8 h-8 text-status-error" />
                      </div>
                      <h3 className="text-xl font-semibold font-display mb-2">
                        No Rows Detected
                      </h3>
                      <p className="text-muted-foreground mb-4">
                        {uploadedImport.original_filename} • 0 rows detected
                      </p>
                      {uploadedImport.parse_error_message && (
                        <Alert variant="destructive" className="mb-6 text-left max-w-md">
                          <AlertCircle className="h-4 w-4" />
                          <AlertDescription className="mt-2">
                            {uploadedImport.parse_error_message}
                          </AlertDescription>
                        </Alert>
                      )}
                      <Button
                        variant="outline"
                        onClick={() => {
                          setUploadedImport(null);
                          uploadMutation.reset();
                        }}
                      >
                        Try Another File
                      </Button>
                    </>
                  ) : (
                    <>
                      <div className="p-4 rounded-full bg-status-success-bg mb-4">
                        <CheckCircle2 className="w-8 h-8 text-status-success" />
                      </div>
                      <h3 className="text-xl font-semibold font-display mb-2">
                        File Uploaded Successfully
                      </h3>
                      <p className="text-muted-foreground mb-6">
                        {uploadedImport.original_filename} • {uploadedImport.row_count.toLocaleString()} rows detected
                      </p>

                      <div className="flex flex-col sm:flex-row gap-3 w-full sm:w-auto">
                        <Button
                          variant="outline"
                          onClick={() => navigate(`/imports/${uploadedImport.id}`)}
                        >
                          <FileSpreadsheet className="w-4 h-4 mr-2" />
                          Preview Data
                        </Button>
                        <Button
                          onClick={() => navigate(`/imports/${uploadedImport.id}/assign-category`)}
                        >
                          Continue to Category
                          <ArrowRight className="w-4 h-4 ml-2" />
                        </Button>
                      </div>
                    </>
                  )}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* Instructions */}
        <Card className="mt-6">
          <CardHeader>
            <CardTitle className="text-base">File Requirements</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground space-y-2">
            <p>• First row should contain column headers</p>
            <p>• UTF-8 encoding recommended for special characters</p>
            <p>• Maximum file size: 50MB</p>
            <p>• For XLSX files, only the first sheet will be imported</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
