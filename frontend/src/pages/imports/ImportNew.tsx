import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { Upload, ArrowRight, FileSpreadsheet, CheckCircle2 } from 'lucide-react';
import { PageHeader } from '@/components/PageHeader';
import { FileUpload } from '@/components/FileUpload';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { uploadImportFile, Import } from '@/lib/api';

export default function ImportNew() {
  const navigate = useNavigate();
  const [uploadedImport, setUploadedImport] = useState<Import | null>(null);

  const uploadMutation = useMutation({
    mutationFn: uploadImportFile,
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
        ) : (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <Card>
              <CardContent className="pt-6">
                <div className="flex flex-col items-center text-center">
                  <div className="p-4 rounded-full bg-status-success-bg mb-4">
                    <CheckCircle2 className="w-8 h-8 text-status-success" />
                  </div>
                  <h3 className="text-xl font-semibold font-display mb-2">
                    File Uploaded Successfully
                  </h3>
                  <p className="text-muted-foreground mb-6">
                    {uploadedImport.filename} • {uploadedImport.row_count.toLocaleString()} rows detected
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
