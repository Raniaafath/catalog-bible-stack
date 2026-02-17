import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { ArrowRight, Sparkles, Loader2, Eye, FileText } from 'lucide-react';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { generateContent, previewContent } from '@/lib/api';

export default function ContentNew() {
  const navigate = useNavigate();
  const [variantIds, setVariantIds] = useState('');
  const [template, setTemplate] = useState('');
  const [previewVariantId, setPreviewVariantId] = useState('');
  const [previewResult, setPreviewResult] = useState('');

  const contentMutation = useMutation({
    mutationFn: generateContent,
    onSuccess: () => {
      navigate('/content');
    },
  });

  const previewMutation = useMutation({
    mutationFn: previewContent,
    onSuccess: (data) => {
      setPreviewResult(data.content);
    },
  });

  const parseVariantIds = () => {
    return variantIds
      .split(/[,\n]/)
      .map((s) => s.trim())
      .filter(Boolean)
      .map((s) => parseInt(s, 10))
      .filter((n) => !isNaN(n));
  };

  const handleGenerateContent = () => {
    const ids = parseVariantIds();
    if (ids.length > 0) {
      contentMutation.mutate({ variant_ids: ids, template: template || undefined });
    }
  };

  const handlePreview = () => {
    const id = parseInt(previewVariantId, 10);
    if (!isNaN(id)) {
      previewMutation.mutate({ variant_id: id, template: template || undefined });
    }
  };

  return (
    <div className="page-container">
      <PageHeader
        title="New Generation"
        description="Generate titles and content for product variants"
        breadcrumbs={[
          { label: 'Dashboard', href: '/' },
          { label: 'Content', href: '/content' },
          { label: 'New' },
        ]}
      />

      <div className="max-w-3xl mx-auto">
        <Tabs defaultValue="generate" className="space-y-6">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="generate">Generate</TabsTrigger>
            <TabsTrigger value="preview">Preview</TabsTrigger>
          </TabsList>

          <TabsContent value="generate">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Sparkles className="w-5 h-5" />
                  Content Generation
                </CardTitle>
                <CardDescription>
                  Generate titles or content for selected product variants.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-2">
                  <Label htmlFor="variantIds">Variant IDs</Label>
                  <Textarea
                    id="variantIds"
                    value={variantIds}
                    onChange={(e) => setVariantIds(e.target.value)}
                    placeholder="Enter variant IDs (comma or newline separated)&#10;e.g., 1, 2, 3 or&#10;1&#10;2&#10;3"
                    rows={4}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="template">Template (optional)</Label>
                  <Textarea
                    id="template"
                    value={template}
                    onChange={(e) => setTemplate(e.target.value)}
                    placeholder="Custom template for generation..."
                    rows={3}
                  />
                </div>

                <div className="flex flex-col sm:flex-row gap-3">
                  <Button
                    variant="outline"
                    className="flex-1"
                    asChild
                  >
                    <Link to="/content/generate-titles">
                      <FileText className="w-4 h-4 mr-2" />
                      Generate titles (channel & locale)
                    </Link>
                  </Button>
                  <Button
                    onClick={handleGenerateContent}
                    disabled={!variantIds.trim() || contentMutation.isPending}
                    className="flex-1"
                  >
                    {contentMutation.isPending && (
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    )}
                    Generate Content
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="preview">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Eye className="w-5 h-5" />
                  Content Preview
                </CardTitle>
                <CardDescription>
                  Preview generated content for a single variant.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-2">
                  <Label htmlFor="previewId">Variant ID</Label>
                  <div className="flex gap-2">
                    <Input
                      id="previewId"
                      value={previewVariantId}
                      onChange={(e) => setPreviewVariantId(e.target.value)}
                      placeholder="Enter a variant ID"
                    />
                    <Button
                      onClick={handlePreview}
                      disabled={!previewVariantId || previewMutation.isPending}
                    >
                      {previewMutation.isPending ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Eye className="w-4 h-4" />
                      )}
                    </Button>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="template2">Template (optional)</Label>
                  <Textarea
                    id="template2"
                    value={template}
                    onChange={(e) => setTemplate(e.target.value)}
                    placeholder="Custom template for preview..."
                    rows={3}
                  />
                </div>

                {previewResult && (
                  <div className="space-y-2">
                    <Label>Preview Result</Label>
                    <div className="p-4 bg-muted rounded-lg text-sm whitespace-pre-wrap">
                      {previewResult}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        <div className="flex justify-end mt-6">
          <Button variant="outline" onClick={() => navigate('/content')}>
            Back to List
          </Button>
        </div>
      </div>
    </div>
  );
}
