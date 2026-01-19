import { useCallback, useState } from 'react';
import { cn } from '@/lib/utils';
import { Upload, File, X, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';

export interface FileUploadProps {
  accept?: string;
  maxSize?: number; // in bytes
  onUpload: (file: File) => Promise<void>;
  className?: string;
}

type UploadState = 'idle' | 'dragging' | 'uploading' | 'success' | 'error';

export function FileUpload({
  accept = '.csv,.xlsx,.xls',
  maxSize = 50 * 1024 * 1024, // 50MB default
  onUpload,
  className,
}: FileUploadProps) {
  const [state, setState] = useState<UploadState>('idle');
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);

  const validateFile = (file: File): string | null => {
    if (maxSize && file.size > maxSize) {
      return `File size exceeds ${Math.round(maxSize / 1024 / 1024)}MB limit`;
    }
    const acceptedTypes = accept.split(',').map((t) => t.trim().toLowerCase());
    const fileExt = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!acceptedTypes.includes(fileExt)) {
      return `File type not accepted. Accepted: ${accept}`;
    }
    return null;
  };

  const handleFile = useCallback(
    async (file: File) => {
      const validationError = validateFile(file);
      if (validationError) {
        setError(validationError);
        setState('error');
        return;
      }

      setFile(file);
      setError(null);
      setState('uploading');

      // Simulate progress for demo
      const progressInterval = setInterval(() => {
        setProgress((prev) => Math.min(prev + 10, 90));
      }, 200);

      try {
        await onUpload(file);
        clearInterval(progressInterval);
        setProgress(100);
        setState('success');
      } catch (err) {
        clearInterval(progressInterval);
        setError(err instanceof Error ? err.message : 'Upload failed');
        setState('error');
      }
    },
    [onUpload, maxSize, accept]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setState('idle');
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile) {
        handleFile(droppedFile);
      }
    },
    [handleFile]
  );

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setState('dragging');
  };

  const handleDragLeave = () => {
    setState('idle');
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      handleFile(selectedFile);
    }
  };

  const reset = () => {
    setFile(null);
    setError(null);
    setState('idle');
    setProgress(0);
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return Math.round(bytes / 1024) + ' KB';
    return (bytes / 1024 / 1024).toFixed(1) + ' MB';
  };

  return (
    <div className={cn('w-full', className)}>
      <AnimatePresence mode="wait">
        {state === 'idle' || state === 'dragging' ? (
          <motion.label
            key="dropzone"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className={cn(
              'file-dropzone flex flex-col items-center',
              state === 'dragging' && 'active'
            )}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
          >
            <Upload className="w-10 h-10 text-muted-foreground mb-4" />
            <p className="text-foreground font-medium mb-1 font-display">
              Drop your file here or click to browse
            </p>
            <p className="text-sm text-muted-foreground">
              Supports {accept.replace(/\./g, '').toUpperCase()} up to {Math.round(maxSize / 1024 / 1024)}MB
            </p>
            <input
              type="file"
              accept={accept}
              onChange={handleInputChange}
              className="hidden"
            />
          </motion.label>
        ) : (
          <motion.div
            key="file-info"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="border border-border rounded-lg p-4"
          >
            <div className="flex items-start gap-4">
              <div
                className={cn(
                  'p-3 rounded-lg',
                  state === 'success' && 'bg-status-success-bg',
                  state === 'error' && 'bg-status-error-bg',
                  state === 'uploading' && 'bg-status-processing-bg'
                )}
              >
                {state === 'uploading' && (
                  <Loader2 className="w-6 h-6 text-status-processing animate-spin" />
                )}
                {state === 'success' && (
                  <CheckCircle2 className="w-6 h-6 text-status-success" />
                )}
                {state === 'error' && (
                  <AlertCircle className="w-6 h-6 text-status-error" />
                )}
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-1">
                  <p className="font-medium text-foreground truncate font-display">
                    {file?.name}
                  </p>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={reset}
                    className="h-8 w-8 p-0"
                  >
                    <X className="w-4 h-4" />
                  </Button>
                </div>

                {file && (
                  <p className="text-sm text-muted-foreground">
                    {formatFileSize(file.size)}
                  </p>
                )}

                {state === 'uploading' && (
                  <div className="mt-3">
                    <div className="flex justify-between text-xs text-muted-foreground mb-1">
                      <span>Uploading...</span>
                      <span>{progress}%</span>
                    </div>
                    <div className="h-2 bg-muted rounded-full overflow-hidden">
                      <motion.div
                        className="h-full bg-primary rounded-full"
                        initial={{ width: 0 }}
                        animate={{ width: `${progress}%` }}
                        transition={{ duration: 0.2 }}
                      />
                    </div>
                  </div>
                )}

                {state === 'success' && (
                  <p className="text-sm text-status-success mt-2">
                    File uploaded successfully
                  </p>
                )}

                {state === 'error' && error && (
                  <p className="text-sm text-status-error mt-2">{error}</p>
                )}
              </div>
            </div>

            {state === 'error' && (
              <Button onClick={reset} variant="outline" className="w-full mt-4">
                Try Again
              </Button>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
