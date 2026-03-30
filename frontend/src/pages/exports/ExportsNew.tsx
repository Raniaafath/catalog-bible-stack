import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { ArrowRight, Download, Loader2 } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { getExportProfiles, getGenerationBatches, createExport } from '@/lib/api';

export default function ExportsNew() {
  const navigate = useNavigate();
  const [profileId, setProfileId] = useState('');
  const [batchId, setBatchId] = useState('');

  const { data: profiles, isLoading: profilesLoading } = useQuery({
    queryKey: ['export-profiles'],
    queryFn: getExportProfiles,
  });

  const { data: batches, isLoading: batchesLoading } = useQuery({
    queryKey: ['generation-batches'],
    queryFn: () => getGenerationBatches({ page: 1, page_size: 50 }),
  });

  const doneBatches = batches?.results?.filter((b) => b.status === 'done') ?? [];

  const createMutation = useMutation({
    mutationFn: createExport,
    onSuccess: () => {
      navigate('/exports');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (profileId) {
      createMutation.mutate({
        profile_id: Number(profileId),
        batch_id: batchId && batchId !== 'none' ? Number(batchId) : null,
      });
    }
  };

  return (
    <div className="page-container">
      <PageHeader
        title="New Export"
        description="Create a new export job"
        breadcrumbs={[
          { label: 'Dashboard', href: '/' },
          { label: 'Exports', href: '/exports' },
          { label: 'New Export' },
        ]}
      />

      <div className="max-w-xl mx-auto">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Download className="w-5 h-5" />
              Export Settings
            </CardTitle>
            <CardDescription>
              Select an export profile and optionally a generation batch to export.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="profile">Export Profile *</Label>
                <Select value={profileId} onValueChange={setProfileId} disabled={profilesLoading}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select profile..." />
                  </SelectTrigger>
                  <SelectContent>
                    {profiles?.results?.map((profile) => (
                      <SelectItem key={profile.id} value={profile.id.toString()}>
                        {profile.name} ({profile.format.toUpperCase()})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="batch">Generation Batch</Label>
                <Select value={batchId} onValueChange={setBatchId} disabled={batchesLoading}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select batch (optional)..." />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">— No batch —</SelectItem>
                    {doneBatches.map((batch) => (
                      <SelectItem key={batch.id} value={batch.id.toString()}>
                        Batch #{batch.id} · {batch.variant_count} variants ·{' '}
                        {formatDistanceToNow(new Date(batch.created_at), { addSuffix: true })}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {doneBatches.length === 0 && !batchesLoading && (
                  <p className="text-sm text-muted-foreground">
                    No completed batches found. Generate titles first to create a batch.
                  </p>
                )}
              </div>

              {createMutation.isError && (
                <p className="text-sm text-destructive">
                  Export failed. Please check your selection and try again.
                </p>
              )}

              <div className="flex justify-end gap-3">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => navigate('/exports')}
                >
                  Cancel
                </Button>
                <Button type="submit" disabled={!profileId || createMutation.isPending}>
                  {createMutation.isPending && (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  )}
                  Create Export
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
